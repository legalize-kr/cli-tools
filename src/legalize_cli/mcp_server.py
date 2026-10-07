"""Compatibility entry point for the local MCP 2.x stdio server."""

try:
    from .mcp.server import build_server
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "MCP support requires the 'mcp' extra: pip install 'legalize-cli[mcp]'"
    ) from exc


def main() -> None:  # pragma: no cover
    build_server().run(transport="stdio")


if __name__ == "__main__":  # pragma: no cover
    main()
