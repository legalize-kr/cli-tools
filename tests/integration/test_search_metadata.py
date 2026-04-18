"""Integration tests for metadata-backed precedent search.

After the index is in-memory, metadata_search_items must do zero HTTP work.
"""

from __future__ import annotations

from legalize_cli.precedents.model import PrecedentEntry
from legalize_cli.search.metadata_search import metadata_search_items


def _build_index(fixture: dict) -> dict[str, PrecedentEntry]:
    out: dict[str, PrecedentEntry] = {}
    for key, value in fixture.items():
        out[key] = PrecedentEntry.model_validate({"판례일련번호": key, **value})
    return out


def test_search_by_사건명(precedent_metadata_fixture) -> None:
    index = _build_index(precedent_metadata_fixture)
    items = metadata_search_items(index, "손해배상")
    assert len(items) == 1
    assert items[0]["path"].endswith("2000므1257_본소_1264_반소.md")
    assert items[0]["source"] == "precedents"


def test_search_by_법원명(precedent_metadata_fixture) -> None:
    index = _build_index(precedent_metadata_fixture)
    items = metadata_search_items(index, "서울중앙지방법원")
    assert len(items) == 1
    assert items[0]["path"] == "형사/하급심/2019고합987.md"


def test_search_by_사건번호(precedent_metadata_fixture) -> None:
    index = _build_index(precedent_metadata_fixture)
    items = metadata_search_items(index, "2018도11111")
    assert len(items) == 1
    assert items[0]["path"] == "형사/대법원/2018도11111.md"


def test_search_empty_on_miss(precedent_metadata_fixture) -> None:
    index = _build_index(precedent_metadata_fixture)
    items = metadata_search_items(index, "없는키워드XYZ")
    assert items == []
