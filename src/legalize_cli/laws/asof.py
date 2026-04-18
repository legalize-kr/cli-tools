"""Resolve ``as-of date D`` to a specific commit.

Same-date tiebreaker (§5 of the plan):

1. Newest ``author.date`` at-or-before the target.
2. Among ties on ``author.date``, newest ``committer.date``.
3. Among ties on both, lexicographically smallest SHA.

The ``시행일자`` semantic requires reading each candidate's frontmatter (one
GET per candidate). This module returns the full candidate list for that
semantic; the caller decides how many to fetch.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import List, Literal, Optional

from ..github.commits import CommitInfo

#: +09:00 KST — used when building the end-of-day upper bound for as-of scans.
_KST = timezone(timedelta(hours=9))

Semantic = Literal["공포일자", "시행일자"]


def resolve_as_of(
    commits: List[CommitInfo],
    target_date: date,
    semantic: Semantic = "공포일자",
) -> Optional[CommitInfo]:
    """Return the single at-or-before commit for ``공포일자``, else ``None``.

    For ``시행일자`` the semantics require the frontmatter of each candidate;
    this function in that mode returns the **last-matching** commit only as a
    best-effort placeholder so callers that do not yet read frontmatter still
    get a reasonable answer. See :func:`candidates_for_semantic` for a
    frontmatter-aware replacement.
    """
    if not commits:
        return None

    if semantic == "공포일자":
        return _choose_by_author_date(commits, target_date)

    # 시행일자: fall back to 공포일자 until the caller runs the heavier
    # frontmatter-scanning path.
    return _choose_by_author_date(commits, target_date)


def candidates_for_semantic(
    commits: List[CommitInfo],
    target_date: date,
) -> List[CommitInfo]:
    """Return every commit at-or-before ``target_date`` (newest first).

    Callers wanting ``시행일자`` semantics iterate these candidates, fetch each
    one's frontmatter, and pick the newest whose ``시행일자 <= target_date``.
    """
    target_dt = _end_of_day_kst(target_date)
    return [c for c in commits if c.author_date <= target_dt]


# ---- internals --------------------------------------------------------


def _choose_by_author_date(commits: List[CommitInfo], target_date: date) -> Optional[CommitInfo]:
    target_dt = _end_of_day_kst(target_date)
    candidates = [c for c in commits if c.author_date <= target_dt]
    if not candidates:
        return None

    # Step 1: newest author_date.
    newest_author = max(c.author_date for c in candidates)
    first_pass = [c for c in candidates if c.author_date == newest_author]
    if len(first_pass) == 1:
        return first_pass[0]

    # Step 2: newest committer_date.
    newest_committer = max(c.committer_date for c in first_pass)
    second_pass = [c for c in first_pass if c.committer_date == newest_committer]
    if len(second_pass) == 1:
        return second_pass[0]

    # Step 3: lexicographically smallest SHA.
    return min(second_pass, key=lambda c: c.sha)


def _end_of_day_kst(d: date) -> datetime:
    """``YYYY-MM-DDT23:59:59+09:00`` — the inclusive upper bound per §5."""
    return datetime.combine(d, time(23, 59, 59), tzinfo=_KST)


__all__ = ["resolve_as_of", "candidates_for_semantic", "Semantic"]
