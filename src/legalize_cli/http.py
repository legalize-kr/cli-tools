"""Thin httpx wrapper that injects UA/auth/Accept and maps GitHub errors.

This is the single chokepoint for all GitHub API traffic; downstream modules
(``github/*``) call ``GitHubClient`` methods rather than using ``httpx``
directly. Keeping the chokepoint lets us:

- Attach the User-Agent required for rate-limit exemptions.
- Parse rate-limit headers into a typed snapshot on every response.
- Map ``403 + remaining=0`` to :class:`RateLimitError` and ``404`` to
  :class:`NotFoundError` consistently.
- Layer the ETag-aware disk cache on top without leaking httpx types.

Step 4 integrates the disk cache (``get_json(..., cache_ttl=...)``) on top of
the skeleton provided here.
"""

from __future__ import annotations

import json as _json
from typing import Any, Mapping, Optional

import httpx

from .auth import TokenSource, resolve_token
from .cache import DiskCache
from .config import GITHUB_API_ROOT, USER_AGENT
from .rate_limit import RateLimit
from .util.errors import NotFoundError, RateLimitError

#: Default Accept header for REST JSON responses.
_ACCEPT_JSON = "application/vnd.github+json"
#: Accept header for raw file bodies (used by contents/blobs).
_ACCEPT_RAW = "application/vnd.github.raw"
#: GitHub's current API version.
_API_VERSION = "2022-11-28"


class GitHubClient:
    """Typed-result wrapper around ``httpx.Client`` for the GitHub REST API."""

    def __init__(
        self,
        token: Optional[str] = None,
        token_source: TokenSource = "none",
        *,
        api_root: str = GITHUB_API_ROOT,
        transport: Optional[httpx.BaseTransport] = None,
        timeout: float = 30.0,
        cache: Optional[DiskCache] = None,
    ) -> None:
        if token is None and token_source == "none":
            token, token_source = resolve_token(None)

        self._token = token
        self.token_source: TokenSource = token_source
        self._api_root = api_root.rstrip("/")
        self._client = httpx.Client(
            transport=transport,
            timeout=timeout,
            headers=self._default_headers(),
        )
        self._cache: Optional[DiskCache] = cache
        #: Most recent rate-limit snapshot, or ``None`` until the first call.
        self.last_rate_limit: Optional[RateLimit] = None

    # ---- public API ----------------------------------------------------

    def get_json(
        self,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        accept: str = _ACCEPT_JSON,
        cache_ttl: Optional[int] = None,
    ) -> Any:
        """GET a REST endpoint and return parsed JSON.

        When a :class:`DiskCache` is attached AND ``cache_ttl`` is non-None, the
        client stores the response body + ETag and sends ``If-None-Match`` on
        subsequent requests. On 304 the cached body is reused with zero API
        cost. ``cache_ttl`` is accepted for forward compatibility; actual
        expiry is enforced by :class:`DiskCache` per-subdir TTLs.
        """
        url = self._api_url(path)
        cache_key = self._cache_key(url, params)
        extra_headers: dict[str, str] = {}

        if self._cache is not None and cache_ttl is not None:
            cached = self._cache.get_with_etag(cache_key)
            if cached is not None:
                extra_headers["If-None-Match"] = cached.etag

        response = self._request(
            "GET", url, params=params, accept=accept, extra_headers=extra_headers
        )

        if response.status_code == 304 and self._cache is not None:
            cached = self._cache.get_with_etag(cache_key)
            if cached is not None:
                return _json.loads(cached.body.decode("utf-8"))

        if self._cache is not None and cache_ttl is not None:
            etag = response.headers.get("ETag")
            if etag:
                self._cache.put_etag(cache_key, response.content, etag)

        return response.json()

    def get_raw(
        self,
        path: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
    ) -> bytes:
        """GET a REST endpoint with ``Accept: vnd.github.raw`` and return bytes."""
        response = self._request(
            "GET", self._api_url(path), params=params, accept=_ACCEPT_RAW
        )
        return response.content

    def get_url(self, url: str, *, accept: Optional[str] = None) -> bytes:
        """GET an absolute URL (used for ``raw.githubusercontent.com``)."""
        response = self._request("GET", url, accept=accept)
        return response.content

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "GitHubClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    # ---- internals -----------------------------------------------------

    def _default_headers(self) -> dict[str, str]:
        headers = {
            "User-Agent": USER_AGENT,
            "Accept": _ACCEPT_JSON,
            "X-GitHub-Api-Version": _API_VERSION,
        }
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"
        return headers

    def _api_url(self, path: str) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        if not path.startswith("/"):
            path = "/" + path
        return f"{self._api_root}{path}"

    def _request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        accept: Optional[str] = None,
        extra_headers: Optional[Mapping[str, str]] = None,
    ) -> httpx.Response:
        headers: dict[str, str] = {}
        if accept is not None:
            headers["Accept"] = accept
        if extra_headers:
            headers.update(extra_headers)

        response = self._client.request(method, url, params=params, headers=headers)
        self.last_rate_limit = RateLimit.from_headers(response.headers)

        if response.status_code == 304:
            # Caller is responsible for reading from cache; do not raise.
            return response

        if response.status_code == 404:
            raise NotFoundError(f"{method} {url} → 404 Not Found")

        if response.status_code == 403:
            remaining_raw = response.headers.get("x-ratelimit-remaining")
            if remaining_raw is not None and remaining_raw.strip() == "0":
                reset = self.last_rate_limit.reset if self.last_rate_limit else None
                raise RateLimitError(
                    f"GitHub rate limit exhausted; resets at {reset.isoformat() if reset else '<unknown>'}"
                )

        response.raise_for_status()
        return response

    def _cache_key(self, url: str, params: Optional[Mapping[str, Any]]) -> str:
        """Deterministic URL+params key for the ETag cache."""
        if not params:
            return url
        serialized = "&".join(f"{k}={params[k]}" for k in sorted(params))
        return f"{url}?{serialized}"


__all__ = ["GitHubClient"]
