from __future__ import annotations

import pytest
from pydantic import ValidationError

from legalize_cli.contracts.requests import LawDiffRequest, LawGetRequest, PrecedentGetRequest, SearchRequest


def test_request_models_are_strict_and_forbid_extra() -> None:
    with pytest.raises(ValidationError):
        SearchRequest.model_validate({"keyword": "민법", "limit": "30"})
    with pytest.raises(ValidationError):
        LawGetRequest.model_validate({"law_name": "민법", "date": "20260921"})
    with pytest.raises(ValidationError):
        LawGetRequest.model_validate({"law_name": "민법", "extra": 1})


def test_diff_dates_are_ordered_and_no_generic_date_field() -> None:
    schema = LawDiffRequest.model_json_schema()
    assert "date" not in schema["properties"]
    with pytest.raises(ValidationError):
        LawDiffRequest(law_name="민법", date_a="2026-09-22", date_b="2026-09-21")


@pytest.mark.parametrize("case", [
    {"model": LawGetRequest, "value": {"law_name": "민법\n"}},
    {"model": PrecedentGetRequest, "value": {"identifier": "민사/대법원/예시.md\n"}},
    {"model": SearchRequest, "value": {"keyword": "민법\t"}},
])
def test_trailing_control_characters_are_not_silently_trimmed(case: dict) -> None:
    with pytest.raises(ValidationError):
        case["model"].model_validate(case["value"])
