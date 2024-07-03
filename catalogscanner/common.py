import dataclasses
import enum
import json
from pathlib import Path
from typing import Any, List

ASSET_PATH = Path(__file__).parent.parent / "assets"


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
