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


def test_list_commits_parses_fixture_and_normalizes_to_kst() -> None:
    payload = json.loads(FIXTURE.read_text())
    client = GitHubClient(transport=_transport(payload), token=None, token_source="none")

    commits = list_commits(client, "legalize-kr", "legalize-kr", "kr/민법/법률.md")

    assert len(commits) == 3
    first = commits[0]
    # SHA round-trips verbatim.
    assert first.sha.startswith("ca7d5c5")
    # GitHub commit dates are normalized to KST for date-based law lookups.
    assert first.author_date.utcoffset() is not None
    assert first.author_date.utcoffset().total_seconds() == 9 * 3600
    assert first.committer_date.utcoffset().total_seconds() == 9 * 3600
    assert first.committer_date.hour == 12


def test_list_commits_converts_github_utc_author_date_to_kst() -> None:
    payload = [
        {
            "sha": "abc123",
            "commit": {
                "author": {"date": "2026-04-30T03:00:00Z"},
                "committer": {"date": "2026-04-30T04:30:00Z"},
                "message": "UTC from GitHub",
            },
        }
    ]
    client = GitHubClient(transport=_transport(payload), token=None, token_source="none")

    commit = list_commits(client, "legalize-kr", "legalize-kr", "kr/민법/법률.md")[0]

    assert commit.author_date.isoformat() == "2026-04-30T12:00:00+09:00"
    assert commit.committer_date.isoformat() == "2026-04-30T13:30:00+09:00"


def test_list_commits_message_preserved() -> None:
    payload = json.loads(FIXTURE.read_text())
    client = GitHubClient(transport=_transport(payload), token=None, token_source="none")

    commits = list_commits(client, "legalize-kr", "legalize-kr", "kr/민법/법률.md")

    assert "민법" in commits[0].message
