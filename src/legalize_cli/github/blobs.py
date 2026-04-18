"""Wrapper for ``GET /repos/{owner}/{repo}/git/blobs/{sha}``.

Unlike ``/contents/``, the blob endpoint supports files up to 100MB when
``Accept: application/vnd.github.raw`` is sent. This is the REST fallback
for fetching ``precedent-kr/metadata.json`` (~34MB) when the preferred
``raw.githubusercontent.com`` CDN path fails.
"""

from __future__ import annotations

from ..http import GitHubClient


def get_blob_raw(
    client: GitHubClient,
    owner: str,
    repo: str,
    sha: str,
) -> bytes:
    """Return the raw bytes of the blob identified by ``sha``."""
    return client.get_raw(f"/repos/{owner}/{repo}/git/blobs/{sha}")


__all__ = ["get_blob_raw"]
