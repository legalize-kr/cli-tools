"""Unit tests for :mod:`legalize_cli.laws.asof`.

Pins the same-date tiebreaker contract:
1. Newest ``author_date``.
2. Newest ``committer_date``.
3. Lexicographically smallest SHA.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import List

from legalize_cli.github.commits import CommitInfo
from legalize_cli.laws.asof import candidates_for_semantic, resolve_as_of

_KST = timezone(timedelta(hours=9))


def _c(sha: str, author_iso: str, committer_iso: str | None = None) -> CommitInfo:
    from dateutil import parser as dateparser

    author_dt = dateparser.isoparse(author_iso)
    committer_dt = dateparser.isoparse(committer_iso or author_iso)
    return CommitInfo(
        sha=sha, author_date=author_dt, committer_date=committer_dt, message=""
    )


def test_empty_returns_none() -> None:
    assert resolve_as_of([], date(2020, 1, 1)) is None


def test_before_all_returns_none() -> None:
    commits: List[CommitInfo] = [_c("aa", "2020-01-01T12:00:00+09:00")]
    assert resolve_as_of(commits, date(2019, 12, 31)) is None


def test_basic_newest_author_date_wins() -> None:
    commits = [
        _c("aa", "2017-01-01T12:00:00+09:00"),
        _c("bb", "2020-01-01T12:00:00+09:00"),
        _c("cc", "2022-01-01T12:00:00+09:00"),
    ]
    chosen = resolve_as_of(commits, date(2021, 1, 1))
    assert chosen is not None
    assert chosen.sha == "bb"


def test_tiebreak_step2_committer_date() -> None:
    """Same author_date → newest committer_date wins."""
    commits = [
        _c("aa", "2020-01-01T12:00:00+09:00", "2020-01-02T00:00:00+00:00"),
        _c("bb", "2020-01-01T12:00:00+09:00", "2020-01-03T00:00:00+00:00"),
        _c("cc", "2020-01-01T12:00:00+09:00", "2020-01-01T23:00:00+00:00"),
    ]
    chosen = resolve_as_of(commits, date(2020, 6, 1))
    assert chosen is not None
    assert chosen.sha == "bb"  # newest committer date


def test_tiebreak_step3_lex_smallest_sha() -> None:
    """Identical author AND committer dates → lex-smallest SHA wins."""
    same_author = "2020-01-01T12:00:00+09:00"
    same_committer = "2020-01-02T00:00:00+00:00"
    commits = [
        _c("zz99", same_author, same_committer),
        _c("aa00", same_author, same_committer),
        _c("mm50", same_author, same_committer),
    ]
    chosen = resolve_as_of(commits, date(2020, 6, 1))
    assert chosen is not None
    assert chosen.sha == "aa00"


def test_pre_1970_date() -> None:
    """Dates before epoch must still resolve."""
    commits = [
        _c("aa", "1968-06-01T12:00:00+09:00"),
        _c("bb", "1972-01-01T12:00:00+09:00"),
    ]
    chosen = resolve_as_of(commits, date(1970, 1, 1))
    assert chosen is not None
    assert chosen.sha == "aa"


def test_end_of_day_kst_inclusive() -> None:
    """A commit at 23:59 KST on the target date must be included."""
    commits = [_c("aa", "2020-06-15T23:59:00+09:00")]
    chosen = resolve_as_of(commits, date(2020, 6, 15))
    assert chosen is not None and chosen.sha == "aa"


def test_candidates_for_semantic_returns_list() -> None:
    commits = [
        _c("aa", "2017-01-01T12:00:00+09:00"),
        _c("bb", "2020-01-01T12:00:00+09:00"),
        _c("cc", "2022-01-01T12:00:00+09:00"),
    ]
    result = candidates_for_semantic(commits, date(2020, 12, 31))
    shas = {c.sha for c in result}
    assert shas == {"aa", "bb"}


def test_시행일자_falls_back_to_공포일자_stub() -> None:
    """Without per-candidate frontmatter, 시행일자 mode reuses 공포일자 logic."""
    commits = [
        _c("aa", "2017-01-01T12:00:00+09:00"),
        _c("bb", "2020-01-01T12:00:00+09:00"),
    ]
    chosen = resolve_as_of(commits, date(2021, 1, 1), semantic="시행일자")
    assert chosen is not None and chosen.sha == "bb"
