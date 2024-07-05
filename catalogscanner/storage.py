# SPDX-License-Identifier: MIT
# Copyright (c) 2020 Ehsan Kia
# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (c) 2024 Nachtalb
# This file contains both MIT and LGPL-3.0-or-later licensed code.
from pathlib import Path
from typing import Iterator, List

import cv2
import numpy as np

from catalogscanner.common import FRAME_TYPE, ScanMode, ScanResult

# The expected color for the video background.
BG_COLOR = (69, 198, 246)

# The center color for a empty storage slot.
BLANK_COLOR = (192, 230, 242)


def detect(frame: FRAME_TYPE) -> bool:
    """Detects if a given frame is showing the storage items."""
    color = frame[:20, 1100:1150].mean(axis=(0, 1))
    return np.linalg.norm(color - BG_COLOR) < 5  # type: ignore[return-value]


def scan(video_file: Path, locale: str = "en-us") -> ScanResult:
    """Scans a video of scrolling through storage returns all items found."""
    item_images = parse_video(video_file)
    item_names = match_items(item_images)
    results = translate_names(item_names, locale)

    return ScanResult(
        mode=ScanMode.STORAGE,
        items=results,
        locale=locale.replace("auto", "en-us"),
    )


def parse_video(filename: Path) -> List[FRAME_TYPE]:
    """Parses a whole video and returns images for all storage items found."""
    all_rows: List[FRAME_TYPE] = []
    for i, frame in enumerate(_read_frames(filename)):
        if i % 4 != 0:
            continue  # Skip every 4th frame
        for new_row in _parse_frame(frame):
            if _is_duplicate_row(all_rows, new_row):
                continue  # Skip non-moving frames
            all_rows.extend(new_row)
    return _remove_blanks(all_rows)


def match_items(item_images: List[FRAME_TYPE]) -> List[str]:
    """Matches icons against database of item images, finding best matches."""
    # TODO: Implement image to item matching.
    return []


def translate_names(item_names: List[str], locale: str) -> List[str]:
    """Translates a list of item names to the given locale."""
    # TODO: Implement translation
    return item_names


def _read_frames(filename: Path) -> Iterator[FRAME_TYPE]:
    """Parses frames of the given video and returns the relevant region."""
    cap = cv2.VideoCapture(filename)  # type: ignore[call-overload]
    while True:
        ret, frame = cap.read()
        if not ret:
            break  # Video is over

        assert frame.shape[:2] == (720, 1280), "Invalid resolution: {1}x{0}".format(*frame.shape)

        if not detect(frame):
            continue  # Skip frames that are not showing storage.

        # Crop the region containing storage items.
        yield frame[150:675, 112:1168]
    cap.release()


def _parse_frame(frame: FRAME_TYPE) -> Iterator[List[FRAME_TYPE]]:
    """Parses an individual frame and extracts cards from the storage."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    x_positions = list(range(0, 1056, 132))

    cols = []
    for x in x_positions[1:]:
        empty_col = gray[:, x - 10 : x + 10]
        if empty_col.min() < 200:
            continue  # Skip columns with occlusions
        cols.append(empty_col)

    thresh = cv2.threshold(cv2.hconcat(cols), 236, 255, 0)[1]
    separators = list(np.nonzero(thresh.mean(axis=1) < 240)[0])

    # Normalize row lines by taking the average of all of them.
    # We know they are 127px apart, so we find the best offset from given lines.
    centroid = int(np.median([s % 127 for s in separators]))
    y_positions = list(range(centroid, 525, 127))

    for y in y_positions:
        if y + 127 > frame.shape[0]:
            continue  # Past the bottom of the frame.
        # Skip row when tooltip is overlapping the item.
        tooltip = cv2.inRange(frame[y + 122 : y + 127, :], (160, 195, 80), (180, 205, 100))  # type: ignore[call-overload]
        if tooltip.mean() > 10:
            continue

        yield [frame[y + 13 : y + 113, x + 16 : x + 116] for x in x_positions]


def _is_duplicate_row(all_rows: List[FRAME_TYPE], new_row: List[FRAME_TYPE]) -> bool:
    """Checks if the new row is the same as the previous seen rows."""
    if not new_row or len(all_rows) < len(new_row):
        return False

    new_concat = cv2.hconcat(new_row)
    # Checks the last 4 rows for similarities to the newly added row.
    for ind in [slice(-8, None), slice(-16, -8), slice(-24, -16), slice(-32, -24)]:
        old_concat = cv2.hconcat(all_rows[ind])
        if old_concat is None:
            continue

        if cv2.absdiff(new_concat, old_concat).mean() < 12:
            # If the old version had a cursor in it, replace with new row.
            if old_concat[-5:].min() < 50:
                all_rows[ind] = new_row
            return True

    return False


def _remove_blanks(all_icons: List[FRAME_TYPE]) -> List[FRAME_TYPE]:
    """Remove all icons that show empty critter boxes."""
    filtered_icons = []
    for icon in all_icons:
        center_color = icon[40:60, 40:60].mean(axis=(0, 1))
        if np.linalg.norm(center_color - BLANK_COLOR) < 5:
            continue
        filtered_icons.append(icon)
    return filtered_icons


if __name__ == "__main__":
    results = scan(Path("examples/storage.mp4"))
    print("\n".join(results.items))
