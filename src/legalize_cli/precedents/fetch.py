"""Fetch a single precedent markdown by path or 사건번호/판례일련번호."""

from __future__ import annotations

from typing import Dict, Optional, Tuple

from ..config import OWNER, PRECEDENTS_REPO
from ..github.contents import get_file_raw
from ..http import GitHubClient
from ..util.errors import NotFoundError
from .model import PrecedentEntry


def fetch_by_id_or_path(
    client: GitHubClient,
    cache,  # noqa: ANN001 - passed through for API symmetry
    index: Dict[str, PrecedentEntry],
    arg: str,
    *,
    owner: str = OWNER,
    repo: str = PRECEDENTS_REPO,
) -> Tuple[str, bytes]:
    """Return ``(path, markdown_bytes)`` for a precedent given by path or id.

    :raises NotFoundError: no matching entry was found.
    """
    path = _resolve_path(index, arg)
    try:
        body = get_file_raw(client, owner, repo, path)
    except NotFoundError as exc:
        raise NotFoundError(f"precedent path not reachable: {path}") from exc
    return path, body


def _resolve_path(index: Dict[str, PrecedentEntry], arg: str) -> str:
    """Return a repo-relative path for ``arg``.

    Resolution order:

    1. Path-looking input (contains ``/`` and ends with ``.md``) is passed
       through verbatim.
    2. Exact ``판례일련번호`` key.
    3. Exact ``사건번호`` match in the index.
    """
    if "/" in arg and arg.endswith(".md"):
        return arg

    # ID lookup.
    if arg in index:
        return index[arg].path

    # 사건번호 scan.
    hits = [e for e in index.values() if e.사건번호 == arg]
    if len(hits) == 1:
        return hits[0].path
    if len(hits) > 1:
        raise NotFoundError(
            f"ambiguous 사건번호 {arg!r} ({len(hits)} hits); pass the full path instead"
        )
    raise NotFoundError(f"no precedent matches {arg!r}")


__all__ = ["fetch_by_id_or_path"]
