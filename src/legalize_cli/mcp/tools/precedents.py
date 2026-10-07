from __future__ import annotations

from typing import Annotated, Optional

from mcp.server import MCPServer
from mcp.types import CallToolResult
from pydantic import Field

from ...contracts.precedents import PrecedentDocumentResult, PrecedentListResult
from ...contracts.requests import PrecedentGetRequest, PrecedentListRequest
from ...services.context import ContextFactory
from ...services.precedents import get_precedent, list_precedents
from ..errors import tool_error_result
from ..results import render_result
from .laws import READ_ONLY


def register_precedent_tools(server: MCPServer, context_factory: ContextFactory) -> None:
    @server.tool(title="한국 판례 목록 조회", annotations=READ_ONLY, structured_output=True,
                 description="고정한 미러 snapshot의 판례 목록을 조회합니다. 판례일련번호 필드는 현재 저장소 경로 값입니다.")
    def precedents_list(
        court: Optional[Annotated[str, Field(min_length=1, max_length=200)]] = None,
        type_: Optional[Annotated[str, Field(min_length=1, max_length=200)]] = None,
        page: Annotated[int, Field(strict=True, ge=1, le=10_000)] = 1,
        page_size: Annotated[int, Field(strict=True, ge=1, le=100)] = 50,
    ) -> Annotated[CallToolResult, PrecedentListResult]:
        try:
            request = PrecedentListRequest(court=court, type_=type_, page=page, page_size=page_size)
            with context_factory() as context:
                return render_result(list_precedents(context, request))
        except Exception as exc:
            return tool_error_result(exc)

    @server.tool(title="한국 판례 전문 조회", annotations=READ_ONLY, structured_output=True,
                 description="사건번호 또는 저장소 상대 Markdown 경로로 조회합니다. 숫자형 판례 ID와 로컬 mapping 파일은 받지 않으며 모호한 사건번호는 임의 선택하지 않습니다.")
    def precedents_get(
        identifier: Annotated[str, Field(min_length=1, max_length=1024)],
    ) -> Annotated[CallToolResult, PrecedentDocumentResult]:
        try:
            request = PrecedentGetRequest(identifier=identifier)
            with context_factory() as context:
                return render_result(get_precedent(context, request))
        except Exception as exc:
            return tool_error_result(exc)


__all__ = ["register_precedent_tools"]
