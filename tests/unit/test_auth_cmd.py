"""Tests for ``legalize auth status``."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from legalize_cli.__main__ import app

runner = CliRunner()


def test_auth_status_no_token(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("LEGALIZE_GITHUB_TOKEN", raising=False)
    result = runner.invoke(app, ["auth", "status"])
    assert result.exit_code == 0
    assert "not set" in result.output


def test_auth_status_json_no_token(monkeypatch) -> None:
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("LEGALIZE_GITHUB_TOKEN", raising=False)
    result = runner.invoke(app, ["auth", "status", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["schema_version"] == "1.0"
    assert data["kind"] == "auth.status"
    assert data["token_present"] is False
    assert data["token_source"] == "none"


def test_auth_status_with_token(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test1234567890abcdef")
    result = runner.invoke(app, ["auth", "status"])
    assert result.exit_code == 0
    assert "present" in result.output


def test_auth_status_json_with_token(monkeypatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test1234567890abcdef")
    result = runner.invoke(app, ["auth", "status", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["token_present"] is True
    assert data["token_source"] in ("flag", "GITHUB_TOKEN")
