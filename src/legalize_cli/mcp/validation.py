from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from mcp.types import CallToolResult, TextContent
from pydantic import ValidationError

from ..contracts.errors import ErrorDetail, ErrorResult
from ..contracts.requests import REQUEST_MODELS


def _invalid_result(exc: ValidationError) -> CallToolResult:
    fields = sorted({".".join(str(part) for part in item["loc"]) for item in exc.errors()})
    message = "입력 형식이 올바르지 않습니다."
    if fields:
        message += " 확인할 필드: " + ", ".join(fields)
    payload = ErrorResult(error=ErrorDetail(
        code="INVALID_INPUT", message=message, retryable=False
    )).model_dump(mode="json", by_alias=True)
    return CallToolResult(
        content=[TextContent(type="text", text=json.dumps(payload, ensure_ascii=False, separators=(",", ":")))],
        is_error=True,
    )


class StrictToolArgumentsMiddleware:
    async def __call__(self, ctx: Any, call_next: Any) -> Any:
        if ctx.method != "tools/call" or not isinstance(ctx.params, Mapping):
            return await call_next(ctx)
        name = ctx.params.get("name")
        model = REQUEST_MODELS.get(name)
        if model is None:
            return await call_next(ctx)
        arguments = ctx.params.get("arguments", {})
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            return await call_next(ctx)
        try:
            model.model_validate(arguments)
        except ValidationError as exc:
            return _invalid_result(exc)
        return await call_next(ctx)


__all__ = ["StrictToolArgumentsMiddleware"]
