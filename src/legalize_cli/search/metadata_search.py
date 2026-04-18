"""Search ``precedent-kr/metadata.json`` entries in-memory — zero HTTP calls."""

from __future__ import annotations

from typing import Dict, List

from ..precedents.model import PrecedentEntry
from .unicode import query_variants


def metadata_search_items(
    index: Dict[str, PrecedentEntry],
    query: str,
    *,
    source: str = "precedents",
) -> List[Dict[str, str]]:
    """Match ``query`` against 사건명 / 사건번호 / 법원명 / 사건종류."""
    canonical, alt = query_variants(query)

    out: List[Dict[str, str]] = []
    for entry in index.values():
        haystack = " ".join(
            (entry.사건명, entry.사건번호, entry.법원명, entry.사건종류)
        )
        if canonical in haystack or alt in haystack:
            out.append(
                {
                    "source": source,
                    "path": entry.path,
                    "match_type": "title",
                    "사건명": entry.사건명,
                }
            )
    return out


__all__ = ["metadata_search_items"]
