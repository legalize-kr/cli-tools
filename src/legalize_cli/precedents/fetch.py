"""Fetch a single precedent markdown by path or 사건번호."""

from __future__ import annotations

from typing import Optional, Tuple

from ..config import DEFAULT_BRANCH, OWNER, PRECEDENTS_REPO
from ..github.contents import get_file_raw
from ..github.trees import get_tree
from ..http import GitHubClient
from ..util.errors import NotFoundError


def fetch_by_id_or_path(
    client: GitHubClient,
    cache,  # noqa: ANN001 - passed through for API symmetry
    arg: str,
    *,
    owner: str = OWNER,
    repo: str = PRECEDENTS_REPO,
    ref: str = DEFAULT_BRANCH,
) -> Tuple[str, bytes]:
    """Return ``(path, markdown_bytes)`` for a precedent given by path or 사건번호.

    Resolution order:

    1. Path-looking input (contains ``/`` and ends with ``.md``) → direct fetch.
    2. 사건번호 → scan tree for a blob whose filename stem matches.

    :raises NotFoundError: no matching entry was found.
    """
    if "/" in arg and arg.endswith(".md"):
        body = get_file_raw(client, owner, repo, arg)
        return arg, body

    # 사건번호: scan tree for a matching filename stem.
    entries = get_tree(client, owner, repo, ref)
    hits = [e for e in entries if e.type == "blob" and e.path.endswith(f"/{arg}.md")]
    if len(hits) == 1:
        path = hits[0].path
        body = get_file_raw(client, owner, repo, path)
        return path, body
    if len(hits) > 1:
        raise NotFoundError(
            f"ambiguous 사건번호 {arg!r} ({len(hits)} hits); pass the full path instead"
        )
    raise NotFoundError(f"no precedent matches {arg!r}")


__all__ = ["fetch_by_id_or_path"]
