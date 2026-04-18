"""Verify the runtime KST (+09:00) author-date invariant per plan §9 Step 2."""

from __future__ import annotations

import copy

import httpx
import pytest

from legalize_cli.http import GitHubClient
from legalize_cli.laws.revisions import get_revisions
from legalize_cli.util.errors import LegalizeError


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


def test_utc_author_date_raises(commits_fixture) -> None:
    bad = copy.deepcopy(commits_fixture)
    # Swap the NEWEST commit's author_date to a UTC offset — get_revisions
    # checks commits[0] which is newest-first.
    bad[0]["commit"]["author"]["date"] = "2022-12-27T03:00:00+00:00"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=bad)

    client = GitHubClient(
        transport=httpx.MockTransport(handler), token=None, token_source="none"
    )
    try:
        with pytest.raises(LegalizeError, match="timezone invariant broken"):
            get_revisions(client, None, "kr/민법/법률.md")
    finally:
        client.close()
