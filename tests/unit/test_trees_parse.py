"""Parse a stored GitHub tree response fixture."""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from legalize_cli.github.trees import get_tree
from legalize_cli.http import GitHubClient

FIXTURE = Path(__file__).parent.parent / "fixtures" / "github" / "tree_laws_small.json"


def _transport(payload: dict) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    return httpx.MockTransport(handler)


def test_get_tree_counts_entries() -> None:
    payload = json.loads(FIXTURE.read_text())
    client = GitHubClient(transport=_transport(payload), token=None, token_source="none")

    entries = get_tree(client, "legalize-kr", "legalize-kr", "HEAD")

    assert len(entries) == 10
    blobs = [e for e in entries if e.type == "blob"]
    trees = [e for e in entries if e.type == "tree"]
    assert len(blobs) == 8
    assert len(trees) == 2


def test_get_tree_preserves_korean_paths() -> None:
    payload = json.loads(FIXTURE.read_text())
    client = GitHubClient(transport=_transport(payload), token=None, token_source="none")

    entries = get_tree(client, "legalize-kr", "legalize-kr", "HEAD")
    paths = {e.path for e in entries}

    assert "kr/민법/법률.md" in paths
    assert "kr/주택법/시행규칙.md" in paths
