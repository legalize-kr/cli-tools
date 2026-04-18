"""Live smoke: ``laws list`` returns >=3000 law entries."""

from __future__ import annotations

import json

import pytest
from typer.testing import CliRunner

from legalize_cli.__main__ import app


@pytest.mark.live
def test_live_laws_list_returns_many_entries() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["laws", "list", "--json", "--page-size", "1"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["total"] >= 3000
