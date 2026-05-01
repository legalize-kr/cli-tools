"""Live smoke: 민법 latest commit is parseable."""

from __future__ import annotations

import json
from datetime import date

import pytest
from typer.testing import CliRunner

from legalize_cli.__main__ import app


@pytest.mark.live
def test_live_mingbeop_get() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["laws", "get", "민법", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["law"] == "민법"
    assert data["schema_version"] == "1.0"
    date.fromisoformat(data["resolved_commit_date"])
