"""Unit tests for rate-limit pre-flight budget refusal."""

from __future__ import annotations

from datetime import datetime, timezone

import httpx
import pytest

from legalize_cli.http import GitHubClient
from legalize_cli.rate_limit import RateLimit
from legalize_cli.search.tree_filter import tree_filter_items
from legalize_cli.util.errors import LegalizeError


_TREE_PAYLOAD = {
    "sha": "deadbeef",
    "truncated": False,
    "tree": [
        {"path": f"kr/law{i}/법률.md", "mode": "100644", "type": "blob", "sha": f"s{i}", "size": 1000}
        for i in range(50)
    ],
}


def _client_with_remaining(remaining: int) -> GitHubClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_TREE_PAYLOAD,
            headers={
                "X-RateLimit-Limit": "60",
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": "9999999999",
                "X-RateLimit-Used": "0",
            },
        )

    return GitHubClient(
        transport=httpx.MockTransport(handler), token=None, token_source="none"
    )


def test_refuses_when_budget_insufficient() -> None:
    # 50 entries → needs 2*50 = 100 fetches; remaining=10 → refuse.
    client = _client_with_remaining(10)
    try:
        with pytest.raises(LegalizeError, match="rate-limit budget"):
            tree_filter_items(
                client, None, "민법", heavy_content_scan=True, yes_exhaust=False
            )
    finally:
        client.close()


def test_allows_when_yes_exhaust() -> None:
    client = _client_with_remaining(10)

    # yes_exhaust=True bypasses the budget gate; we let the actual fetches
    # proceed. Each non-matching blob will 404, so we intercept via a mock
    # that responds 200 to every content fetch.
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/git/trees/" in url:
            return httpx.Response(
                200,
                json=_TREE_PAYLOAD,
                headers={
                    "X-RateLimit-Remaining": "10",
                    "X-RateLimit-Limit": "60",
                    "X-RateLimit-Reset": "9999999999",
                    "X-RateLimit-Used": "0",
                },
            )
        return httpx.Response(200, content=b"body")

    client._client = httpx.Client(transport=httpx.MockTransport(handler), headers={})

    try:
        # Must not raise.
        items = tree_filter_items(
            client, None, "law1", heavy_content_scan=True, yes_exhaust=True
        )
    finally:
        client.close()
    assert isinstance(items, list)
