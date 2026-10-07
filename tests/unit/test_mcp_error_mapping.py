from __future__ import annotations

from legalize_cli.mcp.errors import error_result
from legalize_cli.util.errors import AmbiguousMatchError, ResponseTooLargeError


def test_ambiguous_candidates_are_capped() -> None:
    result = error_result(AmbiguousMatchError("secret input", [f"public/{i}.md" for i in range(20)]))
    assert result.error.code == "AMBIGUOUS_MATCH"
    assert len(result.error.candidates) == 10
    assert result.error.candidate_total == 20
    assert "secret" not in result.error.message


def test_response_too_large_keeps_only_safe_source() -> None:
    source = {
        "dataset": "laws", "repository": "legalize-kr/legalize-kr",
        "path": "kr/민법/법률.md", "ref": "a" * 40, "ref_type": "commit",
        "github_url": "https://github.com/legalize-kr/legalize-kr/blob/main/kr/x.md",
        "original_url": None,
    }
    result = error_result(ResponseTooLargeError("too large", source=source))
    assert result.error.code == "RESPONSE_TOO_LARGE"
    assert result.error.source.path == "kr/민법/법률.md"
