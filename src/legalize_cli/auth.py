"""GitHub token resolution.

Precedence (highest → lowest):
1. Explicit ``--token`` CLI flag.
2. ``$GITHUB_TOKEN``.
3. ``$LEGALIZE_GITHUB_TOKEN``.
4. None (anonymous; subject to the 60 req/hr unauthenticated quota).

Returns a ``(token, source)`` tuple so callers can surface provenance in
``legalize auth status --json`` without re-reading the environment.
"""

from __future__ import annotations

import os
from typing import Literal, Optional, Tuple

TokenSource = Literal["flag", "GITHUB_TOKEN", "LEGALIZE_GITHUB_TOKEN", "none"]


def resolve_token(cli_token: Optional[str] = None) -> Tuple[Optional[str], TokenSource]:
    """Resolve the GitHub token according to the documented precedence.

    :param cli_token: Value passed via ``--token`` on the CLI. ``None`` or an
        empty string is treated as "flag not set".
    :returns: ``(token, source)``. ``token`` is ``None`` when no source yields
        a non-empty value, and ``source`` is ``"none"`` in that case.
    """
    if cli_token:
        return cli_token, "flag"

    env_github = os.environ.get("GITHUB_TOKEN")
    if env_github:
        return env_github, "GITHUB_TOKEN"

    env_legalize = os.environ.get("LEGALIZE_GITHUB_TOKEN")
    if env_legalize:
        return env_legalize, "LEGALIZE_GITHUB_TOKEN"

    return None, "none"


def mask_token(token: Optional[str]) -> str:
    """Return a log-safe representation of a token.

    Keeps the first 4 chars so operators can confirm which token is loaded
    without leaking the secret. Returns ``"<none>"`` when no token is present.
    """
    if not token:
        return "<none>"
    if len(token) <= 8:
        return "****"
    return f"{token[:4]}…{'*' * 4}"


__all__ = ["resolve_token", "mask_token", "TokenSource"]
