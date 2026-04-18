"""Unit tests for query canonicalization (· ↔ ㆍ)."""

from __future__ import annotations

from legalize_cli.search.unicode import normalize_query, query_variants
from legalize_cli.util.normalize import HANGUL_ARAEA, MIDDLE_DOT


def test_normalize_folds_middle_dot() -> None:
    # Input contains U+00B7 (·); canonical form uses U+318D (ㆍ).
    raw = "10" + MIDDLE_DOT + "27"
    normalized = normalize_query(raw)
    assert MIDDLE_DOT not in normalized
    assert HANGUL_ARAEA in normalized


def test_variants_emit_both_spellings() -> None:
    raw = "10" + HANGUL_ARAEA + "27"
    canonical, alt = query_variants(raw)
    assert HANGUL_ARAEA in canonical
    assert MIDDLE_DOT in alt
    # Round-trip swap consistent.
    assert canonical.replace(HANGUL_ARAEA, MIDDLE_DOT) == alt
