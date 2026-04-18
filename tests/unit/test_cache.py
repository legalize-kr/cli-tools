"""Tests for :mod:`legalize_cli.cache` — TTL, ETag 304, and (path,date) key stability."""

from __future__ import annotations

import os
import time
from datetime import date
from pathlib import Path

import httpx

from legalize_cli.cache import DiskCache
from legalize_cli.http import GitHubClient


def test_put_and_get_contents_roundtrips(tmp_path: Path) -> None:
    cache = DiskCache(tmp_path)
    cache.put_contents("legalize-kr/legalize-kr", "kr/민법/법률.md", date(2017, 10, 31), b"body-v1")

    got = cache.get_contents("legalize-kr/legalize-kr", "kr/민법/법률.md", date(2017, 10, 31))

    assert got == b"body-v1"


def test_get_contents_returns_none_when_missing(tmp_path: Path) -> None:
    cache = DiskCache(tmp_path)
    assert cache.get_contents("repo", "path.md", date(2020, 1, 1)) is None


def test_contents_ttl_expires(tmp_path: Path) -> None:
    cache = DiskCache(tmp_path)
    cache.put_contents("r", "p.md", date(2020, 1, 1), b"x")

    # "now" is 8 days in the future → contents TTL (7d) expired.
    future = time.time() + 8 * 24 * 60 * 60
    assert cache.get_contents("r", "p.md", date(2020, 1, 1), now=future) is None

    # Within TTL: still served.
    assert cache.get_contents("r", "p.md", date(2020, 1, 1), now=time.time()) == b"x"


def test_path_date_key_survives_sha_rewrite(tmp_path: Path) -> None:
    """Simulate force-push: two writes for same (repo,path,date) return first body unless overwritten."""
    cache = DiskCache(tmp_path)
    cache.put_contents("r", "p.md", date(2020, 1, 1), b"body-from-sha-A")

    # Second write under a "rewritten SHA" but same (path, date) → overwrites
    # the same cache slot deterministically. Key insight: no SHA-keyed slot
    # was created in the first place, so a rewrite can't orphan a cache entry.
    cache.put_contents("r", "p.md", date(2020, 1, 1), b"body-from-sha-B")

    got = cache.get_contents("r", "p.md", date(2020, 1, 1))
    assert got == b"body-from-sha-B"


def test_invalidate_path_contents_removes_all_date_entries(tmp_path: Path) -> None:
    cache = DiskCache(tmp_path)
    cache.put_contents("r", "p.md", date(2015, 1, 1), b"a")
    cache.put_contents("r", "p.md", date(2020, 1, 1), b"b")
    cache.put_contents("r", "p.md", date(2024, 1, 1), b"c")
    # Unrelated path keeps its entry.
    cache.put_contents("r", "other.md", date(2020, 1, 1), b"z")

    removed = cache.invalidate_path_contents("r", "p.md")

    assert removed == 3
    assert cache.get_contents("r", "p.md", date(2020, 1, 1)) is None
    assert cache.get_contents("r", "other.md", date(2020, 1, 1)) == b"z"


def test_etag_put_and_get(tmp_path: Path) -> None:
    cache = DiskCache(tmp_path)
    cache.put_etag("https://api.github.com/x", b'{"ok": true}', '"abc123"')

    got = cache.get_with_etag("https://api.github.com/x")

    assert got is not None
    assert got.body == b'{"ok": true}'
    assert got.etag == '"abc123"'


def test_etag_304_round_trip_reuses_cache(tmp_path: Path) -> None:
    """A 304 response must be served from cache with zero JSON re-parse surprises."""
    cache = DiskCache(tmp_path)
    stored_body = b'{"cached": "hit"}'
    cache.put_etag(
        "https://api.github.com/repos/a/b/git/trees/HEAD",
        stored_body,
        '"etag-1"',
    )

    calls: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append({"if-none-match": request.headers.get("If-None-Match")})
        return httpx.Response(304, headers={"ETag": '"etag-1"'})

    client = GitHubClient(
        transport=httpx.MockTransport(handler),
        token=None,
        token_source="none",
        cache=cache,
    )

    got = client.get_json("/repos/a/b/git/trees/HEAD", cache_ttl=3600)

    assert got == {"cached": "hit"}
    assert calls[0]["if-none-match"] == '"etag-1"'
    client.close()


def test_etag_200_stores_body_for_next_request(tmp_path: Path) -> None:
    cache = DiskCache(tmp_path)
    fresh_body = b'{"fresh": "miss"}'

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=fresh_body,
            headers={"ETag": '"etag-new"', "Content-Type": "application/json"},
        )

    client = GitHubClient(
        transport=httpx.MockTransport(handler),
        token=None,
        token_source="none",
        cache=cache,
    )

    got = client.get_json("/repos/a/b/git/trees/HEAD", cache_ttl=3600)

    assert got == {"fresh": "miss"}
    cached = cache.get_with_etag("https://api.github.com/repos/a/b/git/trees/HEAD")
    assert cached is not None
    assert cached.etag == '"etag-new"'
    client.close()
