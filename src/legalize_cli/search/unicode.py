"""Query normalization for Korean-aware text search.

The canonical form:
- NFC.
- ``·`` (U+00B7) folded to ``ㆍ`` (U+318D).

We emit both canonical and alt spellings so callers can try each against a
target set.
"""

from __future__ import annotations

import unicodedata
from typing import Tuple

from ..util.normalize import HANGUL_ARAEA, MIDDLE_DOT


def normalize_query(q: str) -> str:
    """Return the canonical form of ``q`` (NFC + middle-dot fold)."""
    if not q:
        return q
    return unicodedata.normalize("NFC", q).replace(MIDDLE_DOT, HANGUL_ARAEA)


def query_variants(q: str) -> Tuple[str, str]:
    """Return ``(canonical, alt_with_middle_dot)`` so matcher can try both."""
    canonical = normalize_query(q)
    alt = canonical.replace(HANGUL_ARAEA, MIDDLE_DOT)
    return canonical, alt


__all__ = ["normalize_query", "query_variants"]
