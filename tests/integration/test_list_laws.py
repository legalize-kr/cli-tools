"""Integration test for ``legalize laws list`` + underlying enumerator."""

from __future__ import annotations

import json

import httpx
from typer.testing import CliRunner

from legalize_cli.__main__ import app
from legalize_cli.http import GitHubClient
from legalize_cli.laws.list import enumerate_laws

from .conftest import install_client_factory


def _make_client(tree_payload: dict) -> GitHubClient:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=tree_payload)

    return GitHubClient(
        transport=httpx.MockTransport(handler),
        token=None,
        token_source="none",
    )


def test_enumerate_laws_filters_paths(tree_fixture) -> None:
    client = _make_client(tree_fixture)
    try:
        laws = enumerate_laws(client)
    finally:
        client.close()

    # README.md, metadata.json, kr/.gitkeep, .github/* filtered out.
    paths = {e.path for e in laws}
    assert "README.md" not in paths
    assert "metadata.json" not in paths
    assert "kr/.gitkeep" not in paths
    assert not any(p.startswith(".github") for p in paths)

    # All four canonical categories must appear.
    categories = {e.category for e in laws}
    assert categories == {"법률", "시행령", "시행규칙", "대통령령"}


def test_enumerate_laws_count_matches_fixture(tree_fixture) -> None:
    client = _make_client(tree_fixture)
    try:
        laws = enumerate_laws(client)
    finally:
        client.close()

    # Fixture has 17 blobs under kr/ matching canonical law paths:
    # 7 법률 + 6 시행령 + 2 시행규칙 + 2 대통령령 = 17.
    assert len(laws) == 17


def test_pretty_output_exit_zero(tree_fixture, monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=tree_fixture)

    install_client_factory(
        monkeypatch,
        lambda opts: (
            GitHubClient(
                transport=httpx.MockTransport(handler),
                token=None,
                token_source="none",
            ),
            None,
        ),
    )

    runner = CliRunner()
    result = runner.invoke(app, ["laws", "list", "--category", "법률"])

    assert result.exit_code == 0, result.output
    assert "민법" in result.output


def test_json_output_has_schema_version(tree_fixture, monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=tree_fixture)

    install_client_factory(
        monkeypatch,
        lambda opts: (
            GitHubClient(
                transport=httpx.MockTransport(handler),
                token=None,
                token_source="none",
            ),
            None,
        ),
    )

    runner = CliRunner()
    result = runner.invoke(
        app, ["laws", "list", "--category", "법률", "--json"]
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema_version"] == "1.0"
    assert payload["kind"] == "laws.list"
    assert "items" in payload
    # All canonical law filenames have a 법률 variant except 대통령령-only fixtures.
    assert all(item["category"] == "법률" for item in payload["items"])
