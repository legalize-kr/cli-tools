"""Wrapper for ``GET /repos/{owner}/{repo}/git/trees/{ref}``.

A single recursive tree call enumerates every path in the repo at ``ref`` —
this is how Feature 1 (``legalize laws list``) avoids the lack of a laws-level
``metadata.json`` in ``legalize-kr/legalize-kr``.
"""

from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, Field

from ..http import GitHubClient

TreeEntryType = Literal["blob", "tree", "commit"]


class TreeEntry(BaseModel):
    """A single entry in a Git tree response."""

    path: str
    type: TreeEntryType
    sha: str
    size: int | None = Field(default=None)


def get_tree(
    client: GitHubClient,
    owner: str,
    repo: str,
    ref: str = "HEAD",
    *,
    recursive: bool = True,
) -> List[TreeEntry]:
    """Return all entries in the tree rooted at ``ref``.

    ``recursive`` uses GitHub's ``?recursive=1`` flag, which returns a flat
    list of every blob + tree below the root. The response includes a
    ``truncated: true`` flag on very large repos; we surface whatever GitHub
    returns and leave truncation handling to callers (laws + precedents repos
    are both well under the 100k-entry limit as of 2026).
    """
    params: dict[str, str] = {}
    if recursive:
        params["recursive"] = "1"

    payload = client.get_json(
        f"/repos/{owner}/{repo}/git/trees/{ref}",
        params=params,
    )

    tree = payload.get("tree", [])
    return [TreeEntry.model_validate(entry) for entry in tree]


__all__ = ["TreeEntry", "TreeEntryType", "get_tree"]
