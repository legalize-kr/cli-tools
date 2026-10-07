"""``GET /search/code`` wrapper — requires a GitHub token."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from ..http import GitHubClient
from ..util.errors import AuthError, LegalizeError

GITHUB_SEARCH_RESULT_LIMIT = 1000


class SearchIncompleteError(LegalizeError):
    """Raised when GitHub reports ``incomplete_results`` for code search."""

    exit_code = 11


class CodeMatch(BaseModel):
    """A single ``/search/code`` item."""

    model_config = ConfigDict(extra="ignore")

    path: str
    sha: str
    name: str
    html_url: Optional[str] = None
    repository: Optional[dict] = None


class CodeSearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: List[CodeMatch]
    total_count: int
    has_more: bool


def search_code(
    client: GitHubClient,
    query: str,
    *,
    repo: str,
    limit: int = 100,
) -> List[CodeMatch]:
    """Run a ``/search/code`` query restricted to ``repo``.

    :raises AuthError: if the client has no token attached.
    :raises SearchIncompleteError: if GitHub reports a timed-out search.
    """
    return search_code_detailed(client, query, repo=repo, limit=limit).items


def search_code_detailed(
    client: GitHubClient,
    query: str,
    *,
    repo: str,
    limit: int = 100,
) -> CodeSearchResult:
    """Run code search while preserving count and pagination metadata."""
    if client.token_source == "none":
        raise AuthError(
            "/search/code requires a GitHub token; set GITHUB_TOKEN or pass --token"
        )

    q = f"{query} repo:{repo} extension:md"
    target = min(max(limit, 1), GITHUB_SEARCH_RESULT_LIMIT)
    per_page = min(target, 100)
    page = 1
    items: list[dict] = []
    reported_total = 0

    while len(items) < target:
        payload = client.get_json(
            "/search/code",
            params={"q": q, "per_page": per_page, "page": page},
            cache_ttl=3600,
        )
        if payload.get("incomplete_results"):
            raise SearchIncompleteError(
                "GitHub code search returned incomplete_results=true; "
                "retry with --strategy tree"
            )

        page_items = payload.get("items", [])
        items.extend(page_items)

        total_count = min(payload.get("total_count", 0), GITHUB_SEARCH_RESULT_LIMIT)
        reported_total = total_count
        if len(items) >= total_count or len(page_items) < per_page:
            break
        page += 1

    parsed = [CodeMatch.model_validate(item) for item in items[:target]]
    return CodeSearchResult(
        items=parsed,
        total_count=reported_total,
        has_more=reported_total > len(parsed),
    )


__all__ = [
    "CodeMatch",
    "CodeSearchResult",
    "GITHUB_SEARCH_RESULT_LIMIT",
    "SearchIncompleteError",
    "search_code",
    "search_code_detailed",
]
