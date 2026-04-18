"""Integration test for ``legalize laws as-of`` using the commits fixture."""

from __future__ import annotations

import json

import httpx
from typer.testing import CliRunner

from legalize_cli.__main__ import app
from legalize_cli.http import GitHubClient
from legalize_cli.laws.asof import resolve_as_of
from legalize_cli.laws.revisions import get_revisions
from datetime import date

from .conftest import install_client_factory


def _install_mock(monkeypatch, commits_fixture, tree_fixture, body: bytes) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/commits" in url:
            return httpx.Response(200, json=commits_fixture)
        if "/git/trees/" in url:
            return httpx.Response(200, json=tree_fixture)
        if "/contents/" in url:
            return httpx.Response(200, content=body)
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


def test_resolve_2015_06_01_picks_2013_commit(commits_fixture) -> None:
    """2015-06-01 sits between 2013 and 2021 commits; must pick 2017 (before 2021)."""
    # Fixture commits: 2022-12-27, 2021-01-26, 2017-10-31.
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=commits_fixture)

    client = GitHubClient(
        transport=httpx.MockTransport(handler), token=None, token_source="none"
    )
    try:
        commits = get_revisions(client, None, "kr/민법/법률.md")
    finally:
        client.close()

    chosen = resolve_as_of(commits, date(2020, 1, 1))
    assert chosen is not None
    # 2020-01-01 is after 2017-10-31 but before 2021-01-26 → 2017 commit.
    assert chosen.sha.startswith("ca7d5c5")


def test_asof_cli_json(
    monkeypatch, commits_fixture, tree_fixture, mingbeop_2024_bytes
) -> None:
    _install_mock(monkeypatch, commits_fixture, tree_fixture, mingbeop_2024_bytes)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "laws",
            "as-of",
            "--date",
            "2022-12-31",
            "--category",
            "법률",
            "--json",
            "--limit",
            "5",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema_version"] == "1.0"
    assert payload["kind"] == "laws.asof"
    assert payload["requested_date"] == "2022-12-31"
    # Every law in the tree fixture should resolve to the same fixture commit
    # (we wired the same commits payload for every /commits call).
    for item in payload["items"]:
        assert item["resolved_commit_date"] == "2022-12-27"
