"""Integration tests for the updated fetch_by_id_or_path lookup chain.

Four scenarios (all using mocked GitHub API):
  1. new_grammar  — composite filename ``*--{caseno}.md`` found in tree
  2. legacy       — old ``{caseno}.md`` filename found after new-grammar miss
  3. legacy_map   — neither grammar matches; fallback via legacy-paths.json
  4. disambiguation — >1 new-grammar hits raise NotFoundError
"""

from __future__ import annotations

import httpx
import pytest

from legalize_cli.http import GitHubClient
from legalize_cli.precedents.fetch import fetch_by_id_or_path
from legalize_cli.util.errors import NotFoundError

from .conftest import build_mock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_tree(paths: list[str]) -> dict:
    """Build a minimal GitHub tree payload from a list of blob paths."""
    tree = [
        {"path": p, "type": "blob", "sha": f"sha_{i:04d}", "size": 100}
        for i, p in enumerate(paths)
    ]
    return {"sha": "root", "truncated": False, "tree": tree}


SAMPLE_BYTES = b"---\n\xec\x82\xac\xea\xb1\xb4\xeb\xb2\x88\xed\x98\xb8: 2022\xeb\x8b\xa412345\n---\n\n# \xed\x8c\x90\xeb\xa1\x80"

# SEP = "--" as determined by pipeline preflight
SEP = "--"


# ---------------------------------------------------------------------------
# Scenario 1: New composite grammar
# ---------------------------------------------------------------------------

def test_new_grammar_lookup() -> None:
    """Tree contains composite filename; lookup by caseno finds it."""
    tree = _make_tree([
        f"민사/대법원/대법원{SEP}2022-03-15{SEP}2022다12345.md",
        f"민사/대법원/서울중앙지방법원{SEP}2021-06-01{SEP}2021가합11111.md",
    ])
    mock = build_mock(
        {
            "/git/trees/": (200, tree),
            "/contents/": httpx.Response(200, content=SAMPLE_BYTES),
        }
    )
    client = GitHubClient(transport=mock.transport(), token=None, token_source="none")
    try:
        path, body = fetch_by_id_or_path(client, None, "2022다12345")
    finally:
        client.close()

    assert path == f"민사/대법원/대법원{SEP}2022-03-15{SEP}2022다12345.md"
    assert body == SAMPLE_BYTES


# ---------------------------------------------------------------------------
# Scenario 2: Legacy fallback (no composite match, exact caseno.md found)
# ---------------------------------------------------------------------------

def test_legacy_fallback_lookup() -> None:
    """Tree has only legacy filename; new-grammar miss falls through to legacy."""
    tree = _make_tree([
        "민사/대법원/2000다10048.md",
        "형사/대법원/2018도11111.md",
    ])
    mock = build_mock(
        {
            "/git/trees/": (200, tree),
            "/contents/": httpx.Response(200, content=SAMPLE_BYTES),
        }
    )
    client = GitHubClient(transport=mock.transport(), token=None, token_source="none")
    try:
        path, body = fetch_by_id_or_path(client, None, "2000다10048")
    finally:
        client.close()

    assert path == "민사/대법원/2000다10048.md"
    assert body == SAMPLE_BYTES


# ---------------------------------------------------------------------------
# Scenario 3: legacy-paths.json fallback
# ---------------------------------------------------------------------------

def test_legacy_map_fallback() -> None:
    """Neither grammar nor legacy filename in tree; legacy-map resolves to new path."""
    new_path = f"민사/대법원/대법원{SEP}2000-09-27{SEP}2000다55555.md"
    legacy_map = [
        {
            "판례일련번호": "99001",
            "old_path": "민사/대법원/2000다55555.md",
            "new_path": new_path,
        }
    ]
    # Deliberately use an empty tree to force the legacy-map branch.
    empty_tree = _make_tree([])
    mock = build_mock(
        {
            "/git/trees/": (200, empty_tree),
            "/contents/": httpx.Response(200, content=SAMPLE_BYTES),
        }
    )
    client = GitHubClient(transport=mock.transport(), token=None, token_source="none")
    try:
        path, body = fetch_by_id_or_path(
            client, None, "2000다55555", legacy_map=legacy_map
        )
    finally:
        client.close()

    assert path == new_path
    assert body == SAMPLE_BYTES


# ---------------------------------------------------------------------------
# Scenario 4: Disambiguation (>1 composite matches)
# ---------------------------------------------------------------------------

def test_disambiguation_raises() -> None:
    """Two composite entries share the same caseno → NotFoundError with guidance."""
    tree = _make_tree([
        f"민사/대법원/대법원{SEP}2022-01-10{SEP}2022다99999.md",
        f"민사/하급심/서울중앙지방법원{SEP}2022-01-10{SEP}2022다99999.md",
    ])
    mock = build_mock({"/git/trees/": (200, tree)})
    client = GitHubClient(transport=mock.transport(), token=None, token_source="none")
    try:
        with pytest.raises(NotFoundError) as exc_info:
            fetch_by_id_or_path(client, None, "2022다99999")
    finally:
        client.close()

    msg = str(exc_info.value)
    assert "ambiguous" in msg
    assert "2022다99999" in msg
    assert "2" in msg  # reports the hit count
