from __future__ import annotations

from ..contracts.requests import _safe_identifier
from ..util.errors import InputValidationError


def validate_repository_identifier(value: str) -> str:
    try:
        return _safe_identifier(value)
    except ValueError as exc:
        raise InputValidationError(str(exc)) from exc


__all__ = ["validate_repository_identifier"]
