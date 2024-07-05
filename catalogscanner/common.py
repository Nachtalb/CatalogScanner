# SPDX-License-Identifier: MIT
# Copyright (c) 2020 Ehsan Kia
# SPDX-License-Identifier: LGPL-3.0-or-later
# Copyright (c) 2024 Nachtalb
# This file contains both MIT and LGPL-3.0-or-later licensed code.
import dataclasses
import enum
import json
from pathlib import Path
from typing import Any, List

import numpy as np

ASSET_PATH = Path(__file__).parent.parent / "assets"

FRAME_TYPE = np.ndarray[Any, np.dtype[np.integer[Any] | np.floating[Any]]]
NP_BOOL = np.dtype(np.bool)


class ScanMode(enum.Enum):
    CATALOG = 1
    RECIPES = 2
    STORAGE = 3
    CRITTERS = 4
    REACTIONS = 5
    MUSIC = 6


@dataclasses.dataclass
class ScanResult:
    mode: ScanMode
    items: List[str]
    locale: str
    unmatched: List[str] = dataclasses.field(default_factory=list)


def read_asset(filename: str | Path, encoding: str = "utf-8") -> str:
    filename = Path(filename)
    if filename.is_file():
        return filename.read_text(encoding=encoding)
    return (ASSET_PATH / filename).read_text(encoding=encoding)


def read_json_asset(filename: str | Path, encoding: str = "utf-8") -> Any:
    return json.loads(read_asset(filename, encoding=encoding))
