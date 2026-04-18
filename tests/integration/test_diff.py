"""Integration test for ``legalize laws diff``."""

from __future__ import annotations

import copy
import json

import httpx
from typer.testing import CliRunner

from legalize_cli.__main__ import app
from legalize_cli.http import GitHubClient

from .conftest import install_client_factory


def test_diff_2015_vs_2024(
    monkeypatch, commits_fixture, mingbeop_2015_bytes, mingbeop_2024_bytes
) -> None:
    """2015 vs 2024 민법: 제839조의2 modified, 제841조의2 added, 일부 동일."""

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/commits" in url:
            # Return the same commits payload regardless of law path.
            return httpx.Response(200, json=commits_fixture)
        if "/contents/" in url:
            # Pick the fixture based on the ref (sha) in the query string.
            if "ca7d5c5" in url or "bbbccc" in url:
                return httpx.Response(200, content=mingbeop_2015_bytes)
            return httpx.Response(200, content=mingbeop_2024_bytes)
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
        app,
        [
            "laws",
            "diff",
            "민법",
            "민법",
            "--date-a",
            "2017-11-01",  # picks 2017 commit (ca7d5c5)
            "--date-b",
            "2024-01-01",  # picks 2022 commit (cccbbb)
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["schema_version"] == "1.0"
    assert payload["kind"] == "laws.diff"
    assert payload["mode"] == "article"

    statuses = {
        (c["article_no"]["조"], c["article_no"].get("의"), c["status"])
        for c in payload["changes"]
    }
    # 제839조의2 body changed → modified.
    assert any(
        jo == "839" and ui == "2" and status == "modified"
        for jo, ui, status in statuses
    )
    # 제841조의2 is only in 2024 → added.
    assert any(
        jo == "841" and ui == "2" and status == "added"
        for jo, ui, status in statuses
    )


def test_cross_statute_warning_to_stderr(
    monkeypatch, commits_fixture, mingbeop_2015_bytes, mingbeop_2024_bytes
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/commits" in url:
            return httpx.Response(200, json=commits_fixture)
        if "/contents/" in url:
            if "민법" in url:
                return httpx.Response(200, content=mingbeop_2024_bytes)
            return httpx.Response(200, content=mingbeop_2015_bytes)
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
        app,
        [
            "laws",
            "diff",
            "민법",
            "상법",
            "--date-a",
            "2024-01-01",
            "--date-b",
            "2024-01-01",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    # Typer's default CliRunner merges stderr into result.output; the warning
    # is written via sys.stderr.write so it surfaces in the combined stream.
    assert "cross-statute" in result.output


def test_cross_statute_warning_suppressed(
    monkeypatch, commits_fixture, mingbeop_2015_bytes, mingbeop_2024_bytes
) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/commits" in url:
            return httpx.Response(200, json=commits_fixture)
        if "/contents/" in url:
            if "민법" in url:
                return httpx.Response(200, content=mingbeop_2024_bytes)
            return httpx.Response(200, content=mingbeop_2015_bytes)
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
        app,
        [
            "laws",
            "diff",
            "민법",
            "상법",
            "--date-a",
            "2024-01-01",
            "--date-b",
            "2024-01-01",
            "--suppress-cross-statute-warning",
            "--json",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "cross-statute" not in result.output
