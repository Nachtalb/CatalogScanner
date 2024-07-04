import functools
from pathlib import Path
from typing import Iterator, List

import cv2
import imagehash
import numpy as np
from PIL import Image

from catalogscanner.common import ASSET_PATH, FRAME_TYPE, ScanMode, ScanResult, read_json_asset

# The expected color for the video background.
BG_COLOR1 = (240, 210, 100)
BG_COLOR2 = (226, 119, 79)
BG_COLOR3 = (49, 60, 102)
BG_COLOR4 = (83, 117, 173)

MUSIC_PATH = ASSET_PATH / "music"


class SongCover:
    """The image and data associated with a given song."""

    def __init__(self, song_name: str, image_name: str, hash_hex: str) -> None:
        self.song_name = song_name
        self.image_name = image_name
        self.hash_hex = hash_hex
        self.icon_hash = imagehash.hex_to_hash(hash_hex)

    def __repr__(self) -> str:
        return f"SongCover({self.song_name!r}, {self.hash_hex!r})"


def detect(frame: FRAME_TYPE) -> bool:
    """Detects if a given frame is showing the music list."""
    color = frame[:20, 1220:1250].mean(axis=(0, 1))
    if _is_background(color):
        return True
    return False


def scan(video_file: Path, locale: str = "en-us") -> ScanResult:
    """Scans a video of scrolling through music list and returns all songs found."""
    song_covers = parse_video(video_file)
    song_names = match_songs(song_covers)
    results = translate_names(song_names, locale)

    return ScanResult(
        mode=ScanMode.MUSIC,
        items=results,
        locale=locale.replace("auto", "en-us"),
    )


def parse_video(filename: Path) -> List[FRAME_TYPE]:
    """Parses a whole video and returns images for all song covers found."""
    all_covers: List[FRAME_TYPE] = []
    for frame in _read_frames(filename):
        for new_covers in _parse_frame(frame):
            if _is_duplicate_cards(all_covers, new_covers):
                continue  # Skip non-moving frames
            all_covers.extend(new_covers)
    return _remove_blanks(all_covers)


def match_songs(song_covers: List[FRAME_TYPE]) -> List[str]:
    """Matches icons against database of music covers, finding best matches."""
    matched_songs = set()
    song_db = _get_song_db()
    for cover in song_covers:
        image = Image.fromarray(cover)
        test_hash = imagehash.phash(image, hash_size=18)
        best_match = min(song_db, key=lambda x: x.icon_hash - test_hash)
        matched_songs.add(best_match.song_name)
    return sorted(matched_songs)


def translate_names(song_names: List[str], locale: str) -> List[str]:
    """Translates a list of song names to the given locale."""
    if locale in ["auto", "en-us"]:
        return song_names

    translations = read_json_asset(MUSIC_PATH / "translations.json")
    return [translations[name][locale] for name in song_names]


def _read_frames(filename: Path) -> Iterator[FRAME_TYPE]:
    """Parses frames of the given video and returns the relevant region."""
    cap = cv2.VideoCapture(filename)  # type: ignore[call-overload]
    while True:
        ret, frame = cap.read()
        if not ret:
            break  # Video is over

        assert frame.shape[:2] == (720, 1280), "Invalid resolution: {1}x{0}".format(*frame.shape)

        if not detect(frame):
            continue  # Skip frames that are not showing music list.

        # Crop the region containing only song covers.
        yield frame[95:670, 40:1240]

    cap.release()


def _parse_frame(frame: FRAME_TYPE) -> Iterator[List[FRAME_TYPE]]:
    """Parses an individual frame and extracts song covers from the music list."""
    # Start vertical position for the 4 song covers.
    x_positions = [40, 327, 614, 900]

    # The current backgroudn color.
    bg_color = frame[:20, :20].mean(axis=(0, 1))

    # Detect special case when less than one full row of song covers.
    end_row_color = frame[100:200, 1000:1100].mean(axis=(0, 1))
    if np.linalg.norm(end_row_color - bg_color) < 5:
        yield [frame[15:275, x : x + 260] for x in x_positions]
        return

    # This code finds areas of the image that are blue (background color),
    # then it averages the frame across the Y-axis to find the area rows.
    # Lastly, it finds the y-positions marking the start/end of each row.
    thresh = cv2.inRange(frame[:410], bg_color - 30, bg_color + 30)
    separators = np.nonzero(np.diff(thresh.mean(axis=1) > 100))[0]
    if len(separators) < 2:
        return

    # We do a first pass finding all sensible y positions.
    y_centers = []
    for y1, y2 in zip(separators, separators[1:]):
        if 259 < y2 - y1 < 266:
            y_centers.extend([y1 % 287, (y2 + 25) % 287])
        if 20 < y2 - y1 < 27:
            y_centers.extend([y2 % 287, (y1 + 25) % 287])
    if not y_centers:
        return

    y_centroid = np.mean(y_centers) + 1
    y_positions = np.arange(y_centroid, 575, 287).astype(int)

    for y in y_positions:
        if y + 260 > frame.shape[0]:
            continue  # Past the bottom of the frame
        yield [frame[y : y + 260, x : x + 260] for x in x_positions]


def _is_duplicate_cards(all_covers: List[FRAME_TYPE], new_covers: List[FRAME_TYPE]) -> bool:
    """Checks if the new set of covers are the same as the previous seen covers."""
    if not all_covers or len(all_covers) < len(new_covers):
        return False

    new_concat = cv2.hconcat(new_covers)
    # Checks the last 2 rows for similarities to the newly added row.
    for ind in [slice(-4, None), slice(-8, -4)]:
        old_concat = cv2.hconcat(all_covers[ind])
        if old_concat is None:
            continue
        if cv2.absdiff(new_concat, old_concat).mean() < 15:
            return True
    return False


def _remove_blanks(all_icons: List[FRAME_TYPE]) -> List[FRAME_TYPE]:
    """Remove all icons that do not show a song cover."""
    filtered_icons = []
    for icon in all_icons:
        color = icon[5:25, 60:200].mean(axis=(0, 1))
        if _is_background(color):
            continue
        filtered_icons.append(icon)
    return filtered_icons


def _is_background(color: FRAME_TYPE) -> bool:
    if np.linalg.norm(color - BG_COLOR1) < 15:
        return True
    if np.linalg.norm(color - BG_COLOR2) < 15:
        return True
    if np.linalg.norm(color - BG_COLOR3) < 15:
        return True
    if np.linalg.norm(color - BG_COLOR4) < 15:
        return True
    return False


@functools.lru_cache()
def _get_song_db() -> List[SongCover]:
    """Fetches the song cover database for a given locale, with caching."""
    music_data = read_json_asset(MUSIC_PATH / "names.json")
    return [SongCover(*data) for data in music_data]


if __name__ == "__main__":
    results = scan(Path("examples/music.mp4"))
    print("\n".join(results.items))
