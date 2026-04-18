"""Smoke test: every subcommand's ``--help`` exits 0."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from legalize_cli.__main__ import app


@pytest.mark.parametrize(
    "argv",
    [
        ["--help"],
        ["laws", "--help"],
        ["laws", "list", "--help"],
        ["laws", "get", "--help"],
        ["laws", "as-of", "--help"],
        ["laws", "article", "--help"],
        ["laws", "diff", "--help"],
        ["precedents", "--help"],
        ["precedents", "list", "--help"],
        ["precedents", "get", "--help"],
        ["search", "--help"],
        ["cache", "--help"],
        ["cache", "info", "--help"],
        ["cache", "clear", "--help"],
        ["auth", "--help"],
        ["auth", "status", "--help"],
    ],
)
def test_help_exits_zero(argv) -> None:
    runner = CliRunner()
    result = runner.invoke(app, argv)
    assert result.exit_code == 0, f"{argv} → {result.exit_code}\n{result.output}"


def test_readme_mentions_budget() -> None:
    from pathlib import Path

    readme = (Path(__file__).parent.parent.parent / "README.md").read_text()
    assert "시간당 60회" in readme
