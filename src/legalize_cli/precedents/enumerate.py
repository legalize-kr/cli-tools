"""Enumerate precedents from ``legalize-kr/precedent-kr`` via the trees endpoint.

Path structure: ``{사건종류}/{법원명}/{사건번호}.md``

This mirrors how ``laws/list.py`` enumerates laws — no ``metadata.json`` needed.
"""

from __future__ import annotations

import regex as re
from typing import List, Optional

from ..cache import DiskCache
from ..config import DEFAULT_BRANCH, OWNER, PRECEDENTS_REPO
from ..github.trees import get_tree
from ..http import GitHubClient
from .model import PrecedentEntry

_PRECEDENT_PATH_RE = re.compile(
    r"^(?P<type>[^/]+)/(?P<court>[^/]+)/(?P<case>.+)\.md$"
)


def enumerate_precedents(
    client: GitHubClient,
    cache: Optional[DiskCache] = None,
    *,
    owner: str = OWNER,
    repo: str = PRECEDENTS_REPO,
    ref: str = DEFAULT_BRANCH,
) -> List[PrecedentEntry]:
    """Return every precedent in the repo, parsed from tree paths."""
    entries = get_tree(client, owner, repo, ref)

    result: List[PrecedentEntry] = []
    for entry in entries:
        if entry.type != "blob":
            continue
        m = _PRECEDENT_PATH_RE.match(entry.path)
        if not m:
            continue
        result.append(
            PrecedentEntry(
                path=entry.path,
                사건종류=m.group("type"),
                법원명=m.group("court"),
                사건번호=m.group("case"),
                판례일련번호=entry.path,
            )
        )

    result.sort(key=lambda e: (e.사건종류, e.법원명, e.사건번호))
    return result


__all__ = ["enumerate_precedents"]
