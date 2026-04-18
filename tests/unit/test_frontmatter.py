"""Tests for :mod:`legalize_cli.laws.frontmatter`."""

from __future__ import annotations

import unicodedata
from datetime import date
from pathlib import Path

import pytest

from legalize_cli.laws.frontmatter import parse
from legalize_cli.util.errors import ParserError

FIXTURES = Path(__file__).parent.parent / "fixtures" / "laws"


def test_parses_simple_fixture() -> None:
    text = (FIXTURES / "small_simple.md").read_text()

    fm, body = parse(text)

    assert fm.title == "작은시행규칙"
    assert fm.category == "국토교통부령"
    assert fm.ministries == ["국토교통부"]
    assert fm.promulgation_date == date(2020, 5, 1)
    assert fm.enforcement_date == date(2020, 6, 1)
    assert fm.status == "시행"
    assert "제1조 (목적)" in body


def test_tolerates_bom() -> None:
    text = "\ufeff---\n제목: BOM테스트\n법령구분: 법률\n---\n\n본문"

    fm, body = parse(text)

    assert fm.title == "BOM테스트"
    assert body == "\n본문"


def test_tolerates_crlf() -> None:
    text = "---\r\n제목: CRLF테스트\r\n법령구분: 법률\r\n---\r\n\r\n본문"

    fm, body = parse(text)

    assert fm.title == "CRLF테스트"
    assert "본문" in body


def test_missing_frontmatter_returns_empty() -> None:
    text = "# 제목\n본문만 있음"

    fm, body = parse(text)

    assert fm.title is None
    assert body == text


def test_scalar_ministry_coerced_to_list() -> None:
    text = "---\n제목: 단독부처\n소관부처: 법무부\n법령구분: 법률\n---\n\n본문"

    fm, _ = parse(text)

    assert fm.ministries == ["법무부"]


def test_list_ministry_preserved() -> None:
    text = "---\n제목: 복수부처\n소관부처: [법무부, 기획재정부]\n법령구분: 법률\n---\n\n본문"

    fm, _ = parse(text)

    assert fm.ministries == ["법무부", "기획재정부"]


def test_unicode_nfd_input_is_normalized_to_nfc() -> None:
    """Pre-composed vs decomposed jamo must collapse."""
    nfd_title = unicodedata.normalize("NFD", "민법")
    text = f"---\n제목: {nfd_title}\n법령구분: 법률\n---\n\n본문"

    fm, _ = parse(text)

    assert fm.title == unicodedata.normalize("NFC", "민법")


def test_empty_string_value_is_preserved_as_empty_string() -> None:
    text = "---\n제목: ''\n법령구분: 법률\n---\n\n본문"

    fm, _ = parse(text)

    assert fm.title == ""


def test_invalid_yaml_raises_parser_error() -> None:
    text = "---\n제목: [unterminated\n---\n\n본문"

    with pytest.raises(ParserError):
        parse(text)


def test_none_input_raises() -> None:
    with pytest.raises(ParserError):
        parse(None)  # type: ignore[arg-type]
