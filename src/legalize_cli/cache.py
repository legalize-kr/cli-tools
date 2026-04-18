"""On-disk cache with ETag support and force-push-safe addressing.

Design:

- Content entries are keyed by ``(repo, path, author_date)`` — never by raw
  SHA. A pipeline rebuild that rewrites commit history but preserves the
  ``(path, author_date)`` pair therefore cannot dirty the cache.
- A per-path **list fingerprint** (sha256 of sorted ``author_date | first-line
  message`` tuples) is stored alongside the commit list. On re-fetch, if the
  fingerprint differs, every cached ``contents/`` entry for that path is
  invalidated — this catches the one case (same path+date, different content)
  that could otherwise serve stale bytes.
- ETag entries live under ``etag/``; the key is the full request URL. The
  HTTP layer reads the previous ETag, sends ``If-None-Match``, and on 304
  reuses the stored body.
- TTLs are enforced by comparing file mtime against the subdir-specific TTL
  table; expired entries return ``None`` (cache miss) but remain on disk
  until explicit ``cache clear`` (cheap and audit-friendly).
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, List, Optional, Tuple

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .github.commits import CommitInfo

#: TTL (seconds) per cache subdirectory. Matches §7 of the plan.
TTLS: dict[str, int] = {
    "trees": 60 * 60,  # 1 hour
    "commits": 10 * 60,  # 10 minutes
    "contents": 7 * 24 * 60 * 60,  # 7 days
    "precedent-index": 24 * 60 * 60,  # 24 hours
    "search": 60 * 60,  # 1 hour
    "etag": 7 * 24 * 60 * 60,  # match contents; etag body is only used with its sibling
}

_SUBDIRS: Tuple[str, ...] = (
    "etag",
    "trees",
    "commits",
    "contents",
    "precedent-index",
    "search",
)


@dataclass(frozen=True)
class CachedEtag:
    """A body + etag pair, returned by :meth:`DiskCache.get_with_etag`."""

    body: bytes
    etag: str


class DiskCache:
    """Filesystem-backed cache rooted at ``cache_dir``."""

    def __init__(self, cache_dir: Path) -> None:
        self.root = Path(cache_dir).expanduser()
        for sub in _SUBDIRS:
            (self.root / sub).mkdir(parents=True, exist_ok=True)

    # ---- ETag (URL-addressed) ------------------------------------------

    def get_with_etag(self, url: str, *, now: Optional[float] = None) -> Optional[CachedEtag]:
        """Return ``(body, etag)`` if a fresh ETag entry exists for ``url``."""
        key = _hash_url(url)
        body_path = self.root / "etag" / f"{key}.body"
        etag_path = self.root / "etag" / f"{key}.etag"
        if not body_path.exists() or not etag_path.exists():
            return None
        if _is_expired(body_path, TTLS["etag"], now=now):
            return None
        return CachedEtag(body=body_path.read_bytes(), etag=etag_path.read_text().strip())

    def put_etag(self, url: str, body: bytes, etag: str) -> None:
        key = _hash_url(url)
        (self.root / "etag" / f"{key}.body").write_bytes(body)
        (self.root / "etag" / f"{key}.etag").write_text(etag)

    # ---- contents (force-push-safe key) --------------------------------

    def get_contents(
        self,
        repo: str,
        path: str,
        author_date: date,
        *,
        now: Optional[float] = None,
    ) -> Optional[bytes]:
        target = self._contents_path(repo, path, author_date)
        if not target.exists():
            return None
        if _is_expired(target, TTLS["contents"], now=now):
            return None
        return target.read_bytes()

    def put_contents(
        self,
        repo: str,
        path: str,
        author_date: date,
        body: bytes,
    ) -> None:
        target = self._contents_path(repo, path, author_date)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)

    def invalidate_path_contents(self, repo: str, path: str) -> int:
        """Delete every ``contents/`` entry for ``(repo, path)``; return count."""
        folder = self._contents_folder(repo, path)
        if not folder.exists():
            return 0
        removed = 0
        for entry in folder.iterdir():
            if entry.is_file():
                entry.unlink()
                removed += 1
        return removed

    # ---- commits + fingerprint -----------------------------------------

    def get_commits(
        self,
        repo: str,
        path: str,
        *,
        now: Optional[float] = None,
    ) -> Optional[list[dict]]:
        target = self._commits_payload(repo, path)
        if not target.exists():
            return None
        if _is_expired(target, TTLS["commits"], now=now):
            return None
        try:
            return json.loads(target.read_text())
        except json.JSONDecodeError:
            return None

    def put_commits(
        self,
        repo: str,
        path: str,
        items: Iterable[dict],
        list_fingerprint: str,
    ) -> None:
        target = self._commits_payload(repo, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(list(items), ensure_ascii=False, default=str))
        self._commits_fingerprint(repo, path).write_text(list_fingerprint)

    def get_list_fingerprint(self, repo: str, path: str) -> Optional[str]:
        target = self._commits_fingerprint(repo, path)
        if not target.exists():
            return None
        return target.read_text().strip()

    # ---- internals -----------------------------------------------------

    def _contents_folder(self, repo: str, path: str) -> Path:
        key = _hash_pair(repo, path)
        return self.root / "contents" / key

    def _contents_path(self, repo: str, path: str, author_date: date) -> Path:
        return self._contents_folder(repo, path) / f"{author_date.isoformat()}.bin"

    def _commits_folder(self, repo: str, path: str) -> Path:
        key = _hash_pair(repo, path)
        return self.root / "commits" / key

    def _commits_payload(self, repo: str, path: str) -> Path:
        return self._commits_folder(repo, path) / "commits.json"

    def _commits_fingerprint(self, repo: str, path: str) -> Path:
        return self._commits_folder(repo, path) / "fingerprint.sha256"


def compute_list_fingerprint(commits: List[CommitInfo]) -> str:
    """Hash a commit list by ``(author_date_iso, first-line message)``.

    The input order is irrelevant — entries are sorted by ISO author date to
    make the fingerprint stable across API pagination order. Only the first
    line of each commit message is used; subsequent lines can drift benignly
    without invalidating cached bodies.
    """
    items: list[str] = []
    for c in commits:
        first_line = c.message.splitlines()[0] if c.message else ""
        items.append(f"{c.author_date.isoformat()}|{first_line}")
    payload = "\n".join(sorted(items))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# ---- module-private helpers -------------------------------------------


def _hash_url(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def _hash_pair(repo: str, path: str) -> str:
    return hashlib.sha256(f"{repo}\x00{path}".encode("utf-8")).hexdigest()


def _is_expired(path: Path, ttl_seconds: int, *, now: Optional[float] = None) -> bool:
    t_now = time.time() if now is None else now
    return (t_now - path.stat().st_mtime) >= ttl_seconds


# ``datetime`` is imported so type-checkers in downstream modules that
# re-export our ``date`` parameter types see a concrete symbol.
_ = datetime  # noqa: F841


__all__ = [
    "CachedEtag",
    "DiskCache",
    "TTLS",
    "compute_list_fingerprint",
]
