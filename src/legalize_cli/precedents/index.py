"""Fetch and parse ``precedent-kr/metadata.json`` (~34MB).

Primary path: ``raw.githubusercontent.com`` (anonymous CDN; no API-rate-limit
charge, no 1MB cap). Fallback: ``/git/blobs/{sha}`` with raw media type. We
never hit ``/repos/.../contents/`` — that endpoint hard-caps at 1MB and would
silently fail on this payload (see plan §5).
"""

from __future__ import annotations

import json
import time
from datetime import date
from typing import Dict, Optional

from ..cache import DiskCache
from ..config import DEFAULT_BRANCH, GITHUB_RAW_HOST, OWNER, PRECEDENTS_REPO
from ..github.blobs import get_blob_raw
from ..github.trees import get_tree
from ..http import GitHubClient
from ..util.errors import LegalizeError
from .model import PrecedentEntry


def fetch_precedent_index(
    client: GitHubClient,
    cache: Optional[DiskCache] = None,
    *,
    owner: str = OWNER,
    repo: str = PRECEDENTS_REPO,
    ref: str = DEFAULT_BRANCH,
) -> Dict[str, PrecedentEntry]:
    """Return a dict keyed by 판례일련번호 → :class:`PrecedentEntry`.

    Cached on disk for 24h at ``precedent-index/metadata.json.bin``.
    """
    raw_bytes = _load_cached(cache)
    if raw_bytes is None:
        raw_bytes = _fetch_fresh(client, owner, repo, ref)
        _store_cached(cache, raw_bytes)

    try:
        parsed = json.loads(raw_bytes.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise LegalizeError(f"precedent index: invalid JSON ({exc})") from exc

    if not isinstance(parsed, dict):
        raise LegalizeError("precedent index: expected top-level object")

    result: Dict[str, PrecedentEntry] = {}
    for key, value in parsed.items():
        if not isinstance(value, dict):
            continue
        entry_data = {"판례일련번호": str(key), **value}
        try:
            result[str(key)] = PrecedentEntry.model_validate(entry_data)
        except Exception:
            # Skip malformed entries rather than kill the index.
            continue
    return result


# ---- internals ---------------------------------------------------------


def _fetch_fresh(client: GitHubClient, owner: str, repo: str, ref: str) -> bytes:
    primary_url = f"{GITHUB_RAW_HOST}/{owner}/{repo}/{ref}/metadata.json"
    try:
        return client.get_url(primary_url)
    except Exception:
        # Fallback: look up the blob sha via the tree, then /git/blobs/{sha}
        # with raw media type.
        entries = get_tree(client, owner, repo, ref, recursive=False)
        blob_sha: Optional[str] = None
        for entry in entries:
            if entry.path == "metadata.json" and entry.type == "blob":
                blob_sha = entry.sha
                break
        if not blob_sha:
            raise LegalizeError(
                "precedent index: metadata.json not present at ref "
                f"{owner}/{repo}@{ref}"
            )
        return get_blob_raw(client, owner, repo, blob_sha)


def _cache_path_date() -> date:
    """Sentinel 'date' used by DiskCache addressing for the index blob."""
    return date(1970, 1, 1)


def _load_cached(cache: Optional[DiskCache]) -> Optional[bytes]:
    if cache is None:
        return None
    path = cache.root / "precedent-index" / "metadata.json.bin"
    if not path.exists():
        return None
    # 24h TTL.
    if time.time() - path.stat().st_mtime >= 24 * 60 * 60:
        return None
    return path.read_bytes()


def _store_cached(cache: Optional[DiskCache], payload: bytes) -> None:
    if cache is None:
        return
    target = cache.root / "precedent-index" / "metadata.json.bin"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)


__all__ = ["fetch_precedent_index"]
