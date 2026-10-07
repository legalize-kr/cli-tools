from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import anyio
from mcp import Client, StdioServerParameters

ROOT = Path(__file__).resolve().parents[2]


def test_fixture_subprocess_uses_stdio_protocol() -> None:
    async def run() -> None:
        env = {
            key: value for key, value in os.environ.items()
            if key not in ("GITHUB_TOKEN", "LEGALIZE_GITHUB_TOKEN")
        }
        params = StdioServerParameters(
            command=sys.executable,
            args=[str(ROOT / "tests/fixtures/mcp/stdio_server.py")],
            env=env,
            cwd=str(ROOT),
        )
        async with Client(params) as client:
            listed = await client.list_tools()
            assert len(listed.tools) == 11
            result = await client.call_tool("laws_list", {})
            assert not result.is_error
            assert json.loads(result.content[0].text) == result.structured_content
            invalid = await client.call_tool("laws_list", {"page": "1"})
            assert invalid.is_error
            assert json.loads(invalid.content[0].text)["error"]["code"] == "INVALID_INPUT"
    anyio.run(run)
