"""Integration tests for ``legalize precedents get`` and underlying fetch."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
from typer.testing import CliRunner

from legalize_cli.__main__ import app
from legalize_cli.http import GitHubClient
from legalize_cli.precedents.fetch import fetch_by_id_or_path

from .conftest import build_mock, install_client_factory

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _tree() -> dict:
    return json.loads((FIXTURES / "precedents" / "tree_precedents.json").read_text())


def test_fetch_by_path(sample_precedent_bytes) -> None:
    mock = build_mock({"/contents/": httpx.Response(200, content=sample_precedent_bytes)})
    client = GitHubClient(transport=mock.transport(), token=None, token_source="none")
    try:
        path, body = fetch_by_id_or_path(client, None, "민사/대법원/2000다10048.md")
    finally:
        client.close()

    assert path == "민사/대법원/2000다10048.md"
    assert body == sample_precedent_bytes


def test_fetch_by_사건번호(sample_precedent_bytes) -> None:
    tree_payload = _tree()
    mock = build_mock(
        {
            "/git/trees/": (200, tree_payload),
            "/contents/": httpx.Response(200, content=sample_precedent_bytes),
        }
    )
    client = GitHubClient(transport=mock.transport(), token=None, token_source="none")
    try:
        path, body = fetch_by_id_or_path(client, None, "2000다10048")
    finally:
        client.close()

    assert path == "민사/대법원/2000다10048.md"
    assert body == sample_precedent_bytes


def test_fetch_not_found() -> None:
    from legalize_cli.util.errors import NotFoundError

    mock = build_mock({"/git/trees/": (200, _tree())})
    client = GitHubClient(transport=mock.transport(), token=None, token_source="none")
    try:
        import pytest
        with pytest.raises(NotFoundError):
            fetch_by_id_or_path(client, None, "없는사건번호99999")
    finally:
        client.close()


def test_cli_precedents_get_json(sample_precedent_bytes, monkeypatch) -> None:
    tree_payload = _tree()
    mock = build_mock(
        {
            "/git/trees/": (200, tree_payload),
            "/contents/": httpx.Response(200, content=sample_precedent_bytes),
        }
    )
    install_client_factory(
        monkeypatch,
        lambda opts: (
            GitHubClient(transport=mock.transport(), token=None, token_source="none"),
            None,
        ),
    )

    result = CliRunner().invoke(app, ["precedents", "get", "2000다10048", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema_version"] == "1.0"
    assert payload["kind"] == "precedents.get"
    assert payload["path"] == "민사/대법원/2000다10048.md"
