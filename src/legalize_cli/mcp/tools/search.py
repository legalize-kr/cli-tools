from __future__ import annotations

from typing import Annotated, Literal

from mcp.server import MCPServer
from mcp.types import CallToolResult
from pydantic import Field

from ...contracts.requests import SearchRequest
from ...contracts.search import SearchResult
from ...services.context import ContextFactory
from ...services.search import search_documents
from ..errors import tool_error_result
from ..results import render_result
from .laws import READ_ONLY


def register_search_tool(server: MCPServer, context_factory: ContextFactory) -> None:
    @server.tool(title="한국 법률자료 검색", annotations=READ_ONLY, structured_output=True,
                 description="code는 GitHub 본문 인덱스, tree와 metadata는 저장소 경로 검색입니다. 과거 snapshot 전체 본문 검색이 아니며 부분 실패와 실제 검색 범위를 결과에 표시합니다.")
    def search(
        keyword: Annotated[str, Field(min_length=1, max_length=200)],
        scope: Literal["laws", "precedents", "admrules", "ordinances", "all"] = "all",
        limit: Annotated[int, Field(strict=True, ge=1, le=100)] = 30,
        strategy: Literal["auto", "code", "tree", "metadata"] = "auto",
    ) -> Annotated[CallToolResult, SearchResult]:
        try:
            request = SearchRequest(keyword=keyword, scope=scope, limit=limit, strategy=strategy)
            with context_factory() as context:
                return render_result(search_documents(context, request))
        except Exception as exc:
            return tool_error_result(exc)


__all__ = ["register_search_tool"]
