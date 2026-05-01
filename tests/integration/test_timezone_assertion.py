"""Verify commit dates are normalized to KST before revision resolution."""

from __future__ import annotations

import copy

import httpx

from legalize_cli.http import GitHubClient
from legalize_cli.laws.revisions import get_revisions


def test_plus_0900_passes(commits_fixture) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=commits_fixture)

    client = GitHubClient(
        transport=httpx.MockTransport(handler), token=None, token_source="none"
    )
    try:
        commits = get_revisions(client, None, "kr/민법/법률.md")
    finally:
        client.close()

    assert len(commits) == 3
    # All fixture commits use +09:00 author date; no raise.


def test_utc_author_date_is_normalized_to_kst(commits_fixture) -> None:
    payload = copy.deepcopy(commits_fixture)
    payload[0]["commit"]["author"]["date"] = "2022-12-27T03:00:00+00:00"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    client = GitHubClient(
        transport=httpx.MockTransport(handler), token=None, token_source="none"
    )
    try:
        commits = get_revisions(client, None, "kr/민법/법률.md")
    finally:
        client.close()

    assert commits[0].author_date.isoformat() == "2022-12-27T12:00:00+09:00"
