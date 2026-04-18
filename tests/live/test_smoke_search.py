"""Live smoke: search works with a token (or degrades gracefully without)."""

from __future__ import annotations

import json
import os

import pytest
from typer.testing import CliRunner

from legalize_cli.__main__ import app


@pytest.mark.live
def test_live_search_precedent_metadata() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["search", "소유권이전", "--in", "precedents", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert len(data["items"]) >= 1


@pytest.mark.live
@pytest.mark.skipif(not os.environ.get("GITHUB_TOKEN"), reason="code search needs token")
def test_live_search_code_with_token() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["search", "개인정보", "--in", "laws", "--strategy", "code", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["strategy_used"] == "code"
