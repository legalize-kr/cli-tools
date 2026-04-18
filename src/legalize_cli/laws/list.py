"""Enumerate laws from ``legalize-kr/legalize-kr`` via the trees endpoint.

There is no laws-level ``metadata.json`` in the committed repo (see plan §6
note) so the list is synthesized from ``GET /git/trees/{branch}?recursive=1``
and filtered to paths matching ``kr/{법령명}/{법률|시행령|시행규칙|대통령령}.md``.
"""

from __future__ import annotations

from typing import List, Optional

import regex as re
from pydantic import BaseModel, ConfigDict

from ..cache import DiskCache
from ..config import DEFAULT_BRANCH, LAWS_REPO, OWNER
from ..github.trees import get_tree
from ..http import GitHubClient

#: Canonical category set. Arbitrary ministry-specific 법령구분 values are
#: possible inside frontmatter, but the enumeration is path-driven and only
#: these four filenames exist in the repo.
LAW_CATEGORIES = ("법률", "시행령", "시행규칙", "대통령령")

_LAW_PATH_RE = re.compile(
    r"^kr/(?P<name>[^/]+)/(?P<category>법률|시행령|시행규칙|대통령령)\.md$"
)


class LawEntry(BaseModel):
    """A single law (path, name, category) tuple."""

    model_config = ConfigDict(extra="forbid")

    name: str
    path: str
    category: str


def enumerate_laws(
    client: GitHubClient,
    cache: Optional[DiskCache] = None,
    *,
    owner: str = OWNER,
    repo: str = LAWS_REPO,
    ref: str = DEFAULT_BRANCH,
) -> List[LawEntry]:
    """Return every law path in the repo, filtered by the canonical regex.

    ``cache`` is accepted for API symmetry; the underlying HTTP layer attaches
    ETag caching transparently when ``cache_ttl`` is passed.
    """
    # Use a 1-hour ETag window for trees. Signed into get_json via cache_ttl.
    entries = get_tree(client, owner, repo, ref)

    laws: List[LawEntry] = []
    for entry in entries:
        if entry.type != "blob":
            continue
        m = _LAW_PATH_RE.match(entry.path)
        if not m:
            continue
        laws.append(
            LawEntry(
                name=m.group("name"),
                path=entry.path,
                category=m.group("category"),
            )
        )

    # Deterministic order: by category then name.
    laws.sort(key=lambda e: (e.category, e.name))
    return laws


def filter_and_paginate(
    items: List[LawEntry],
    *,
    category: Optional[str] = None,
    page: int = 1,
    page_size: int = 100,
) -> tuple[int, List[LawEntry], Optional[int]]:
    """Apply category filter + pagination; return ``(total, slice, next_page)``."""
    if category and category != "all":
        filtered = [e for e in items if e.category == category]
    else:
        filtered = list(items)

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


__all__ = [
    "LAW_CATEGORIES",
    "LawEntry",
    "enumerate_laws",
    "filter_and_paginate",
]
