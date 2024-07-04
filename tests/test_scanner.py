import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator
from unittest import mock

import pytest

from catalogscanner import catalog, scanner
from catalogscanner.common import ScanMode

TEST_ASSETS = Path(__file__).parent / "assets"


GROUND_TRUTH = json.loads((TEST_ASSETS / "expected/examples.json").read_text(encoding="utf-8"))
GROUND_TRUTH_EXTRAS = json.loads((TEST_ASSETS / "expected/extra.json").read_text(encoding="utf-8"))


@contextmanager
def inject_catalog_words(words: list[str], locale: str = "en-us") -> Generator[None, None, None]:
    db = catalog._get_item_db(locale) | set(words)
    with mock.patch.object(catalog, "_get_item_db", return_value=db):
        yield


class TestScanner:
    def test_when_catalog_scan_given_for_sale_then_only_return_for_sale_items(self) -> None:
        with inject_catalog_words(["Writing desk", "Teacup ride"]):
            results = scanner.scan_media(TEST_ASSETS / "input/catalog.mp4", for_sale=True)
        assert results.mode == ScanMode.CATALOG
        assert results.items == GROUND_TRUTH["test_catalog_for_sale"]
        assert results.locale == "en-us"

    def test_when_catalog_scan_given_not_for_sale_then_only_return_not_for_sale_items(self) -> None:
        with inject_catalog_words(["Writing desk", "Teacup ride"]):
            results = scanner.scan_media(TEST_ASSETS / "input/catalog.mp4", for_sale=False)
        assert results.mode == ScanMode.CATALOG
        assert results.items == GROUND_TRUTH["test_catalog"]
        assert results.locale == "en-us"

    def test_when_recipe_scan_given_recipe_video_then_return_recipes_from_video(self) -> None:
        results = scanner.scan_media(TEST_ASSETS / "input/recipes.mp4")
        assert results.mode == ScanMode.RECIPES
        assert results.items == GROUND_TRUTH["test_recipes"]
        assert results.locale == "en-us"

    def test_when_recipe_scan_given_recipe_video_and_locale_then_return_recipes_from_video_in_locale(self) -> None:
        results = scanner.scan_media(TEST_ASSETS / "input/recipes.mp4", locale="fr-eu")
        assert results.mode == ScanMode.RECIPES
        assert results.items == GROUND_TRUTH["test_recipes_translate"]
        assert results.locale == "fr-eu"

    def test_when_critters_scan_given_critters_video_then_return_critters_from_video(self) -> None:
        results = scanner.scan_media(TEST_ASSETS / "input/critters.mp4")
        assert results.mode == ScanMode.CRITTERS
        assert results.items == GROUND_TRUTH["test_critters"]
        assert results.locale == "en-us"

    def test_when_critters_scan_given_critters_video_and_locale_then_return_critters_from_video_in_locale(self) -> None:
        results = scanner.scan_media(TEST_ASSETS / "input/critters.mp4", locale="ko-kr")
        assert results.mode == ScanMode.CRITTERS
        assert results.items == GROUND_TRUTH["test_critters_translate"]
        assert results.locale == "ko-kr"

    def test_when_reactions_scan_given_reactions_video_then_return_reactions_from_video(self) -> None:
        results = scanner.scan_media(TEST_ASSETS / "input/reactions.jpg")
        assert results.mode == ScanMode.REACTIONS
        assert results.items == GROUND_TRUTH["test_reactions"]
        assert results.locale == "en-us"

    def test_when_reactions_scan_given_reactions_video_and_locale_then_return_reactions_from_video_in_locale(
        self,
    ) -> None:
        results = scanner.scan_media(TEST_ASSETS / "input/reactions.jpg", locale="de-eu")
        assert results.mode == ScanMode.REACTIONS
        assert results.items == GROUND_TRUTH["test_reactions_translate"]
        assert results.locale == "de-eu"

    def test_when_music_scan_given_music_video_then_return_music_from_video(self) -> None:
        results = scanner.scan_media(TEST_ASSETS / "input/music.mp4")
        assert results.mode == ScanMode.MUSIC
        assert results.items == GROUND_TRUTH["test_music"]
        assert results.locale == "en-us"

    def test_when_music_scan_given_music_video_and_locale_then_return_music_from_video_in_locale(self) -> None:
        results = scanner.scan_media(TEST_ASSETS / "input/music.mp4", locale="ja-jp")
        assert results.mode == ScanMode.MUSIC
        assert results.items == GROUND_TRUTH["test_music_translate"]
        assert results.locale == "ja-jp"


@pytest.mark.parametrize("filename", GROUND_TRUTH_EXTRAS.keys())
def test_extra(filename: str) -> None:
    filepath = TEST_ASSETS / "input/extra" / filename
    try:
        results = scanner.scan_media(filepath)
        actual: Any = results.items
    except AssertionError as e:
        actual = str(e)
    assert GROUND_TRUTH_EXTRAS[filename] == actual
