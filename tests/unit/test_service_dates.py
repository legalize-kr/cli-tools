from __future__ import annotations

from datetime import datetime, timezone

import pytest

from legalize_cli.services.dates import parse_date_or_today
from legalize_cli.util.errors import InputValidationError


def test_default_date_uses_kst_boundary() -> None:
    assert parse_date_or_today(None, now=datetime(2026, 9, 20, 15, 0, tzinfo=timezone.utc)).isoformat() == "2026-09-21"


@pytest.mark.parametrize("raw", ["20260921", "2026-02-30", "2026-9-1", "2026-01-01T00:00:00Z"])
def test_invalid_dates_are_rejected(raw: str) -> None:
    with pytest.raises(InputValidationError):
        parse_date_or_today(raw)


def test_naive_clock_is_rejected() -> None:
    with pytest.raises(InputValidationError):
        parse_date_or_today(None, now=datetime(2026, 9, 21))
