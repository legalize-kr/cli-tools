"""Tree-based helpers for Markdown document repos.

The administrative-rule and ordinance repos share the same terminal layout:
``.../{문서종류}/{문서명}/본문.md``. This module keeps that path parsing in one
place without changing the law/precedent-specific code paths.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from pydantic import BaseModel, ConfigDict

from .cache import DiskCache
from .config import DEFAULT_BRANCH, OWNER
from .github.contents import get_file_raw
from .github.trees import get_tree
from .http import GitHubClient
from .util.errors import AmbiguousMatchError, NotFoundError

BODY_FILENAME = "본문.md"


class TreeDocumentEntry(BaseModel):
    """A Markdown document entry parsed from a repository tree path."""

    model_config = ConfigDict(extra="forbid")

    path: str
    name: str
    category: str
    parents: List[str]


def enumerate_documents(
    client: GitHubClient,
    cache: Optional[DiskCache] = None,
    *,
    owner: str = OWNER,
    repo: str,
    ref: str = DEFAULT_BRANCH,
) -> List[TreeDocumentEntry]:
    """Return every ``.../{category}/{name}/본문.md`` document in ``repo``."""
    _ = cache
    entries = get_tree(client, owner, repo, ref)

    result: List[TreeDocumentEntry] = []
    for entry in entries:
        if entry.type != "blob":
            continue
        parts = entry.path.split("/")
        if len(parts) < 4 or parts[-1] != BODY_FILENAME:
            continue
        result.append(
            TreeDocumentEntry(
                path=entry.path,
                name=parts[-2],
                category=parts[-3],
                parents=parts[:-3],
            )
        )

    result.sort(key=lambda e: (e.category, e.parents, e.name))
    return result


def filter_and_paginate_documents(
    items: List[TreeDocumentEntry],
    *,
    category: Optional[str] = None,
    parent_contains: Optional[str] = None,
    parent0: Optional[str] = None,
    parent1: Optional[str] = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[int, List[TreeDocumentEntry], Optional[int]]:
    """Apply common document filters and pagination."""
    filtered = _filter_documents(
        items,
        category=category,
        parent_contains=parent_contains,
        parent0=parent0,
        parent1=parent1,
    )

    total = len(filtered)
    if page_size <= 0:
        raise ValueError("page_size must be positive")
    if page <= 0:
        raise ValueError("page must be 1-indexed")

    start = (page - 1) * page_size
    end = start + page_size
    window = filtered[start:end]
    next_page = page + 1 if end < total else None
    return total, window, next_page


def fetch_document_by_name_or_path(
    client: GitHubClient,
    cache: Optional[DiskCache],
    identifier: str,
    *,
    owner: str = OWNER,
    repo: str,
    ref: str = DEFAULT_BRANCH,
    category: Optional[str] = None,
    parent_contains: Optional[str] = None,
    parent0: Optional[str] = None,
    parent1: Optional[str] = None,
) -> Tuple[str, bytes]:
    """Fetch a document by repository path or exact document name."""
    if "/" in identifier and identifier.endswith(".md"):
        body = get_file_raw(client, owner, repo, identifier, ref=ref)
        return identifier, body

    entries = enumerate_documents(client, cache, owner=owner, repo=repo, ref=ref)
    hits = [
        entry
        for entry in _filter_documents(
            entries,
            category=category,
            parent_contains=parent_contains,
            parent0=parent0,
            parent1=parent1,
        )
        if entry.name == identifier
    ]

    if len(hits) == 1:
        path = hits[0].path
        return path, get_file_raw(client, owner, repo, path, ref=ref)
    if not hits:
        raise NotFoundError(f"no document matches {identifier!r} in {repo}")

    candidates = ", ".join(entry.path for entry in hits[:10])
    suffix = "" if len(hits) <= 10 else f", ... +{len(hits) - 10} more"
    raise AmbiguousMatchError(
        f"ambiguous document name {identifier!r} in {repo}; "
        f"pass the full path instead: {candidates}{suffix}",
        [entry.path for entry in hits],
    )


def _filter_documents(
    items: List[TreeDocumentEntry],
    *,
    category: Optional[str],
    parent_contains: Optional[str],
    parent0: Optional[str],
    parent1: Optional[str],
) -> List[TreeDocumentEntry]:
    filtered = list(items)
    if category:
        filtered = [entry for entry in filtered if entry.category == category]
    if parent_contains:
        filtered = [entry for entry in filtered if parent_contains in entry.parents]
    if parent0:
        filtered = [
            entry for entry in filtered
            if len(entry.parents) >= 1 and entry.parents[0] == parent0
        ]
    if parent1:
        filtered = [
            entry for entry in filtered
            if len(entry.parents) >= 2 and entry.parents[1] == parent1
        ]
    return filtered


__all__ = [
    "TreeDocumentEntry",
    "enumerate_documents",
    "fetch_document_by_name_or_path",
    "filter_and_paginate_documents",
]
