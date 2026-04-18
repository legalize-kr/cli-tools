"""Integration tests for tree-based precedent search (no metadata.json)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from legalize_cli.http import GitHubClient
from legalize_cli.search.tree_filter import tree_filter_items

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _tree() -> dict:
    return json.loads((FIXTURES / "precedents" / "tree_precedents.json").read_text())


def _client(tree_payload: dict) -> GitHubClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/git/trees/" in str(request.url):
            return httpx.Response(200, json=tree_payload)
        return httpx.Response(404, json={"message": "unexpected"})

    return GitHubClient(
        transport=httpx.MockTransport(handler), token=None, token_source="none"
    )


def test_search_by_사건번호_in_path() -> None:
    client = _client(_tree())
    try:
        items = tree_filter_items(client, None, "2018도11111", repo="precedent-kr", source="precedents")
    finally:
        client.close()

    assert len(items) == 1
    assert items[0]["path"] == "형사/대법원/2018도11111.md"
    assert items[0]["source"] == "precedents"


def test_search_by_사건종류_in_path() -> None:
    client = _client(_tree())
    try:
        items = tree_filter_items(client, None, "가사", repo="precedent-kr", source="precedents")
    finally:
        client.close()

    assert len(items) >= 1
    assert all("가사" in item["path"] for item in items)


def test_search_no_match() -> None:
    client = _client(_tree())
    try:
        items = tree_filter_items(client, None, "없는키워드XYZ99999", repo="precedent-kr", source="precedents")
    finally:
        client.close()

    assert items == []
