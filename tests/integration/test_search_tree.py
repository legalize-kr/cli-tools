"""Integration test for tree-filter fallback (no token)."""

from __future__ import annotations

import json

import httpx
from typer.testing import CliRunner

from legalize_cli.__main__ import app
from legalize_cli.http import GitHubClient

from .conftest import install_client_factory


def test_search_no_token_uses_tree(monkeypatch, tree_fixture) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/git/trees/" in url:
            return httpx.Response(200, json=tree_fixture)
        return httpx.Response(404, json={"message": f"no route for {url}"})

    install_client_factory(
        monkeypatch,
        lambda opts: (
            GitHubClient(transport=httpx.MockTransport(handler), token=None, token_source="none"),
            None,
        ),
    )

    runner = CliRunner()
    result = runner.invoke(
        app, ["search", "민법", "--in", "laws", "--json"]
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema_version"] == "1.0"
    assert payload["strategy_used"] == "tree"
    assert payload["token_used"] is False
    # 민법/법률.md + 민법/시행령.md should match.
    paths = {item["path"] for item in payload["items"]}
    assert "kr/민법/법률.md" in paths
    # warnings array present
    assert isinstance(payload["warnings"], list)
    assert any("GITHUB_TOKEN" in w for w in payload["warnings"])
