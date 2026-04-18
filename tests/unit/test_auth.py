"""Tests for :mod:`legalize_cli.auth` token resolution."""

from __future__ import annotations

import pytest

from legalize_cli.auth import mask_token, resolve_token


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove both token env vars so precedence tests are hermetic."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("LEGALIZE_GITHUB_TOKEN", raising=False)


def test_cli_flag_wins_over_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "from-env")
    monkeypatch.setenv("LEGALIZE_GITHUB_TOKEN", "from-legalize")

    token, source = resolve_token("from-flag")

    assert token == "from-flag"
    assert source == "flag"


def test_github_token_beats_legalize_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "from-env")
    monkeypatch.setenv("LEGALIZE_GITHUB_TOKEN", "from-legalize")

    token, source = resolve_token(None)

    assert token == "from-env"
    assert source == "GITHUB_TOKEN"


def test_legalize_token_used_when_github_token_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LEGALIZE_GITHUB_TOKEN", "from-legalize")

    token, source = resolve_token(None)

    assert token == "from-legalize"
    assert source == "LEGALIZE_GITHUB_TOKEN"


def test_none_when_nothing_set() -> None:
    token, source = resolve_token(None)

    assert token is None
    assert source == "none"


def test_empty_string_cli_flag_falls_through(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "from-env")

    token, source = resolve_token("")

    assert token == "from-env"
    assert source == "GITHUB_TOKEN"


def test_mask_token_hides_long_token() -> None:
    assert mask_token("ghp_abcdefghijklmnop") == "ghp_…****"


def test_mask_token_short_value_fully_masked() -> None:
    assert mask_token("short") == "****"


def test_mask_token_none() -> None:
    assert mask_token(None) == "<none>"
