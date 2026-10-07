from __future__ import annotations

import json
import logging

import httpx
from mcp.types import CallToolResult, TextContent

from ..contracts.errors import ErrorDetail, ErrorResult
from ..github.search_code import SearchIncompleteError
from ..util.errors import (
    AmbiguousMatchError,
    ArticleNotFoundError,
    AuthError,
    ForcePushError,
    InputValidationError,
    LegalizeError,
    NotFoundError,
    ParserError,
    RateLimitError,
    RequestBudgetExceededError,
    ResponseTooLargeError,
    VersionNotFoundError,
)

logger = logging.getLogger(__name__)


def error_result(exc: Exception) -> ErrorResult:
    code = "INTERNAL_ERROR"
    retryable = False
    message = "예상하지 못한 내부 오류가 발생했습니다."
    candidates: list[str] = []
    candidate_total = 0
    source = None
    if isinstance(exc, InputValidationError):
        code, message = "INVALID_INPUT", str(exc)
    elif isinstance(exc, ArticleNotFoundError):
        code, message = "ARTICLE_NOT_FOUND", str(exc)
    elif isinstance(exc, VersionNotFoundError):
        code, message = "VERSION_NOT_FOUND", str(exc)
    elif isinstance(exc, AmbiguousMatchError):
        code = "AMBIGUOUS_MATCH"
        message = "동일 이름 또는 사건번호의 문서가 여러 개 있습니다. 전체 경로를 지정하세요."
        candidates = exc.candidates[:10]
        candidate_total = exc.candidate_total
    elif isinstance(exc, NotFoundError):
        code, message = "NOT_FOUND", "요청한 문서를 찾을 수 없습니다. 식별자와 경로를 확인하세요."
    elif isinstance(exc, AuthError):
        code, message = "AUTH_REQUIRED", "이 검색에는 실행 환경에 설정된 GitHub token이 필요합니다."
    elif isinstance(exc, RateLimitError):
        code, message, retryable = "RATE_LIMITED", "GitHub 요청 제한에 도달했습니다. 나중에 다시 시도하세요.", True
    elif isinstance(exc, SearchIncompleteError):
        code, message, retryable = "SEARCH_INCOMPLETE", "GitHub 본문 검색이 불완전했습니다. 질의를 좁히거나 tree 검색을 사용하세요.", True
    elif isinstance(exc, ForcePushError):
        code, message, retryable = "CACHE_INCONSISTENT", "원격 이력 변경으로 캐시 일관성을 확인하지 못했습니다.", True
    elif isinstance(exc, RequestBudgetExceededError):
        code, message = "REQUEST_BUDGET_EXCEEDED", str(exc)
    elif isinstance(exc, ResponseTooLargeError):
        code, message, source = "RESPONSE_TOO_LARGE", str(exc), exc.source
    elif isinstance(exc, ParserError):
        code, message = "PARSE_ERROR", "원천 문서 형식을 해석하지 못했습니다. 원문을 대조하세요."
    elif isinstance(exc, httpx.TimeoutException):
        code, message, retryable = "UPSTREAM_TIMEOUT", "GitHub 응답 시간이 초과되었습니다. 나중에 다시 시도하세요.", True
    elif isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status == 401:
            code, message = "AUTH_FAILED", "GitHub 인증에 실패했습니다. 로컬 token을 갱신하세요."
        elif status == 403:
            code, message = "UPSTREAM_FORBIDDEN", "GitHub가 요청을 거부했습니다. 권한과 운영 설정을 확인하세요."
        elif status == 429:
            code, message, retryable = "RATE_LIMITED", "GitHub 요청 제한에 도달했습니다.", True
        elif status >= 500:
            code, message, retryable = "UPSTREAM_UNAVAILABLE", "GitHub 서비스가 일시적으로 응답하지 않습니다.", True
    elif isinstance(exc, httpx.RequestError):
        code, message, retryable = "UPSTREAM_UNAVAILABLE", "GitHub 네트워크 요청에 실패했습니다.", True
    elif isinstance(exc, LegalizeError):
        code, message = "INTERNAL_ERROR", "요청을 처리하지 못했습니다. 범위를 줄이거나 지원을 요청하세요."
    else:
        logger.error("Unexpected MCP tool failure: %s", type(exc).__name__)
    return ErrorResult(error=ErrorDetail(
        code=code, message=message, retryable=retryable,
        candidates=candidates, candidate_total=candidate_total, source=source,
    ))


def tool_error_result(exc: Exception) -> CallToolResult:
    """Return a tool failure directly; SDK ToolError wraps its message in prose."""
    payload = error_result(exc).model_dump(mode="json", by_alias=True)
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(payload, ensure_ascii=False, separators=(",", ":")))],
        is_error=True,
    )


__all__ = ["error_result", "tool_error_result"]
