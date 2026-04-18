"""Shared helpers for the ``commands/*`` CLI layer.

Centralizes:

- Global-flag parsing (``--token``, ``--no-cache``, ``--cache-dir``, ``--offline``).
- :class:`GitHubClient` + :class:`DiskCache` factory so each subcommand does
  not re-wire the plumbing.
- JSON-output helpers that enforce the top-level ``schema_version: "1.0"``
  contract (see plan §1 Principle 4).

Exposed ``GlobalOpts`` is a plain dataclass — typer cannot type-check a
dataclass as a ``--`` option natively, so each command explicitly declares the
individual flags and packs them via :func:`build_global_opts`.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

import typer

from ..auth import resolve_token
from ..cache import DiskCache
from ..config import DEFAULT_CACHE_DIR
from ..http import GitHubClient
from .errors import LegalizeError

#: Every ``--json`` payload carries this top-level literal.
SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class GlobalOpts:
    """Parsed values of the CLI-wide flags."""

    token: Optional[str]
    no_cache: bool
    cache_dir: Optional[Path]
    offline: bool
    json_output: bool


def build_global_opts(
    token: Optional[str],
    no_cache: bool,
    cache_dir: Optional[Path],
    offline: bool,
    json_output: bool,
) -> GlobalOpts:
    return GlobalOpts(
        token=token or None,
        no_cache=no_cache,
        cache_dir=cache_dir,
        offline=offline,
        json_output=json_output,
    )


def make_client(opts: GlobalOpts) -> tuple[GitHubClient, Optional[DiskCache]]:
    """Construct a :class:`GitHubClient` + (optional) :class:`DiskCache`."""
    token, source = resolve_token(opts.token)
    cache: Optional[DiskCache] = None
    if not opts.no_cache:
        cache = DiskCache(opts.cache_dir or DEFAULT_CACHE_DIR)
    client = GitHubClient(token=token, token_source=source, cache=cache)
    return client, cache


def _json_default(value: Any) -> Any:
    """JSON fallback for :class:`date` / :class:`datetime` values from pydantic."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def emit_json(payload: dict[str, Any], *, kind: str) -> None:
    """Write a JSON payload to stdout with the schema_version + kind headers."""
    payload = {"schema_version": SCHEMA_VERSION, "kind": kind, **payload}
    json.dump(payload, sys.stdout, ensure_ascii=False, default=_json_default)
    sys.stdout.write("\n")


def die(message: str, *, code: int = 1) -> "typer.Exit":
    """Print ``message`` to stderr and return a :class:`typer.Exit`."""
    sys.stderr.write(f"error: {message}\n")
    return typer.Exit(code=code)


def handle_domain_error(exc: LegalizeError) -> "typer.Exit":
    """Map a :class:`LegalizeError` to a typer exit with its declared code."""
    return die(str(exc), code=exc.exit_code)


__all__ = [
    "GlobalOpts",
    "SCHEMA_VERSION",
    "build_global_opts",
    "make_client",
    "emit_json",
    "die",
    "handle_domain_error",
]
