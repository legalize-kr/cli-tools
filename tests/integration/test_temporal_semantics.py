"""CLI coverage for file-level 공포일자 and 시행일자 selection."""

from __future__ import annotations

import json
from datetime import date, datetime

from typer.testing import CliRunner

from legalize_cli.__main__ import app
from legalize_cli.commands import article, asof_cmd, diff
from legalize_cli.github.commits import CommitInfo
from legalize_cli.laws.asof import ResolvedAsOf
from legalize_cli.laws.frontmatter import parse as parse_frontmatter
from legalize_cli.laws.list import LawEntry
from legalize_cli.laws.lookup import ResolvedLawFile
from legalize_cli.services import laws as law_service


class _Client:
    token_source = "none"

    def get_json(self, path, **kwargs):
        return []

    def close(self) -> None:
        pass


def _resolved(
    *,
    sha: str,
    promulgation: str,
    enforcement: str,
    status: str = "시행",
    content: str,
    selected_date: str | None = None,
) -> ResolvedLawFile:
    raw = (
        f"---\n제목: 예시법\n법령MST: 100\n법령ID: '000100'\n"
        f"공포일자: {promulgation}\n시행일자: {enforcement}\n상태: {status}\n"
        "출처: https://example.test/law\n---\n"
        f"##### 제1조 (목적)\n\n{content}\n"
    ).encode()
    frontmatter, _ = parse_frontmatter(raw.decode())
    stamp = datetime.fromisoformat(f"{promulgation}T12:00:00+00:00")
    commit = CommitInfo(sha=sha, author_date=stamp, committer_date=stamp, message="")
    return ResolvedLawFile(
        resolution=ResolvedAsOf(
            commit=commit,
            frontmatter=frontmatter,
            semantic_date=date.fromisoformat(selected_date or enforcement),
        ),
        raw=raw,
    )


def test_get_and_article_cli_apply_semantic_and_warn_before_file_effective_date(
    monkeypatch,
) -> None:
    announced = _resolved(
        sha="b" * 40, promulgation="2026-03-01", enforcement="2026-07-01", content="새 규정", selected_date="2026-03-01"
    )
    effective = _resolved(
        sha="a" * 40, promulgation="2025-01-01", enforcement="2025-01-01", content="이전 규정"
    )
    selections = {"공포일자": announced, "시행일자": effective}

    monkeypatch.setattr(asof_cmd, "make_client", lambda *_args: (_Client(), None))
    monkeypatch.setattr(article, "make_client", lambda *_args: (_Client(), None))
    monkeypatch.setattr(
        law_service,
        "resolve_law_file_as_of",
        lambda _client, _cache, _path, _target, semantic: selections[semantic],
    )

    runner = CliRunner()
    get_result = runner.invoke(
        app,
        ["laws", "get", "예시법", "--date", "2026-04-01", "--semantic", "공포일자", "--json"],
    )
    article_result = runner.invoke(
        app,
        ["laws", "article", "예시법", "1", "--date", "2026-04-01", "--semantic", "시행일자", "--json"],
    )

    assert get_result.exit_code == 0, get_result.output
    assert article_result.exit_code == 0, article_result.output
    get_payload = json.loads(get_result.output)
    article_payload = json.loads(article_result.output)
    assert get_payload["resolved_version_date"] == "2026-03-01"
    assert get_payload["warning"]
    assert article_payload["resolved_version_date"] == "2025-01-01"
    assert article_payload["공포일자"] == "2025-01-01"
    assert "이전 규정" in article_payload["content"]


def test_as_of_uses_selected_historical_status_not_head_status(monkeypatch) -> None:
    active = _resolved(
        sha="active", promulgation="2025-01-01", enforcement="2025-01-01", content="시행"
    )
    repealed = _resolved(
        sha="repealed", promulgation="2025-01-01", enforcement="2025-01-01", status="폐지", content="폐지"
    )
    laws = [
        LawEntry(name="시행법", path="kr/시행법/법률.md", category="법률"),
        LawEntry(name="폐지법", path="kr/폐지법/법률.md", category="법률"),
    ]

    monkeypatch.setattr(asof_cmd, "make_client", lambda *_args: (_Client(), None))
    monkeypatch.setattr(asof_cmd, "enumerate_laws", lambda *_args: laws)
    monkeypatch.setattr(
        asof_cmd,
        "resolve_law_file_as_of",
        lambda _client, _cache, path, _target, _semantic: active if "시행법" in path else repealed,
    )

    result = CliRunner().invoke(
        app,
        ["laws", "as-of", "--date", "2026-04-01", "--semantic", "시행일자", "--json", "--limit", "2"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["total"] == 1
    assert payload["items"][0]["name"] == "시행법"


def test_diff_cli_passes_the_same_semantic_to_both_dates(monkeypatch) -> None:
    old = _resolved(
        sha="old", promulgation="2025-01-01", enforcement="2025-01-01", content="이전 규정"
    )
    new = _resolved(
        sha="new", promulgation="2026-03-01", enforcement="2026-07-01", content="새 규정", selected_date="2026-07-01"
    )
    calls: list[tuple[str, str]] = []

    monkeypatch.setattr(diff, "make_client", lambda *_args: (_Client(), None))

    def resolve(_client, _cache, _path, target, semantic):
        calls.append((target.isoformat(), semantic))
        return old if target == date(2026, 4, 1) else new

    monkeypatch.setattr(diff, "resolve_law_file_as_of", resolve)

    result = CliRunner().invoke(
        app,
        [
            "laws",
            "diff",
            "예시법",
            "예시법",
            "--date-a",
            "2026-04-01",
            "--date-b",
            "2026-08-01",
            "--semantic",
            "시행일자",
            "--mode",
            "unified",
            "--json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert calls == [("2026-04-01", "시행일자"), ("2026-08-01", "시행일자")]
    assert payload["a"]["resolved_version_date"] == "2025-01-01"
    assert payload["b"]["resolved_version_date"] == "2026-07-01"
