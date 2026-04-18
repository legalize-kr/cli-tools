"""Fetch the revision history for a law path with fingerprint-based cache.

The pipeline uses a synthetic ``12:00:00 +09:00`` author date on every commit
(see plan §5 Step 2). This module is responsible for enforcing that
invariant at runtime — if the offset ever drifts from ``+09:00`` we halt
loudly via :class:`LegalizeError`. Silent tolerance of UTC would make
every ``--date`` filter off by up to 9 hours.
"""

from __future__ import annotations

from typing import List, Optional

from ..cache import DiskCache, compute_list_fingerprint
from ..config import DEFAULT_BRANCH, LAWS_REPO, OWNER
from ..github.commits import CommitInfo, list_commits
from ..http import GitHubClient
from ..util.errors import LegalizeError

#: Seconds offset for KST = +09:00.
KST_OFFSET_SECONDS = 9 * 3600


def get_revisions(
    client: GitHubClient,
    cache: Optional[DiskCache],
    path: str,
    *,
    owner: str = OWNER,
    repo: str = LAWS_REPO,
    until: Optional[str] = None,
) -> List[CommitInfo]:
    """Return commits for ``path``, newest first.

    Asserts the first commit's author-date offset is ``+09:00``; any other
    offset raises :class:`LegalizeError` per plan §9 Step 2.

    The ``list_fingerprint`` is computed and (when ``cache`` is supplied)
    compared against the previously-stored value; on mismatch, the cached
    ``contents/`` entries for the same ``(repo, path)`` pair are dropped so
    the next contents fetch re-reads from origin.
    """
    commits = list_commits(client, owner, repo, path, until=until)

    if commits:
        offset = commits[0].author_date.utcoffset()
        observed = offset.total_seconds() if offset is not None else None
        if observed != KST_OFFSET_SECONDS:
            raise LegalizeError(
                "author-date timezone invariant broken: expected +09:00, "
                f"observed offset={observed} for {path}@{commits[0].sha}; "
                "aborting to avoid computing wrong --date answers."
            )

    if cache is not None and commits:
        repo_slug = f"{owner}/{repo}"
        fingerprint = compute_list_fingerprint(commits)
        prior = cache.get_list_fingerprint(repo_slug, path)
        if prior is not None and prior != fingerprint:
            cache.invalidate_path_contents(repo_slug, path)
        cache.put_commits(
            repo_slug,
            path,
            [c.model_dump(mode="json") for c in commits],
            fingerprint,
        )

    return commits


__all__ = ["get_revisions", "KST_OFFSET_SECONDS"]


# ``DEFAULT_BRANCH`` is imported to keep symbol parity with downstream callers
# that may want a default ref; suppress pyflakes noise.
_ = DEFAULT_BRANCH
