from __future__ import annotations

import anyio
import httpx
import json
from mcp import Client
from typer.testing import CliRunner

from legalize_cli.__main__ import app
from legalize_cli.http import GitHubClient
from legalize_cli.mcp.server import build_server
from legalize_cli.services.context import ServiceContext
from .conftest import install_client_factory

SHA = "a" * 40
LAW_PATH = "kr/테스트법/법률(법률).md"
PRECEDENT = "민사/대법원/대법원_2026-01-01_2026다1.md"
BODY = "---\n제목: 테스트법\n공포일자: 2026-01-01\n시행일자: 2026-01-01\n출처: https://www.law.go.kr/법령/테스트법\n---\n## 제1편 총칙\n### 제1장 옛 장\n#### 제1절 옛 절\n##### 제1조\n옛 규정\n### 제2장 새 장\n##### 제2조\n새 규정\n"


def client(paths):
    def handler(request):
        url = str(request.url)
        if "/git/ref/heads/main" in url:
            return httpx.Response(200, json={"object": {"type": "commit", "sha": SHA}})
        if "/git/trees/" in url:
            return httpx.Response(200, json={"truncated": False, "tree": [
                {"path": path, "type": "blob", "sha": SHA} for path in paths if (path.startswith("kr/") if "/repos/legalize-kr/legalize-kr/" in url else not path.startswith("kr/"))]})
        if "/commits" in url:
            assert request.url.params["path"] in paths
            return httpx.Response(200, json=[{"sha": SHA, "commit": {
                "author": {"date": "2026-01-01T00:00:00Z"},
                "committer": {"date": "2026-01-01T00:00:00Z"}}}])
        if "/contents/" in url and not request.url.params.get("ref"):
            return httpx.Response(200, json=[{"path": path, "type": "file"} for path in paths])
        if "/contents/" in url and request.headers.get("accept") != "application/vnd.github.raw":
            return httpx.Response(200, json=[{"path": path, "type": "file"} for path in paths])
        if "/contents/" in url:
            return httpx.Response(200, text=BODY)
        return httpx.Response(404)
    return GitHubClient(token=None, token_source="none", transport=httpx.MockTransport(handler))


def test_current_paths_through_cli_and_mcp(monkeypatch):
    install_client_factory(monkeypatch, lambda *_args: (client([LAW_PATH]), None))
    result = CliRunner().invoke(app, ["laws", "article", "테스트법", "2", "--date", "2026-02-01", "--json"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["parent_structure"] == ["제1편 총칙", "제2장 새 장"]

    async def run():
        async with Client(build_server(lambda: ServiceContext(client([LAW_PATH, PRECEDENT]), None))) as connection:
            laws = await connection.call_tool("laws_list", {})
            assert [entry["path"] for entry in laws.structured_content["items"]] == [LAW_PATH]
            article = await connection.call_tool("laws_article", {"law_name": LAW_PATH, "article_no": "2", "date": "2026-02-01"})
            assert not article.is_error, article.content
            assert article.structured_content["source"]["path"] == LAW_PATH
            assert article.structured_content["parent_structure"] == ["제1편 총칙", "제2장 새 장"]
            precedents = await connection.call_tool("precedents_list", {})
            assert precedents.structured_content["items"][0]["사건번호"] == "2026다1"
            precedent = await connection.call_tool("precedents_get", {"identifier": "2026다1"})
            assert not precedent.is_error, precedent.content
            assert precedent.structured_content["source"]["path"] == PRECEDENT
    anyio.run(run)


def test_ambiguous_law_requires_selection_over_mcp():
    paths = [LAW_PATH, "kr/테스트법/법률(법률)(폐지).md"]
    async def run():
        async with Client(build_server(lambda: ServiceContext(client(paths), None))) as connection:
            result = await connection.call_tool("laws_get", {"law_name": "테스트법", "date": "2026-02-01"})
            assert result.is_error
            error = json.loads(result.content[0].text)["error"]
            assert error["code"] == "AMBIGUOUS_MATCH"
            assert error["candidates"] == sorted(paths)
    anyio.run(run)


def test_cli_full_path_reports_selected_category(monkeypatch):
    path = "kr/테스트법/시행령(대통령령).md"
    install_client_factory(monkeypatch, lambda *_args: (client([path]), None))
    for command in (["get", path], ["article", path, "2"]):
        result = CliRunner().invoke(app, ["laws", *command, "--date", "2026-02-01", "--json"])
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["law"] == "테스트법"
        assert payload["category"] == "시행령"
        assert payload["path"] == path
