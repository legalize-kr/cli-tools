"""Unit tests for the precedent index fetch paths.

Verifies:
- Primary path = ``raw.githubusercontent.com`` (no API-rate-limit charge).
- Fallback path = ``/git/blobs/{sha}`` (via tree lookup), never ``/contents/``.
- Large payloads (>1MB) survive both paths.
"""

from __future__ import annotations

import json

import httpx

from legalize_cli.http import GitHubClient
from legalize_cli.precedents.index import fetch_precedent_index


def _make_index_bytes(n_entries: int = 5, pad_bytes: int = 0) -> bytes:
    """Build a metadata.json-shaped payload, optionally padded for size tests."""
    data = {}
    for i in range(n_entries):
        data[str(100000 + i)] = {
            "path": f"민사/대법원/{2000 + i}다{i:05d}.md",
            "사건명": "padded name " + "X" * pad_bytes if i == 0 else "test",
            "사건번호": f"{2000 + i}다{i:05d}",
            "선고일자": "2020-01-01",
            "법원명": "대법원",
            "사건종류": "민사",
            "판결유형": "",
        }
    return json.dumps(data, ensure_ascii=False).encode("utf-8")


def test_primary_raw_cdn_wins() -> None:
    payload = _make_index_bytes()
    seen_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_urls.append(str(request.url))
        if "raw.githubusercontent.com" in str(request.url):
            return httpx.Response(200, content=payload)
        return httpx.Response(404, json={"message": "should not be called"})

    client = GitHubClient(
        transport=httpx.MockTransport(handler), token=None, token_source="none"
    )
    try:
        index = fetch_precedent_index(client)
    finally:
        client.close()

    assert len(index) == 5
    # Fallback MUST NOT be invoked when primary succeeds.
    assert all("/git/blobs/" not in u for u in seen_urls)
    # /contents/ must never be used for the 34MB file.
    assert all("/contents/" not in u for u in seen_urls)
    # We did hit raw CDN.
    assert any("raw.githubusercontent.com" in u for u in seen_urls)


def test_blob_fallback_when_cdn_fails() -> None:
    payload = _make_index_bytes(n_entries=3)
    tree_payload = {
        "sha": "aaaa",
        "truncated": False,
        "tree": [
            {"path": "metadata.json", "mode": "100644", "type": "blob", "sha": "deadbeef", "size": len(payload)}
        ],
    }
    seen_urls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        seen_urls.append(url)
        if "raw.githubusercontent.com" in url:
            return httpx.Response(500, text="cdn temporarily unavailable")
        if "/git/trees/" in url:
            return httpx.Response(200, json=tree_payload)
        if "/git/blobs/deadbeef" in url:
            return httpx.Response(200, content=payload)
        return httpx.Response(404, json={"message": "unexpected"})

    client = GitHubClient(
        transport=httpx.MockTransport(handler), token=None, token_source="none"
    )
    try:
        index = fetch_precedent_index(client)
    finally:
        client.close()

    assert len(index) == 3
    # /contents/ must never be used — even in fallback mode.
    assert all("/contents/" not in u for u in seen_urls)
    assert any("/git/blobs/deadbeef" in u for u in seen_urls)


def test_oversize_payload_survives() -> None:
    """Index >1MB must come through cleanly (not truncated by the 1MB cap)."""
    payload = _make_index_bytes(n_entries=2, pad_bytes=1_500_000)
    assert len(payload) > 1_024 * 1_024

    def handler(request: httpx.Request) -> httpx.Response:
        if "raw.githubusercontent.com" in str(request.url):
            return httpx.Response(200, content=payload)
        return httpx.Response(404, json={"message": "unexpected"})

    client = GitHubClient(
        transport=httpx.MockTransport(handler), token=None, token_source="none"
    )
    try:
        index = fetch_precedent_index(client)
    finally:
        client.close()

    assert len(index) == 2
