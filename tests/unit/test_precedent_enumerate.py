"""Unit tests for tree-based precedent enumeration."""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from legalize_cli.http import GitHubClient
from legalize_cli.precedents.enumerate import enumerate_precedents
from legalize_cli.precedents.list import list_precedents

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _client(tree_payload: dict) -> GitHubClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/git/trees/" in str(request.url):
            return httpx.Response(200, json=tree_payload)
        return httpx.Response(404, json={"message": "unexpected"})

    return GitHubClient(
        transport=httpx.MockTransport(handler), token=None, token_source="none"
    )


def _tree() -> dict:
    return json.loads((FIXTURES / "precedents" / "tree_precedents.json").read_text())


def test_enumerate_returns_only_md_blobs() -> None:
    client = _client(_tree())
    try:
        entries = enumerate_precedents(client)
    finally:
        client.close()

    assert len(entries) == 5
    assert all(e.path.endswith(".md") for e in entries)
    assert not any(e.path in (".gitignore", "README.md") for e in entries)


def test_fields_parsed_from_path() -> None:
    client = _client(_tree())
    try:
        entries = enumerate_precedents(client)
    finally:
        client.close()

    by_path = {e.path: e for e in entries}

    e = by_path["민사/대법원/2000다10048.md"]
    assert e.사건종류 == "민사"
    assert e.법원명 == "대법원"
    assert e.사건번호 == "2000다10048"
    assert e.판례일련번호 == "민사/대법원/2000다10048.md"

    # Underscore-separated 사건번호 preserved verbatim
    e2 = by_path["가사/대법원/2000므1257_본소_1264_반소.md"]
    assert e2.사건번호 == "2000므1257_본소_1264_반소"
    assert e2.사건종류 == "가사"


def test_list_filter_by_court() -> None:
    client = _client(_tree())
    try:
        entries = enumerate_precedents(client)
    finally:
        client.close()

    total, window, _ = list_precedents(entries, court="대법원")
    assert all(e.법원명 == "대법원" for e in window)
    assert total == 4  # 가사/대법원, 민사/대법원×2, 형사/대법원


def test_list_filter_by_type() -> None:
    client = _client(_tree())
    try:
        entries = enumerate_precedents(client)
    finally:
        client.close()

    total, window, _ = list_precedents(entries, type_="형사")
    assert all(e.사건종류 == "형사" for e in window)
    assert total == 2


def test_list_pagination() -> None:
    client = _client(_tree())
    try:
        entries = enumerate_precedents(client)
    finally:
        client.close()

    total, page1, next_page = list_precedents(entries, page=1, page_size=3)
    assert total == 5
    assert len(page1) == 3
    assert next_page == 2

    _, page2, next_page2 = list_precedents(entries, page=2, page_size=3)
    assert len(page2) == 2
    assert next_page2 is None


def test_enumerate_handles_truncated_root_tree() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("/git/trees/main?recursive=1"):
            return httpx.Response(
                200,
                json={
                    "truncated": True,
                    "tree": [
                        {
                            "path": "민사",
                            "type": "tree",
                            "sha": "sha-civil",
                        }
                    ],
                },
            )
        if url.endswith("/git/trees/main"):
            return httpx.Response(
                200,
                json={
                    "tree": [
                        {
                            "path": "민사",
                            "type": "tree",
                            "sha": "sha-civil",
                        },
                        {
                            "path": "특허",
                            "type": "tree",
                            "sha": "sha-patent",
                        },
                    ]
                },
            )
        if url.endswith("/git/trees/sha-civil?recursive=1"):
            return httpx.Response(200, json={"tree": []})
        if url.endswith("/git/trees/sha-patent?recursive=1"):
            return httpx.Response(
                200,
                json={
                    "tree": [
                        {
                            "path": "대법원/대법원_2026-01-15_2022후10401.md",
                            "type": "blob",
                            "sha": "sha-doc",
                        }
                    ]
                },
            )
        return httpx.Response(404, json={"message": f"unexpected {url}"})

    client = GitHubClient(
        transport=httpx.MockTransport(handler),
        token=None,
        token_source="none",
    )
    try:
        entries = enumerate_precedents(client)
    finally:
        client.close()

    assert [entry.path for entry in entries] == [
        "특허/대법원/대법원_2026-01-15_2022후10401.md"
    ]
    assert entries[0].사건종류 == "특허"


def test_lower_court_filter_uses_filename_court_and_preserves_case_number() -> None:
    path = "가사/하급심/서울중앙지방법원_2023-01-16_2022가단5122663_병합.md"
    missing_date_path = "민사/하급심/미상법원_0000-00-00_12345.md"
    client = _client({"tree": [{"path": p, "type": "blob", "sha": "a" * 40} for p in [path, missing_date_path]]})
    try:
        entries = enumerate_precedents(client)
    finally:
        client.close()
    total, items, _ = list_precedents(entries, court="서울중앙지방법원")
    assert total == 1
    assert items[0].사건번호 == "2022가단5122663_병합"
    assert items[0].path == path
    assert list_precedents(entries, court="미상법원")[0] == 1
    assert list_precedents(entries, court="하급심")[0] == 0
