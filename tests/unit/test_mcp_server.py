from __future__ import annotations

import json

import anyio
import httpx
import jsonschema
from mcp import Client

from legalize_cli.http import GitHubClient
from legalize_cli.mcp.server import build_server
from legalize_cli.services.context import ServiceContext

SHA = "a" * 40


def _factory() -> ServiceContext:
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/git/ref/heads/main" in url:
            return httpx.Response(200, json={"object": {"type": "commit", "sha": SHA}})
        if "/git/trees/" in url:
            return httpx.Response(200, json={
                "truncated": False,
                "tree": [{"path": "kr/민법/법률.md", "type": "blob", "sha": "b" * 40}],
            })
        return httpx.Response(404, json={"message": "not found"})
    client = GitHubClient(token=None, token_source="none", transport=httpx.MockTransport(handler))
    return ServiceContext(client=client, cache=None)


def test_mcp_tools_and_contract_metadata() -> None:
    async def run() -> None:
        async with Client(build_server(_factory)) as client:
            listed = await client.list_tools()
            expected = {
                "laws_list", "laws_get", "laws_article", "laws_diff", "search",
                "precedents_list", "precedents_get", "admrules_list", "admrules_get",
                "ordinances_list", "ordinances_get",
            }
            assert {tool.name for tool in listed.tools} == expected
            for tool in listed.tools:
                assert tool.title
                assert tool.output_schema
                assert tool.annotations.read_only_hint is True
                assert tool.annotations.destructive_hint is False
                assert tool.annotations.idempotent_hint is True
                assert tool.annotations.open_world_hint is True
            precedent = next(tool for tool in listed.tools if tool.name == "precedents_get")
            assert "legacy_map_path" not in precedent.input_schema["properties"]
            listing = next(tool for tool in listed.tools if tool.name == "laws_list")
            assert listing.input_schema["properties"]["page"]["minimum"] == 1
            assert listing.input_schema["properties"]["page_size"]["maximum"] == 100
            lookup = next(tool for tool in listed.tools if tool.name == "laws_get")
            assert lookup.input_schema["properties"]["law_name"]["maxLength"] == 200
    anyio.run(run)


def test_success_has_equal_text_and_structured_json() -> None:
    async def run() -> None:
        async with Client(build_server(_factory)) as client:
            result = await client.call_tool("laws_list", {})
            assert result.is_error is False
            assert json.loads(result.content[0].text) == result.structured_content
            assert result.structured_content["schema_version"] == "2.0"
            assert result.structured_content["snapshot"]["ref"] == SHA
            tool = next(tool for tool in (await client.list_tools()).tools if tool.name == "laws_list")
            jsonschema.validate(result.structured_content, tool.output_schema)
    anyio.run(run)


def test_strict_validation_returns_project_error() -> None:
    async def run() -> None:
        async with Client(build_server(_factory)) as client:
            for arguments in ({"page": 0}, {"page": "1"}, {"unknown": True}):
                result = await client.call_tool("laws_list", arguments)
                payload = json.loads(result.content[0].text)
                assert result.is_error is True
                assert payload["error"]["code"] == "INVALID_INPUT"
            traversal = await client.call_tool("precedents_get", {"identifier": "../secret.md"})
            assert traversal.is_error is True
            assert json.loads(traversal.content[0].text)["error"]["code"] == "INVALID_INPUT"
            control = await client.call_tool("laws_get", {"law_name": "민법\n"})
            assert control.is_error is True
            assert json.loads(control.content[0].text)["error"]["code"] == "INVALID_INPUT"
    anyio.run(run)


def test_document_tools_round_trip_and_match_output_schemas() -> None:
    paths = {
        "precedent-kr": "민사/대법원/대법원_2026-01-01_2026다1.md",
        "admrule-kr": "기관/고시/예시규칙/본문.md",
        "ordinance-kr": "서울특별시/본청/조례/예시조례/본문.md",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "/git/ref/heads/main" in url:
            return httpx.Response(200, json={"object": {"type": "commit", "sha": SHA}})
        repo = next(name for name in paths if f"/{name}/" in url)
        if "/git/trees/" in url:
            return httpx.Response(200, json={
                "truncated": False,
                "tree": [{"path": paths[repo], "type": "blob", "sha": "b" * 40}],
            })
        assert "/contents/" in url
        assert request.url.params["ref"] == SHA
        return httpx.Response(200, content=b"---\n---\nfixture body")

    def factory() -> ServiceContext:
        client = GitHubClient(token="", token_source="none", transport=httpx.MockTransport(handler))
        return ServiceContext(client=client, cache=None)

    async def run() -> None:
        async with Client(build_server(factory)) as client:
            schemas = {tool.name: tool.output_schema for tool in (await client.list_tools()).tools}
            for prefix, repo in (
                ("precedents", "precedent-kr"),
                ("admrules", "admrule-kr"),
                ("ordinances", "ordinance-kr"),
            ):
                for suffix, arguments in (("list", {}), ("get", {"identifier": paths[repo]})):
                    name = f"{prefix}_{suffix}"
                    result = await client.call_tool(name, arguments)
                    assert result.is_error is False, result.content
                    assert json.loads(result.content[0].text) == result.structured_content
                    assert result.structured_content["schema_version"] == "2.0"
                    jsonschema.validate(result.structured_content, schemas[name])
                    assert result.structured_content["source" if suffix == "get" else "snapshot"]["ref"] == SHA

    anyio.run(run)


def test_mcp_cmd_help_reachable() -> None:
    from typer.testing import CliRunner
    from legalize_cli.__main__ import app

    result = CliRunner().invoke(app, ["mcp", "--help"])
    assert result.exit_code == 0
    assert "serve" in result.output
