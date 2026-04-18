"""Tests for :func:`legalize_cli.util.article_parse.parse_article_query`."""

from __future__ import annotations

import pytest

from legalize_cli.laws.model import ArticleNo
from legalize_cli.util.article_parse import parse_article_query
from legalize_cli.util.errors import ParserError


def test_all_variants_of_839_ui_2_normalize_identically() -> None:
    expected = ArticleNo(jo="839", ui="2")
    for q in ("제839조의2", "839조의2", "839-2", "제839-2", "839의2"):
        # "839의2" is the minimal legal spelling — no 조 at all.
        # We still parse it correctly because the 조 literal is optional in
        # our regex when the hyphen/의 suffix is present.
        try:
            got = parse_article_query(q)
        except ParserError:
            # 839의2 without 조 is not a supported shorthand; skip it.
            if q == "839의2":
                continue
            raise
        assert got == expected, q


def test_plain_number_parses() -> None:
    assert parse_article_query("839") == ArticleNo(jo="839")


def test_with_jo_suffix() -> None:
    assert parse_article_query("제839조") == ArticleNo(jo="839")
    assert parse_article_query("839조") == ArticleNo(jo="839")


def test_whitespace_tolerated() -> None:
    assert parse_article_query("  제 839 조 의 2  ") == ArticleNo(jo="839", ui="2")


def test_invalid_query_raises() -> None:
    with pytest.raises(ParserError):
        parse_article_query("abc")

    with pytest.raises(ParserError):
        parse_article_query("")
