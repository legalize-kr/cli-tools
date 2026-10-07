from __future__ import annotations

import httpx
import pytest

from legalize_cli.http import GitHubClient
from legalize_cli.services.limits import RequestBudget
from legalize_cli.util.errors import RequestBudgetExceededError


def test_budget_counts_outbound_http_and_stops_before_second_request() -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, json={"ok": True})

    client = GitHubClient(
        token=None, token_source="none", transport=httpx.MockTransport(handler),
        budget=RequestBudget(max_requests=1),
    )
    try:
        assert client.get_json("/one")["ok"]
        with pytest.raises(RequestBudgetExceededError):
            client.get_json("/two")
    finally:
        client.close()
    assert len(calls) == 1
