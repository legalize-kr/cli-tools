"""Tests for :mod:`legalize_cli.laws.articles`."""

from __future__ import annotations

from pathlib import Path

import pytest

from legalize_cli.laws.articles import parse_articles
from legalize_cli.laws.frontmatter import parse as parse_frontmatter
from legalize_cli.laws.model import ArticleNo
from legalize_cli.util.errors import AmbiguousHeadingLevelError

FIXTURES = Path(__file__).parent.parent / "fixtures" / "laws"


def _body(name: str) -> str:
    _fm, body = parse_frontmatter((FIXTURES / name).read_text())
    return body


def test_two_hash_articles_parsed() -> None:
    articles = parse_articles(_body("small_simple.md"))

    assert len(articles) == 3
    assert [a.article_no.jo for a in articles] == ["1", "2", "3"]
    assert all(a.heading_level == 2 for a in articles)
    assert articles[0].heading_text.startswith("## 제1조")


def test_three_hash_articles_parsed_and_chapter_ignored() -> None:
    articles = parse_articles(_body("small_three_hashes.md"))

    # ``## 제1장 총칙`` is NOT an article (no 조 suffix) → only 3 articles.
    assert len(articles) == 3
    assert all(a.heading_level == 3 for a in articles)
    assert all(a.article_no.ui is None for a in articles)
    # parent_structure captures the chapter.
    assert articles[0].parent_structure == ["제1장 총칙"]


def test_five_hash_articles_with_parent_chain() -> None:
    articles = parse_articles(_body("mingbeop_like.md"))

    # 5 articles: 838, 839, 839의2, 840, 841.
    assert len(articles) == 5
    assert [a.article_no.jo for a in articles] == ["838", "839", "839", "840", "841"]
    article_839_ui_2 = articles[2]
    assert article_839_ui_2.article_no == ArticleNo(jo="839", ui="2")
    assert article_839_ui_2.parent_structure == [
        "제4편 친족",
        "제3장 혼인",
        "제2절 혼인의 해소",
    ]


def test_article_sub_number_parsed() -> None:
    articles = parse_articles(_body("article_no_sub.md"))

    assert len(articles) == 2
    assert articles[1].article_no.jo == "839"
    assert articles[1].article_no.ui == "2"


def test_ambiguous_heading_levels_raises() -> None:
    body = _body("ambiguous_levels.md")

    with pytest.raises(AmbiguousHeadingLevelError):
        parse_articles(body)


def test_deleted_article_detected() -> None:
    articles = parse_articles(_body("deleted_article.md"))
    statuses = {a.article_no.jo: a.status for a in articles}

    assert statuses["7"] == "deleted"
    # Other articles remain active.
    assert statuses["1"] == "active"
    assert statuses["8"] == "active"
    # 삭제 marker preserved in content.
    deleted = next(a for a in articles if a.article_no.jo == "7")
    assert "삭제" in deleted.content


def test_jeonmun_annotation_captured() -> None:
    articles = parse_articles(_body("amended.md"))
    first = articles[0]

    assert any("전문개정" in tag for tag in first.annotations)


def test_jeonmun_annotation_in_mingbeop_fixture() -> None:
    """민법-like fixture has [전문개정 2013.4.5] on article 839의2."""
    articles = parse_articles(_body("mingbeop_like.md"))
    article_839_ui_2 = next(a for a in articles if a.article_no.ui == "2")

    assert any("전문개정 2013.4.5" in tag for tag in article_839_ui_2.annotations)


def test_article_no_is_structured_not_string() -> None:
    articles = parse_articles(_body("mingbeop_like.md"))
    dumped = articles[0].article_no.model_dump(by_alias=True)

    assert dumped == {"조": "838", "의": None, "항": None, "호": None}


def test_empty_body_returns_empty_list() -> None:
    assert parse_articles("") == []
