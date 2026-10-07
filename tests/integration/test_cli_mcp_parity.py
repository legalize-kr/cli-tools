from __future__ import annotations

import json
from datetime import date, datetime

import anyio
from mcp import Client
from typer.testing import CliRunner

from legalize_cli.__main__ import app
from legalize_cli.commands import article, asof_cmd
from legalize_cli.github.commits import CommitInfo
from legalize_cli.laws.asof import ResolvedAsOf
from legalize_cli.laws.frontmatter import parse as parse_frontmatter
from legalize_cli.laws.lookup import ResolvedLawFile
from legalize_cli.mcp.server import build_server
from legalize_cli.services import laws as law_service
from legalize_cli.services.context import ServiceContext


class _Client:
    token_source = "none"

    def get_json(self, path, **kwargs):
        return []

    def close(self) -> None:
        pass


def test_cli_1_and_mcp_2_select_same_article(monkeypatch) -> None:
    raw = b"---\n"
    raw = (
        "---\n제목: 예시법\n법령ID: '000100'\n법령MST: 101\n"
        "공포일자: 2026-03-01\n시행일자: 2026-07-01\n"
        "출처: https://example.test/law\n---\n##### 제1조 (목적)\n\n새 규정\n"
    ).encode()
    fm, _ = parse_frontmatter(raw.decode())
    stamp = datetime.fromisoformat("2026-03-01T12:00:00+09:00")
    selected = ResolvedLawFile(
        resolution=ResolvedAsOf(
            commit=CommitInfo(sha="a" * 40, author_date=stamp, committer_date=stamp, message=""),
            frontmatter=fm, semantic_date=date(2026, 3, 1),
        ),
        raw=raw,
    )
    monkeypatch.setattr(law_service, "resolve_law_file_as_of", lambda *_args: selected)
    monkeypatch.setattr(article, "make_client", lambda *_args: (_Client(), None))
    monkeypatch.setattr(asof_cmd, "make_client", lambda *_args: (_Client(), None))

    cli = CliRunner().invoke(app, [
        "laws", "article", "예시법", "1", "--date", "2026-04-01", "--json",
    ])
    assert cli.exit_code == 0, cli.output
    cli_data = json.loads(cli.output)

    async def run() -> None:
        async with Client(build_server(lambda: ServiceContext(_Client(), None))) as client:
            result = await client.call_tool("laws_article", {
                "law_name": "예시법", "article_no": "1", "date": "2026-04-01",
            })
            assert not result.is_error
            mcp_data = result.structured_content
            assert cli_data["schema_version"] == "1.0"
            assert mcp_data["schema_version"] == "2.0"
            assert cli_data["content"] == mcp_data["content"]
            assert cli_data["resolved_version_date"] == mcp_data["version"]["resolved_version_date"]
            assert cli_data["resolved_commit_sha"] == mcp_data["source"]["ref"]
    anyio.run(run)
