"""Integration test for code-search strategy (token-backed)."""

from __future__ import annotations

import json

import httpx
from typer.testing import CliRunner

from legalize_cli.__main__ import app
from legalize_cli.http import GitHubClient

from .conftest import install_client_factory


def test_search_with_token_uses_code_strategy(monkeypatch) -> None:
    search_payload = {
        "total_count": 1,
        "items": [
            {
                "path": "kr/민법/법률.md",
                "sha": "abc123",
                "name": "법률.md",
                "html_url": "https://github.com/legalize-kr/legalize-kr/blob/main/kr/민법/법률.md",
            }
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/search/code" in url:
            return httpx.Response(200, json=search_payload)
        # Precedents index fetched via raw CDN (scope=all fallbacks).
        if "raw.githubusercontent.com" in url:
            return httpx.Response(200, content=b"{}")
        return httpx.Response(404, json={"message": f"no route for {url}"})

    install_client_factory(
        monkeypatch,
        lambda opts: (
            GitHubClient(
                transport=httpx.MockTransport(handler),
                token="fake-token",
                token_source="flag",
            ),
            None,
        ),
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["search", "재산분할", "--in", "laws", "--json", "--token", "fake-token"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema_version"] == "1.0"
    assert payload["kind"] == "search.result"
    assert payload["strategy_used"] == "code"
    assert payload["token_used"] is True
    assert payload["items"] == [
        {"source": "laws", "path": "kr/민법/법률.md", "match_type": "body"}
    ]
