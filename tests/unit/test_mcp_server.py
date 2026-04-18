"""Unit tests for MCP server tool registration and structure."""

from __future__ import annotations

import pytest

mcp_pkg = pytest.importorskip("mcp", reason="mcp extra not installed")


def test_mcp_server_importable():
    from legalize_cli import mcp_server

    assert hasattr(mcp_server, "mcp")
    assert hasattr(mcp_server, "main")


def test_all_tools_registered():
    from legalize_cli import mcp_server

    expected = {
        "laws_list",
        "laws_get",
        "laws_article",
        "search",
        "precedents_list",
        "precedents_get",
    }
    for name in expected:
        assert hasattr(mcp_server, name), f"tool '{name}' not found in mcp_server"


def test_mcp_instance_name():
    from legalize_cli.mcp_server import mcp

    assert mcp.name == "legalize-kr"


def test_mcp_cmd_importable():
    from legalize_cli.commands.mcp_cmd import mcp_app

    assert mcp_app is not None


def test_mcp_help_reachable():
    """``legalize mcp --help`` exits 0 and lists the serve subcommand."""
    from typer.testing import CliRunner
    from legalize_cli.__main__ import app

    result = CliRunner().invoke(app, ["mcp", "--help"])
    assert result.exit_code == 0
    assert "serve" in result.output
