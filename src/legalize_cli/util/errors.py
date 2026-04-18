"""Typed exception hierarchy for legalize-cli.

Each subclass carries a distinct ``exit_code`` used by the CLI layer to map
domain failures to deterministic shell exit codes. Keep codes stable — they
are part of the public contract documented in README.md (Step 13).
"""

from __future__ import annotations


class LegalizeError(Exception):
    """Base class for all legalize-cli domain errors.

    Subclasses override :attr:`exit_code` to surface a distinct shell code.
    The default ``1`` mirrors generic failure.
    """

    exit_code: int = 1


class RateLimitError(LegalizeError):
    """GitHub API rate limit exhausted (403 + ``X-RateLimit-Remaining: 0``)."""

    exit_code: int = 7


class NotFoundError(LegalizeError):
    """Requested resource (law, path, commit) does not exist."""

    exit_code: int = 4


class ForcePushError(LegalizeError):
    """Cache coherence broken by an upstream force-push (pipeline rebuild)."""

    exit_code: int = 6


class AmbiguousHeadingLevelError(LegalizeError):
    """Article-level headings in a law markdown are not monotonically one level.

    Raised by :mod:`legalize_cli.laws.articles` when the same document uses
    article-numbered headings at mutually incompatible depths (e.g. ``###``
    and ``#####`` intermixed with no reducible rule).
    """

    exit_code: int = 5


class AuthError(LegalizeError):
    """Authentication problem (bad token, missing scope)."""

    exit_code: int = 8


class OfflineError(LegalizeError):
    """Command required a network fetch but ``--offline`` was set."""

    exit_code: int = 9


class ParserError(LegalizeError):
    """Generic parsing failure (frontmatter, metadata.json, tree)."""

    exit_code: int = 10


__all__ = [
    "LegalizeError",
    "RateLimitError",
    "NotFoundError",
    "ForcePushError",
    "AmbiguousHeadingLevelError",
    "AuthError",
    "OfflineError",
    "ParserError",
]
