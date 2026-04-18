"""Frontmatter-based ``상태`` filtering.

Excluding ``상태: 폐지`` is the default for ``laws as-of`` per plan §6. This
module concentrates the single-file fetch + parse so the command layer stays
slim.
"""

from __future__ import annotations

from typing import Iterable, List, Optional

from ..config import LAWS_REPO, OWNER
from ..github.contents import get_file_raw
from ..http import GitHubClient
from .frontmatter import parse as parse_frontmatter
from .list import LawEntry


def filter_by_status(
    client: GitHubClient,
    entries: Iterable[LawEntry],
    *,
    include_repealed: bool = False,
    owner: str = OWNER,
    repo: str = LAWS_REPO,
    ref: Optional[str] = None,
) -> List[LawEntry]:
    """Drop ``상태: 폐지`` entries unless ``include_repealed`` is True.

    Costs one GET per entry — the caller is responsible for rate-limit gating.
    """
    if include_repealed:
        return list(entries)

    kept: List[LawEntry] = []
    for entry in entries:
        body = get_file_raw(client, owner, repo, entry.path, ref=ref)
        fm, _ = parse_frontmatter(body.decode("utf-8", errors="replace"))
        if (fm.status or "") == "폐지":
            continue
        kept.append(entry)
    return kept


__all__ = ["filter_by_status"]
