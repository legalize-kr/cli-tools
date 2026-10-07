from __future__ import annotations

import json

import pytest

from legalize_cli.contracts.common import LawVersion, SourceReference, Warning
from legalize_cli.contracts.laws import LawResult
from legalize_cli.laws.model import Frontmatter
from legalize_cli.mcp.results import MAX_CANONICAL_BYTES, render_result
from legalize_cli.util.errors import ResponseTooLargeError


def _law(body: str) -> LawResult:
    return LawResult(
        law="예시법", category="법률",
        version=LawVersion(
            semantic="공포일자", requested_date="2026-09-21",
            resolved_version_date="2026-09-21", resolved_commit_date="2026-09-21",
        ),
        source=SourceReference(
            dataset="laws", repository="legalize-kr/legalize-kr",
            path="kr/예시법/법률.md", ref="a" * 40, ref_type="commit",
            github_url="https://github.com/legalize-kr/legalize-kr/blob/main/kr/x.md",
        ),
        frontmatter=Frontmatter(), body=body,
        warnings=[Warning(code="FILE_LEVEL_EFFECTIVE_DATE_ONLY", message="파일 단위", dataset="laws")],
    )


def test_unicode_and_escaping_are_measured_as_wire_bytes() -> None:
    result = render_result(_law('한글 "인용"\n'))
    assert json.loads(result.content[0].text) == result.structured_content
    assert len(result.content[0].text.encode("utf-8")) > len(result.content[0].text)


def test_large_body_is_error_not_truncated() -> None:
    with pytest.raises(ResponseTooLargeError) as raised:
        render_result(_law("한" * MAX_CANONICAL_BYTES))
    assert raised.value.source["path"] == "kr/예시법/법률.md"
