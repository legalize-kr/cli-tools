from __future__ import annotations

import json

import anyio
from mcp import Client

from legalize_cli.mcp.server import build_server


def test_local_path_and_secret_values_are_not_echoed() -> None:
    secret = "TEST_DUMMY_SECRET_DO_NOT_ECHO"

    async def run() -> None:
        async with Client(build_server()) as client:
            listed = await client.list_tools()
            for tool in listed.tools:
                assert "token" not in tool.input_schema.get("properties", {})
                assert "legacy_map_path" not in tool.input_schema.get("properties", {})
            result = await client.call_tool("precedents_get", {
                "identifier": "../" + secret + ".md",
                "legacy_map_path": "/private/" + secret,
            })
            assert result.is_error
            text = result.content[0].text
            assert secret not in text
            assert json.loads(text)["error"]["code"] == "INVALID_INPUT"
    anyio.run(run)
