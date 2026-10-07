from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field

from .common import ContractModel, SourceReference


class ErrorDetail(ContractModel):
    code: str
    message: str
    retryable: bool
    retry_after_seconds: Optional[int] = None
    candidates: list[str] = Field(default_factory=list)
    candidate_total: int = 0
    source: Optional[SourceReference] = None


class ErrorResult(ContractModel):
    schema_version: Literal["2.0"] = "2.0"
    kind: Literal["error"] = "error"
    error: ErrorDetail


__all__ = ["ErrorDetail", "ErrorResult"]
