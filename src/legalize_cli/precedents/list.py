"""Filter + paginate an in-memory precedent list (zero HTTP calls)."""

from __future__ import annotations

from typing import List, Optional, Tuple

from .model import PrecedentEntry


def list_precedents(
    items: List[PrecedentEntry],
    *,
    court: Optional[str] = None,
    type_: Optional[str] = None,
    page: int = 1,
    page_size: int = 100,
) -> Tuple[int, List[PrecedentEntry], Optional[int]]:
    """Return ``(total, slice, next_page)`` given in-memory filters."""
    if court:
        items = [e for e in items if e.법원명 == court]
    if type_:
        items = [e for e in items if e.사건종류 == type_]

    total = len(items)
    if page_size <= 0:
        raise ValueError("page_size must be positive")
    if page <= 0:
        raise ValueError("page must be 1-indexed")

    start = (page - 1) * page_size
    end = start + page_size
    window = items[start:end]
    next_page = page + 1 if end < total else None
    return total, window, next_page


__all__ = ["list_precedents"]
