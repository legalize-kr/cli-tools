"""GitHub rate-limit header parsing.

GitHub returns rate-limit state on every REST response via:

- ``X-RateLimit-Limit`` — quota per window (60 anon, 5000 auth).
- ``X-RateLimit-Remaining`` — requests left in the current window.
- ``X-RateLimit-Reset`` — unix epoch seconds when the window resets.
- ``X-RateLimit-Used`` — requests already consumed.

``X-RateLimit-Reset`` is normally a unix epoch integer, but we also accept
ISO-8601 timestamps so the dataclass round-trips through cached/serialized
forms without surprise.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping, Optional

from dateutil import parser as dateparser


@dataclass(frozen=True)
class RateLimit:
    """Snapshot of GitHub's rate-limit state from a single response."""

    remaining: int
    limit: int
    reset: datetime
    used: int

    @classmethod
    def from_headers(cls, headers: Mapping[str, str]) -> Optional["RateLimit"]:
        """Parse from a case-insensitive header mapping.

        Returns ``None`` if any of the four core headers are missing — GitHub
        omits them for a handful of endpoints, and callers should treat that
        as "no accounting available" rather than synthesize zeros.
        """
        try:
            limit = _get_header(headers, "x-ratelimit-limit")
            remaining = _get_header(headers, "x-ratelimit-remaining")
            reset_raw = _get_header(headers, "x-ratelimit-reset")
            used = _get_header(headers, "x-ratelimit-used")
        except KeyError:
            return None

        if limit is None or remaining is None or reset_raw is None or used is None:
            return None

        return cls(
            remaining=int(remaining),
            limit=int(limit),
            reset=parse_reset(reset_raw),
            used=int(used),
        )


def parse_reset(raw: str) -> datetime:
    """Parse an ``X-RateLimit-Reset`` value into a UTC-aware datetime.

    Accepts unix epoch seconds (the GitHub wire format) and ISO-8601 strings
    (useful when a cached value is rehydrated from JSON).
    """
    s = str(raw).strip()
    if s.isdigit():
        return datetime.fromtimestamp(int(s), tz=timezone.utc)
    dt = dateparser.isoparse(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _get_header(headers: Mapping[str, str], name: str) -> Optional[str]:
    """Case-insensitive header lookup that tolerates mapping shapes.

    ``httpx.Headers`` is already case-insensitive, but plain ``dict``s used in
    tests are not — walk the keys defensively.
    """
    if name in headers:
        return headers[name]
    lower = name.lower()
    for key, value in headers.items():
        if key.lower() == lower:
            return value
    return None


__all__ = ["RateLimit", "parse_reset"]
