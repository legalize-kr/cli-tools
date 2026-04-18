"""Wrapper for ``GET /repos/{owner}/{repo}/contents/{path}``.

This endpoint is **hard-capped at 1 MiB** regardless of ``Accept`` header. For
larger files — notably ``precedent-kr/metadata.json`` (~34MB) — callers must
go through :mod:`legalize_cli.github.blobs` (raw blob endpoint, 100MB cap) or
``raw.githubusercontent.com``. We surface a clear exception here to avoid
silent truncation.
"""

from __future__ import annotations

from typing import Optional

from ..http import GitHubClient
from ..util.errors import LegalizeError

#: GitHub's documented size ceiling for the contents endpoint.
CONTENTS_SIZE_LIMIT_BYTES = 1024 * 1024


class FileTooLargeError(LegalizeError):
    """Raised when the contents endpoint refuses a >1MB file.

    Callers should retry via :func:`legalize_cli.github.blobs.get_blob_raw`
    or the raw CDN host.
    """

    exit_code = 10


def get_file_raw(
    client: GitHubClient,
    owner: str,
    repo: str,
    path: str,
    ref: Optional[str] = None,
) -> bytes:
    """Fetch the raw bytes of a file at ``path``.

    :param ref: Commit SHA / branch / tag. Passed as ``?ref=``. When ``None``
        GitHub serves the default branch HEAD.
    :raises FileTooLargeError: The contents endpoint refused the file because
        it exceeds the 1MB cap. Retry via :mod:`legalize_cli.github.blobs`.
    """
    params: dict[str, str] = {}
    if ref:
        params["ref"] = ref

    # GitHub returns 403 with body ``{"errors": [{"code": "too_large"}]}`` for
    # >1MB files when Accept is ``vnd.github.raw``. We translate that to a
    # typed error; other 403s are already mapped to RateLimitError by the
    # HTTP layer.
    try:
        return client.get_raw(
            f"/repos/{owner}/{repo}/contents/{path}",
            params=params or None,
        )
    except Exception as exc:  # pragma: no cover - defensive path
        message = str(exc)
        if "too_large" in message.lower() or "larger than" in message.lower():
            raise FileTooLargeError(
                f"{path} exceeds the 1MB contents endpoint cap; "
                "use github.blobs.get_blob_raw or raw.githubusercontent.com",
            ) from exc
        raise


__all__ = ["get_file_raw", "FileTooLargeError", "CONTENTS_SIZE_LIMIT_BYTES"]
