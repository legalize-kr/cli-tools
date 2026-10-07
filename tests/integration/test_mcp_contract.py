from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone

import anyio
import pytest
from mcp import Client

from legalize_cli.github.commits import CommitInfo
from legalize_cli.laws.asof import ResolvedAsOf
from legalize_cli.laws.frontmatter import parse as parse_frontmatter
from legalize_cli.laws.lookup import ResolvedLawFile
from legalize_cli.mcp.server import build_server
from legalize_cli.services import laws as law_service
from legalize_cli.services.context import ServiceContext

SHA_OLD = "a" * 40
SHA_NEW = "b" * 40


class DummyClient:
    token_source = "none"

    def get_json(self, path, **kwargs):
        return []

    def close(self) -> None:
        pass


def _resolved(sha: str, promulgation: str, enforcement: str, content: str) -> ResolvedLawFile:
    raw = (
        f"---\n제목: 예시법\n법령ID: '000100'\n법령MST: 101\n"
        f"공포일자: {promulgation}\n시행일자: {enforcement}\n"
        "출처: https://example.test/law\n---\n"
        f"##### 제1조 (목적)\n\n{content}\n"
    ).encode()
    fm, _ = parse_frontmatter(raw.decode())
    stamp = datetime.fromisoformat(promulgation + "T12:00:00+09:00")
    commit = CommitInfo(sha=sha, author_date=stamp, committer_date=stamp, message="")
    return ResolvedLawFile(
        resolution=ResolvedAsOf(commit=commit, frontmatter=fm, semantic_date=fm.promulgation_date),
        raw=raw,
    )


def test_law_article_diff_and_error_over_actual_client(monkeypatch: pytest.MonkeyPatch) -> None:
    old = _resolved(SHA_OLD, "2025-01-01", "2025-01-01", "이전 규정")
    new = _resolved(SHA_NEW, "2026-03-01", "2026-07-01", "새 규정")

    def resolve(_client, _cache, _path, target, semantic):
        if target < date(2025, 1, 1):
            return None
        if semantic == "시행일자" and target < date(2026, 7, 1):
            return old
        return old if target < date(2026, 3, 1) else new

    monkeypatch.setattr(law_service, "resolve_law_file_as_of", resolve)

    async def run() -> None:
        async with Client(build_server(lambda: ServiceContext(DummyClient(), None))) as client:
            article = await client.call_tool("laws_article", {
                "law_name": "예시법", "article_no": "1", "date": "2026-04-01",
            })
            assert not article.is_error
            data = article.structured_content
            assert json.loads(article.content[0].text) == data
            assert data["version"]["enforcement_date"] == "2026-07-01"
            assert data["source"]["ref"] == SHA_NEW
            assert "NOT_YET_EFFECTIVE" in [warning["code"] for warning in data["warnings"]]

            effective = await client.call_tool("laws_article", {
                "law_name": "예시법", "article_no": "1", "date": "2026-04-01",
                "semantic": "시행일자",
            })
            assert effective.structured_content["source"]["ref"] == SHA_OLD

            difference = await client.call_tool("laws_diff", {
                "law_name": "예시법", "date_a": "2025-01-01", "date_b": "2026-04-01",
            })
            assert not difference.is_error
            assert difference.structured_content["a"]["source"]["ref"] == SHA_OLD
            assert difference.structured_content["b"]["source"]["ref"] == SHA_NEW
            assert difference.structured_content["changes"][0]["status"] == "modified"

            missing = await client.call_tool("laws_article", {
                "law_name": "예시법", "article_no": "99", "date": "2026-04-01",
            })
            assert missing.is_error
            assert json.loads(missing.content[0].text)["error"]["code"] == "ARTICLE_NOT_FOUND"
            reversed_dates = await client.call_tool("laws_diff", {
                "law_name": "예시법", "date_a": "2026-04-01", "date_b": "2025-01-01",
            })
            assert reversed_dates.is_error
            assert json.loads(reversed_dates.content[0].text)["error"]["code"] == "INVALID_INPUT"
    anyio.run(run)
