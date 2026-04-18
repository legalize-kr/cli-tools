"""Tests for :mod:`legalize_cli.util.normalize`."""

from __future__ import annotations

import unicodedata

from legalize_cli.util.normalize import (
    HANGUL_ARAEA,
    MIDDLE_DOT,
    normalize_lawname,
    normalize_text,
)


def test_middle_dot_canonicalized_to_araea() -> None:
    src = f"대{MIDDLE_DOT}중{MIDDLE_DOT}소기업 상생협력 촉진에 관한 법률"
    canonical = f"대{HANGUL_ARAEA}중{HANGUL_ARAEA}소기업 상생협력 촉진에 관한 법률"

    assert normalize_lawname(src) == canonical


def test_normalize_lawname_idempotent() -> None:
    canonical = f"가{HANGUL_ARAEA}나"
    assert normalize_lawname(canonical) == canonical


def test_nfc_equivalent_to_nfd_after_normalize() -> None:
    nfd = unicodedata.normalize("NFD", "민법")
    nfc = unicodedata.normalize("NFC", "민법")

    assert normalize_text(nfd) == nfc


def test_bom_stripped() -> None:
    assert normalize_text("\ufeff민법") == "민법"


def test_empty_and_none_safe() -> None:
    assert normalize_text("") == ""


def test_middle_dot_only_replaced_in_lawname_not_in_text() -> None:
    """``normalize_text`` must NOT fold ``·`` → ``ㆍ`` — that is lawname-only."""
    src = f"foo{MIDDLE_DOT}bar"
    assert normalize_text(src) == src
