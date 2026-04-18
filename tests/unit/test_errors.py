"""Tests for the exception hierarchy exit-code contract."""

from __future__ import annotations

from legalize_cli.util.errors import (
    AmbiguousHeadingLevelError,
    AuthError,
    ForcePushError,
    LegalizeError,
    NotFoundError,
    OfflineError,
    ParserError,
    RateLimitError,
)


def test_all_subclasses_inherit_from_base() -> None:
    for cls in (
        RateLimitError,
        NotFoundError,
        ForcePushError,
        AmbiguousHeadingLevelError,
        AuthError,
        OfflineError,
        ParserError,
    ):
        assert issubclass(cls, LegalizeError)


def test_exit_codes_are_distinct() -> None:
    codes = {
        LegalizeError.exit_code,
        RateLimitError.exit_code,
        NotFoundError.exit_code,
        ForcePushError.exit_code,
        AmbiguousHeadingLevelError.exit_code,
        AuthError.exit_code,
        OfflineError.exit_code,
        ParserError.exit_code,
    }
    # 8 distinct classes → 8 distinct codes.
    assert len(codes) == 8


def test_exit_code_values_are_stable() -> None:
    """Locks the documented exit-code table; README.md (Step 13) refers to these."""
    assert LegalizeError.exit_code == 1
    assert NotFoundError.exit_code == 4
    assert AmbiguousHeadingLevelError.exit_code == 5
    assert ForcePushError.exit_code == 6
    assert RateLimitError.exit_code == 7
    assert AuthError.exit_code == 8
    assert OfflineError.exit_code == 9
    assert ParserError.exit_code == 10


def test_all_codes_in_range_1_to_10() -> None:
    for cls in (
        LegalizeError,
        RateLimitError,
        NotFoundError,
        ForcePushError,
        AmbiguousHeadingLevelError,
        AuthError,
        OfflineError,
        ParserError,
    ):
        assert 1 <= cls.exit_code <= 10
