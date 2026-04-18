"""Integration test for ``legalize precedents get`` and underlying fetch."""

from __future__ import annotations

import json

import httpx
from typer.testing import CliRunner

from legalize_cli.__main__ import app
from legalize_cli.http import GitHubClient
from legalize_cli.precedents.fetch import fetch_by_id_or_path
from legalize_cli.precedents.index import fetch_precedent_index

from .conftest import CapturingMock, build_mock, install_client_factory


def _make_routes(index_payload: dict, body: bytes) -> CapturingMock:
    """raw CDN for the index; /contents/ for the precedent body."""
    index_bytes = json.dumps(index_payload, ensure_ascii=False).encode("utf-8")
    return build_mock(
        {
            "raw.githubusercontent.com": (200, index_bytes),
            "/contents/": httpx.Response(200, content=body),
        }
    )


def test_fetch_by_사건번호(precedent_metadata_fixture, sample_precedent_bytes) -> None:
    mock = _make_routes(precedent_metadata_fixture, sample_precedent_bytes)
    client = GitHubClient(transport=mock.transport(), token=None, token_source="none")
    try:
        index = fetch_precedent_index(client)
        path, body = fetch_by_id_or_path(client, None, index, "2000다10048")
    finally:
        client.close()

    assert path == "민사/대법원/2000다10048.md"
    assert body == sample_precedent_bytes
    # Critical: no /contents/ call for metadata.json — the ~34MB file MUST
    # come from raw.githubusercontent.com.
    for url in mock.urls():
        if "metadata.json" in url:
            assert "contents" not in url, f"metadata.json fetched via /contents/: {url}"


def test_fetch_by_판례일련번호(precedent_metadata_fixture, sample_precedent_bytes) -> None:
    mock = _make_routes(precedent_metadata_fixture, sample_precedent_bytes)
    client = GitHubClient(transport=mock.transport(), token=None, token_source="none")
    try:
        index = fetch_precedent_index(client)
        path, body = fetch_by_id_or_path(client, None, index, "160450")
    finally:
        client.close()

    assert path == "민사/대법원/2000다10048.md"
    assert body == sample_precedent_bytes


def test_cli_precedents_get_json(
    precedent_metadata_fixture, sample_precedent_bytes, monkeypatch
) -> None:
    mock = _make_routes(precedent_metadata_fixture, sample_precedent_bytes)

    install_client_factory(
        monkeypatch,
        lambda opts: (
            GitHubClient(transport=mock.transport(), token=None, token_source="none"),
            None,
        ),
    )

    runner = CliRunner()
    result = runner.invoke(app, ["precedents", "get", "2000다10048", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema_version"] == "1.0"
    assert payload["kind"] == "precedents.get"
    assert payload["path"] == "민사/대법원/2000다10048.md"
