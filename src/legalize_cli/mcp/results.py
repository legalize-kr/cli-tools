from __future__ import annotations

import json

from pydantic import BaseModel
from mcp.types import CallToolResult, TextContent

from ..util.errors import ResponseTooLargeError

MAX_CANONICAL_BYTES = 256 * 1024
MAX_TOOL_RESULT_BYTES = 1024 * 1024


def render_result(result: BaseModel) -> CallToolResult:
    payload = result.model_dump(mode="json", by_alias=True)
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    source = payload.get("source") if isinstance(payload, dict) else None
    if len(text.encode("utf-8")) > MAX_CANONICAL_BYTES:
        raise ResponseTooLargeError(
            "완전한 응답이 256 KiB 한도를 초과합니다. 조회 범위를 줄이거나 원문 링크를 사용하세요.",
            source=source,
        )
    rendered = CallToolResult(
        content=[TextContent(type="text", text=text)],
        structured_content=payload,
    )
    wire = rendered.model_dump_json(by_alias=True)
    if len(wire.encode("utf-8")) > MAX_TOOL_RESULT_BYTES:
        raise ResponseTooLargeError(
            "text와 structuredContent를 포함한 응답이 1 MiB 한도를 초과합니다.",
            source=source,
        )
    return rendered


__all__ = ["MAX_CANONICAL_BYTES", "MAX_TOOL_RESULT_BYTES", "render_result"]
