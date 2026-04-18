"""Tests for :mod:`legalize_cli.rate_limit`."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest

from legalize_cli.http import GitHubClient
from legalize_cli.rate_limit import RateLimit, parse_reset
from legalize_cli.util.errors import RateLimitError


def test_parse_reset_epoch() -> None:
    got = parse_reset("1712131200")
    assert got == datetime.fromtimestamp(1712131200, tz=timezone.utc)


def test_parse_reset_iso() -> None:
    got = parse_reset("2026-04-16T12:34:56+00:00")
    assert got.year == 2026 and got.month == 4 and got.day == 16
    assert got.tzinfo is not None


def test_from_headers_parses_standard_payload() -> None:
    headers = {
        "X-RateLimit-Limit": "5000",
        "X-RateLimit-Remaining": "4987",
        "X-RateLimit-Reset": "1712131200",
        "X-RateLimit-Used": "13",
    }

    rl = RateLimit.from_headers(headers)

    assert rl is not None
    assert rl.limit == 5000
    assert rl.remaining == 4987
    assert rl.used == 13
    assert rl.reset == datetime.fromtimestamp(1712131200, tz=timezone.utc)


def test_from_headers_case_insensitive() -> None:
    headers = {
        "x-ratelimit-limit": "60",
        "x-ratelimit-remaining": "59",
        "x-ratelimit-reset": "1712131200",
        "x-ratelimit-used": "1",
    }

    rl = RateLimit.from_headers(headers)

    assert rl is not None
    assert rl.limit == 60


def test_from_headers_returns_none_when_missing() -> None:
    assert RateLimit.from_headers({}) is None
    assert RateLimit.from_headers({"X-RateLimit-Limit": "5000"}) is None


def test_http_client_raises_rate_limit_error_on_403_with_zero_remaining() -> None:
    """403 + remaining=0 must raise :class:`RateLimitError`, not a generic HTTP error."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            headers={
                "X-RateLimit-Limit": "60",
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": "1712131200",
                "X-RateLimit-Used": "60",
            },
            json={"message": "API rate limit exceeded"},
        )

    transport = httpx.MockTransport(handler)
    client = GitHubClient(token=None, token_source="none", transport=transport)

    with pytest.raises(RateLimitError):
        client.get_json("/rate_limit")

    client.close()


def test_http_client_records_rate_limit_snapshot_on_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={
                "X-RateLimit-Limit": "5000",
                "X-RateLimit-Remaining": "4999",
                "X-RateLimit-Reset": "1712131200",
                "X-RateLimit-Used": "1",
            },
            json={"ok": True},
        )

    transport = httpx.MockTransport(handler)
    client = GitHubClient(token="ghp_test", token_source="flag", transport=transport)
    client.get_json("/rate_limit")

    assert client.last_rate_limit is not None
    assert client.last_rate_limit.remaining == 4999
    client.close()
