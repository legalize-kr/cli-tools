"""No-token-path search: match the query against paths from the tree API.

Optional ``--heavy-content-scan`` fetches each candidate file for a body
grep. We refuse that mode unless the rate-limit budget comfortably covers
``2 × candidate_count`` fetches or the user explicitly passes
``--yes-exhaust-quota``.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from ..cache import DiskCache
from ..config import LAWS_REPO, OWNER
from ..github.contents import get_file_raw
from ..github.trees import get_tree
from ..http import GitHubClient
from ..util.errors import LegalizeError
from .unicode import normalize_query, query_variants


def tree_filter_items(
    client: GitHubClient,
    cache: Optional[DiskCache],
    query: str,
    *,
    owner: str = OWNER,
    repo: str = LAWS_REPO,
    ref: str = "HEAD",
    heavy_content_scan: bool = False,
    yes_exhaust: bool = False,
    source: str = "laws",
) -> List[Dict[str, str]]:
    """Return ``items[]`` from the tree-filter strategy."""
    canonical, alt = query_variants(query)
    entries = get_tree(client, owner, repo, ref)

    candidates: List[str] = []
    for entry in entries:
        if entry.type != "blob":
            continue
        path = entry.path
        if canonical in path or alt in path:
            candidates.append(path)

    items: List[Dict[str, str]] = [
        {"source": source, "path": p, "match_type": "title"} for p in candidates
    ]

    if not heavy_content_scan:
        return items

    # Heavy scan: pre-flight the budget.
    rl = getattr(client, "last_rate_limit", None)
    if rl is not None:
        needed = 2 * len(entries)  # worst-case: fetch every blob
        if needed > rl.remaining and not yes_exhaust:
            raise LegalizeError(
                f"would exceed rate-limit budget (need {needed}, have {rl.remaining}); "
                "pass --yes-exhaust-quota to proceed or set GITHUB_TOKEN"
            )

    # Fetch every candidate body; add body matches on top of title matches.
    canonical_lower = canonical.lower()
    alt_lower = alt.lower()
    for entry in entries:
        if entry.type != "blob" or entry.path in candidates:
            continue
        body = get_file_raw(client, owner, repo, entry.path).decode(
            "utf-8", errors="replace"
        )
        normalized = normalize_query(body).lower()
        if canonical_lower in normalized or alt_lower in normalized:
            items.append({"source": source, "path": entry.path, "match_type": "body"})

    return items


__all__ = ["tree_filter_items"]
