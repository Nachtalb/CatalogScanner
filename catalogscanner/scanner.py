# SPDX-License-Identifier: MIT
# Copyright (c) 2020 Ehsan Kia
# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (c) 2024 Nachtalb
# This file contains both MIT and LGPL-3.0-or-later licensed code.
import argparse
import logging
from pathlib import Path
from typing import Any, Dict

import cv2

from catalogscanner import catalog, critters, music, reactions, recipes, storage
from catalogscanner.common import ScanResult

SCANNERS: Dict[str, Any] = {
    "catalog": catalog,
    "recipes": recipes,
    "critters": critters,
    "reactions": reactions,
    "music": music,
    "storage": storage,
}

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def scan_media(filename: Path, mode: str = "auto", locale: str = "auto", for_sale: bool = False) -> ScanResult:
    if "%d" not in filename.name and not filename.is_file():
        raise FileNotFoundError("File not found: %r" % filename)

    if mode == "auto":
        mode = _detect_media_type(filename)
        logging.info("Detected scan mode: %s", mode)

    if mode not in SCANNERS:
        raise RuntimeError("Invalid mode: %r" % mode)

    assert mode != "storage", "Storage scanning is not supported."

    kwargs = {}
    if mode == "catalog":
        kwargs["for_sale"] = for_sale

    return SCANNERS[mode].scan(filename, locale=locale, **kwargs)  # type: ignore[no-any-return]


def _detect_media_type(filename: Path) -> str:
    video_capture = cv2.VideoCapture(filename)  # type: ignore[call-overload]

    # Check the first 100 frames for a match.
    for _ in range(100):
        success, frame = video_capture.read()
        if not success or frame is None:
            break

        # Resize 1080p screenshots to 720p to match videos.
        if filename.suffix == ".jpg" and frame.shape[:2] == (1080, 1920):
            frame = cv2.resize(frame, (1280, 720))

        assert frame.shape[:2] == (720, 1280), "Invalid resolution: {1}x{0}".format(*frame.shape)

        for mode, scanner in SCANNERS.items():
            if scanner.detect(frame):
                return mode

    raise AssertionError("Media is not showing a known scan type.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Item scanner configuration")
    parser.add_argument("media", type=Path, help="The media file to scan.")

    parser.add_argument(
        "--locale", choices=list(catalog.LOCALE_MAP), default="auto", help="The locale to use for parsing item names."
    )

    parser.add_argument(
        "--for-sale", action="store_true", help="If true, the scanner will skip items that are not for sale."
    )

    parser.add_argument(
        "--mode",
        choices=["auto"] + list(SCANNERS),
        default="auto",
        help="The type of catalog to scan. Auto tries to detect from the media frames.",
    )

    args = parser.parse_args()

    result = scan_media(
        args.media,
        mode=args.mode,
        locale=args.locale,
        for_sale=args.for_sale,
    )

    result_count, result_mode = len(result.items), result.mode.name.lower()
    print(f"Found {result_count} items in {result_mode} [{result.locale}]")
    print("\n".join(result.items))


if __name__ == "__main__":
    main()
