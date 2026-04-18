"""Parse a stored GitHub commits API response fixture."""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from legalize_cli.github.commits import list_commits
from legalize_cli.http import GitHubClient

FIXTURE = Path(__file__).parent.parent / "fixtures" / "github" / "commits_mingbeop.json"


def _transport(payload: list[dict]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    return httpx.MockTransport(handler)


def test_list_commits_parses_fixture_and_preserves_tz() -> None:
    payload = json.loads(FIXTURE.read_text())
    client = GitHubClient(transport=_transport(payload), token=None, token_source="none")

    commits = list_commits(client, "legalize-kr", "legalize-kr", "kr/민법/법률.md")

    assert len(commits) == 3
    first = commits[0]
    # SHA round-trips verbatim.
    assert first.sha.startswith("ca7d5c5")
    # author_date carries +09:00 offset (critical: §5 Step 2 invariant).
    assert first.author_date.utcoffset() is not None
    assert first.author_date.utcoffset().total_seconds() == 9 * 3600
    # committer_date independently parsed and preserved as UTC.
    assert first.committer_date.utcoffset().total_seconds() == 0


def test_list_commits_message_preserved() -> None:
    payload = json.loads(FIXTURE.read_text())
    client = GitHubClient(transport=_transport(payload), token=None, token_source="none")

    commits = list_commits(client, "legalize-kr", "legalize-kr", "kr/민법/법률.md")

    assert "민법" in commits[0].message
