"""Unit tests for :mod:`legalize_cli.laws.diff`."""

from __future__ import annotations

from legalize_cli.laws.diff import (
    RENAME_SIMILARITY_THRESHOLD,
    diff_laws,
)
from legalize_cli.laws.model import Article, ArticleNo


def _a(jo: str, ui: str | None, content: str) -> Article:
    return Article(
        article_no=ArticleNo(jo=jo, ui=ui),
        heading_level=5,
        heading_text=f"##### 제{jo}조" + (f"의{ui}" if ui else ""),
        content=content,
        annotations=[],
        status="active",
        parent_structure=[],
    )


def test_added_and_removed() -> None:
    a = [_a("1", None, "AAA")]
    b = [_a("2", None, "BBB")]
    result = diff_laws(a, b, mode="article")
    statuses = sorted((c.status, c.article_no.jo) for c in result.changes)
    # 1 removed + 2 added (no rename since similarity between AAA/BBB is low).
    assert ("removed", "1") in statuses
    assert ("added", "2") in statuses


def test_modified_unchanged_omitted() -> None:
    a = [_a("1", None, "old")]
    b = [_a("1", None, "new")]
    result = diff_laws(a, b, mode="article")
    assert len(result.changes) == 1
    assert result.changes[0].status == "modified"
    assert result.changes[0].hunk  # unified diff present


def test_unchanged_hidden_by_default() -> None:
    a = [_a("1", None, "same")]
    b = [_a("1", None, "same")]
    result = diff_laws(a, b, mode="article")
    assert result.changes == []


def test_unchanged_shown_with_flag() -> None:
    a = [_a("1", None, "same")]
    b = [_a("1", None, "same")]
    result = diff_laws(a, b, mode="article", show_unchanged=True)
    assert len(result.changes) == 1
    assert result.changes[0].status == "unchanged"


def test_whitespace_only_change() -> None:
    a = [_a("1", None, "hello world")]
    b = [_a("1", None, "hello   world\n")]
    result = diff_laws(a, b, mode="article")
    assert len(result.changes) == 1
    assert result.changes[0].status == "whitespace-only"


def test_rename_above_threshold() -> None:
    common = "X" * 100 + "한국어 텍스트 예시"  # long matching payload
    a = [_a("1", None, common)]
    b = [_a("2", None, common + "Y")]  # >0.8 ratio
    result = diff_laws(a, b, mode="article")
    statuses = [(c.status, c.similarity) for c in result.changes]
    assert any(s[0] == "renamed" for s in statuses)
    ratio = next(s[1] for s in statuses if s[0] == "renamed")
    assert ratio >= RENAME_SIMILARITY_THRESHOLD


def test_rename_below_threshold_splits() -> None:
    a = [_a("1", None, "totally different content A")]
    b = [_a("2", None, "entirely unrelated body XYZ")]
    result = diff_laws(a, b, mode="article")
    statuses = {c.status for c in result.changes}
    assert statuses == {"added", "removed"}


def test_unified_mode_returns_text() -> None:
    result = diff_laws([], [], a_body="foo\n", b_body="bar\n", mode="unified")
    assert result.mode == "unified"
    assert result.text is not None
    assert "+bar" in result.text
