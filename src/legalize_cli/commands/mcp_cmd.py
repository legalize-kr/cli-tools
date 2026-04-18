"""``legalize mcp serve`` — run the MCP server over stdio."""

from __future__ import annotations

import typer

mcp_app = typer.Typer(
    name="mcp",
    help="MCP server for LLM/agent integration (Claude Desktop, Cursor, etc.).",
    no_args_is_help=True,
)


@mcp_app.command("serve")
def serve_cmd() -> None:
    """Start the MCP server using stdio transport.

    Configure in Claude Desktop / Cursor / any MCP-compatible client by
    pointing the server command at ``legalize mcp serve`` or ``legalize-mcp``.
    Reads GITHUB_TOKEN from the environment automatically.
    """
    try:
        from ..mcp_server import main
    except ImportError:
        typer.echo(
            "error: MCP support requires the 'mcp' extra.\n"
            "       pip install 'legalize-cli[mcp]'",
            err=True,
        )
        raise typer.Exit(1)

    main()  # pragma: no cover


__all__ = ["mcp_app"]
