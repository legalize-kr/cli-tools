"""Wrapper for ``GET /repos/{owner}/{repo}/commits``.

The commits endpoint is the backbone of Feature 3 (``as-of`` resolution): we
filter by ``path=`` and ``until=`` to find the commit at or before a target
date. We **preserve the original timezone offset** on ``author.date`` /
``committer.date`` because the pipeline commits share a synthetic
``+09:00`` author date — normalizing to UTC would destroy the only signal we
use for KST-same-date tiebreaking.
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from dateutil import parser as dateparser
from pydantic import BaseModel, Field

from ..http import GitHubClient


class CommitInfo(BaseModel):
    """A single commit from the list-commits endpoint."""

    sha: str
    author_date: datetime
    committer_date: datetime
    message: str

    model_config = {"arbitrary_types_allowed": True}


def list_commits(
    client: GitHubClient,
    owner: str,
    repo: str,
    path: str,
    *,
    until: Optional[str] = None,
    per_page: int = 100,
    page: int = 1,
) -> List[CommitInfo]:
    """Return commits touching ``path``, newest first.

    :param until: ISO-8601 upper bound (typically ``YYYY-MM-DDT23:59:59+09:00``).
        Passed verbatim as ``?until=`` — the GitHub API accepts it.
    :param per_page: GitHub's max is 100. We keep it at 100 by default to
        widen the same-date tiebreak window (§5 of the plan).
    :param page: 1-indexed page. Pagination via Link header is a future
        step; most paths in these repos have ≤100 revisions.
    """
    params: dict[str, str | int] = {
        "path": path,
        "per_page": per_page,
        "page": page,
    }
    if until:
        params["until"] = until

    payload = client.get_json(
        f"/repos/{owner}/{repo}/commits",
        params=params,
    )

    return [_parse_commit(item) for item in payload]


def _parse_commit(item: dict) -> CommitInfo:
    commit = item.get("commit", {})
    author = commit.get("author", {}) or {}
    committer = commit.get("committer", {}) or {}

    return CommitInfo(
        sha=item["sha"],
        author_date=dateparser.isoparse(author["date"]),
        committer_date=dateparser.isoparse(committer.get("date") or author["date"]),
        message=commit.get("message", ""),
    )


__all__ = ["CommitInfo", "list_commits"]
