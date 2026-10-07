"""Thin wrapper around :mod:`legalize_cli.github.search_code`.

Normalizes the query and packages results in the shape the CLI's JSON output
expects. The underlying ``search_code`` raises :class:`AuthError` if no token
is present; we let that propagate so the command layer can fall back to a
different strategy.
"""

from __future__ import annotations

from typing import Dict, List

from ..github.search_code import CodeSearchResult, search_code, search_code_detailed
from ..http import GitHubClient
from .unicode import normalize_query


def code_search_items(
    client: GitHubClient,
    query: str,
    *,
    repo: str,
    source: str,
    limit: int = 100,
) -> List[Dict[str, str]]:
    """Return normalized items for the JSON ``items[]`` payload."""
    matches = search_code(client, normalize_query(query), repo=repo, limit=limit)
    return [
        {
            "source": source,
            "path": m.path,
            "match_type": "body",
        }
        for m in matches
    ]


def code_search_detailed(
    client: GitHubClient, query: str, *, repo: str, limit: int = 100
) -> CodeSearchResult:
    return search_code_detailed(client, normalize_query(query), repo=repo, limit=limit)


__all__ = ["code_search_detailed", "code_search_items"]
