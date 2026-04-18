"""Integration test for ``legalize laws article``."""

from __future__ import annotations

import json

import httpx
from typer.testing import CliRunner

from legalize_cli.__main__ import app
from legalize_cli.http import GitHubClient

from .conftest import install_client_factory


def _install_mock(monkeypatch, commits_fixture, body: bytes) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/commits" in url:
            return httpx.Response(200, json=commits_fixture)
        if "/contents/" in url:
            return httpx.Response(200, content=body)
        return httpx.Response(404, json={"message": f"no route for {url}"})

    install_client_factory(
        monkeypatch,
        lambda opts: (
            GitHubClient(transport=httpx.MockTransport(handler), token=None, token_source="none"),
            None,
        ),
    )


def test_article_json(monkeypatch, commits_fixture, mingbeop_2024_bytes) -> None:
    _install_mock(monkeypatch, commits_fixture, mingbeop_2024_bytes)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "laws",
            "article",
            "민법",
            "제839조의2",
            "--date",
            "2024-01-01",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema_version"] == "1.0"
    assert payload["kind"] == "laws.article"
    assert payload["article_no"]["조"] == "839"
    assert payload["article_no"]["의"] == "2"
    assert payload["law"] == "민법"
    assert payload["category"] == "법률"
    assert "재산분할" in payload["content"]
    assert payload["parent_structure"]


def test_article_not_found(monkeypatch, commits_fixture, mingbeop_2024_bytes) -> None:
    _install_mock(monkeypatch, commits_fixture, mingbeop_2024_bytes)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "laws",
            "article",
            "민법",
            "제9999조",
            "--date",
            "2024-01-01",
            "--json",
        ],
    )
    # NotFoundError -> exit code 4.
    assert result.exit_code == 4, result.output
