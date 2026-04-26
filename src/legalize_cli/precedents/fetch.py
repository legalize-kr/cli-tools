"""Fetch a single precedent markdown by path or 사건번호."""

from __future__ import annotations

import json
from pathlib import Path
from typing import List, Optional, Tuple, Union

from ..SEP import SEP
from ..config import DEFAULT_BRANCH, OWNER, PRECEDENTS_REPO
from ..github.contents import get_file_raw
from ..github.trees import get_tree
from ..http import GitHubClient
from ..util.errors import NotFoundError


def _load_legacy_map(source: Union[str, Path, List[dict]]) -> List[dict]:
    """Normalise a legacy-paths.json source to a list of dicts."""
    if isinstance(source, list):
        return source
    return json.loads(Path(source).read_text(encoding="utf-8"))


def _lookup_in_legacy_map(entries: List[dict], caseno: str) -> Optional[str]:
    """Return ``new_path`` for the first entry whose ``old_path`` stem equals *caseno*."""
    for entry in entries:
        old_path = entry.get("old_path")
        new_path = entry.get("new_path")
        if old_path and new_path and Path(old_path).stem == caseno:
            return new_path
    return None


def fetch_by_id_or_path(
    client: GitHubClient,
    cache,  # noqa: ANN001 — passed through for API symmetry
    arg: str,
    *,
    owner: str = OWNER,
    repo: str = PRECEDENTS_REPO,
    ref: str = DEFAULT_BRANCH,
    legacy_map: Optional[Union[str, Path, List[dict]]] = None,
) -> Tuple[str, bytes]:
    """Return ``(path, markdown_bytes)`` for a precedent given by path or 사건번호.

    Resolution order:

    1. Path-looking input (contains ``/`` and ends with ``.md``) → direct fetch.
    2. New composite grammar: tree scan for ``*__{caseno}.md``.
    3. Legacy fallback: tree scan for ``{caseno}.md`` (old single-key filename).
    4. ``legacy_map`` fallback: JSON mapping old caseno → new composite path.

    :raises NotFoundError: no matching entry was found, or >1 matches (disambiguation).
    """
    if "/" in arg and arg.endswith(".md"):
        body = get_file_raw(client, owner, repo, arg)
        return arg, body

    entries = get_tree(client, owner, repo, ref)

    # (a) New composite grammar: filename ends with {SEP}{caseno}.md
    new_hits = [
        e for e in entries
        if e.type == "blob" and e.path.endswith(f"{SEP}{arg}.md")
    ]
    if len(new_hits) == 1:
        path = new_hits[0].path
        body = get_file_raw(client, owner, repo, path)
        return path, body
    if len(new_hits) > 1:
        candidates = ", ".join(e.path for e in new_hits)
        raise NotFoundError(
            f"ambiguous 사건번호 {arg!r} ({len(new_hits)} matches); "
            f"pass the full path instead: {candidates}"
        )

    # (b) Legacy: exact filename /{caseno}.md
    legacy_hits = [
        e for e in entries
        if e.type == "blob" and e.path.endswith(f"/{arg}.md")
    ]
    if len(legacy_hits) == 1:
        path = legacy_hits[0].path
        body = get_file_raw(client, owner, repo, path)
        return path, body
    if len(legacy_hits) > 1:
        candidates = ", ".join(e.path for e in legacy_hits)
        raise NotFoundError(
            f"ambiguous 사건번호 {arg!r} ({len(legacy_hits)} matches); "
            f"pass the full path instead: {candidates}"
        )

    # (c) Legacy-map fallback
    if legacy_map is not None:
        mapping = _load_legacy_map(legacy_map)
        new_path = _lookup_in_legacy_map(mapping, arg)
        if new_path:
            body = get_file_raw(client, owner, repo, new_path)
            return new_path, body

    raise NotFoundError(f"no precedent matches {arg!r}")


__all__ = ["fetch_by_id_or_path"]
