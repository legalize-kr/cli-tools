from __future__ import annotations

import re
from datetime import date as Date, datetime, timedelta, timezone
from typing import Optional

from ..util.errors import InputValidationError

KST = timezone(timedelta(hours=9))
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_date_or_today(raw: Optional[str], *, now: Optional[datetime] = None) -> Date:
    if raw is not None:
        if not _DATE_RE.fullmatch(raw):
            raise InputValidationError("날짜는 YYYY-MM-DD 형식이어야 합니다.")
        try:
            return Date.fromisoformat(raw)
        except ValueError as exc:
            raise InputValidationError("실재하는 달력 날짜를 입력하세요.") from exc
    clock = now or datetime.now(KST)
    if clock.tzinfo is None or clock.utcoffset() is None:
        raise InputValidationError("테스트 clock은 timezone-aware datetime이어야 합니다.")
    return clock.astimezone(KST).date()


__all__ = ["KST", "parse_date_or_today"]
