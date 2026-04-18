"""MCP server exposing legalize-kr tools for LLM/agent consumption.

Run via:
    legalize mcp serve          # stdio (Claude Desktop, Cursor, etc.)
    legalize-mcp                # direct entry-point shortcut
    python -m legalize_cli.mcp_server
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Optional

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "MCP support requires the 'mcp' extra: pip install 'legalize-cli[mcp]'"
    ) from exc

from .auth import resolve_token
from .cache import DiskCache
from .config import DEFAULT_CACHE_DIR, OWNER, PRECEDENTS_REPO
from .github.contents import get_file_raw
from .http import GitHubClient
from .laws.articles import parse_articles
from .laws.asof import resolve_as_of
from .laws.frontmatter import parse as parse_frontmatter
from .laws.list import enumerate_laws, filter_and_paginate
from .laws.revisions import get_revisions
from .precedents.enumerate import enumerate_precedents
from .precedents.fetch import fetch_by_id_or_path
from .precedents.list import list_precedents
from .search.code_search import code_search_items
from .search.strategies import select_strategy
from .search.tree_filter import tree_filter_items
from .util.article_parse import parse_article_query
from .util.errors import LegalizeError

mcp = FastMCP(
    "legalize-kr",
    instructions=(
        "한국 법령·판례 검색. legalize-kr GitHub 미러에서 "
        "법률 조문, 개정 이력, 판례를 직접 조회합니다."
    ),
)


def _make_client() -> tuple[GitHubClient, DiskCache]:
    token, source = resolve_token()
    cache = DiskCache(DEFAULT_CACHE_DIR)
    return GitHubClient(token=token, token_source=source, cache=cache), cache


def _date_or_today(raw: Optional[str]) -> date:
    if raw is None:
        return datetime.now(timezone.utc).astimezone().date()
    return date.fromisoformat(raw)


@mcp.tool()
def laws_list(category: str = "all", page: int = 1, page_size: int = 50) -> str:
    """미러된 한국 법령 목록을 조회합니다.

    Args:
        category: 법령 종류 (법률|시행령|시행규칙|대통령령|all). 기본값: all
        page: 페이지 번호. 기본값: 1
        page_size: 페이지당 항목 수. 기본값: 50
    """
    client, cache = _make_client()
    try:
        laws = enumerate_laws(client, cache)
        cat = category if category != "all" else None
        total, window, next_page = filter_and_paginate(
            laws, category=cat, page=page, page_size=page_size
        )
        return json.dumps(
            {
                "schema_version": "1.0",
                "kind": "laws.list",
                "total": total,
                "page": page,
                "next_page": next_page,
                "items": [
                    {"name": e.name, "path": e.path, "category": e.category}
                    for e in window
                ],
            },
            ensure_ascii=False,
        )
    except LegalizeError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.close()


@mcp.tool()
def laws_get(
    law_name: str,
    category: str = "법률",
    date: Optional[str] = None,
) -> str:
    """법령 전문(全文)을 마크다운으로 조회합니다.

    Args:
        law_name: 법령명 (예: 민법, 형법, 근로기준법)
        category: 법령 종류 (법률|시행령|시행규칙|대통령령). 기본값: 법률
        date: 기준 날짜 YYYY-MM-DD. 생략 시 오늘 기준 최신본
    """
    target = _date_or_today(date)
    path = f"kr/{law_name}/{category}.md"

    client, cache = _make_client()
    try:
        commits = get_revisions(client, cache, path)
        if not commits:
            return json.dumps(
                {"error": f"{path} 에 해당하는 개정 이력이 없습니다."},
                ensure_ascii=False,
            )
        chosen = resolve_as_of(commits, target)
        if chosen is None:
            return json.dumps(
                {"error": f"{target.isoformat()} 이전 커밋을 찾을 수 없습니다: {path}"},
                ensure_ascii=False,
            )
        body = get_file_raw(client, OWNER, "legalize-kr", path, ref=chosen.sha)
    except LegalizeError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.close()

    text = body.decode("utf-8", errors="replace")
    fm, md_body = parse_frontmatter(text)
    return json.dumps(
        {
            "schema_version": "1.0",
            "kind": "laws.get",
            "law": law_name,
            "category": category,
            "requested_date": target.isoformat(),
            "resolved_commit_date": chosen.author_date.date().isoformat(),
            "path": path,
            "frontmatter": fm.model_dump(by_alias=True, exclude_none=True),
            "body": md_body,
        },
        ensure_ascii=False,
    )


@mcp.tool()
def laws_article(
    law_name: str,
    article_no: str,
    category: str = "법률",
    date: Optional[str] = None,
) -> str:
    """법령의 특정 조문을 조회합니다.

    Args:
        law_name: 법령명 (예: 민법)
        article_no: 조문 번호 (제839조, 839, 839조의2, 839-2 등 형식 모두 허용)
        category: 법령 종류 (법률|시행령|시행규칙|대통령령). 기본값: 법률
        date: 기준 날짜 YYYY-MM-DD. 생략 시 오늘 기준 최신본
    """
    try:
        query = parse_article_query(article_no)
    except Exception as e:
        return json.dumps({"error": f"조문 번호 파싱 실패: {e}"}, ensure_ascii=False)

    target = _date_or_today(date)
    path = f"kr/{law_name}/{category}.md"

    client, cache = _make_client()
    try:
        commits = get_revisions(client, cache, path)
        if not commits:
            return json.dumps(
                {"error": f"{path} 에 해당하는 개정 이력이 없습니다."},
                ensure_ascii=False,
            )
        chosen = resolve_as_of(commits, target)
        if chosen is None:
            return json.dumps(
                {"error": f"{target.isoformat()} 이전 커밋을 찾을 수 없습니다: {path}"},
                ensure_ascii=False,
            )
        body = get_file_raw(client, OWNER, "legalize-kr", path, ref=chosen.sha)
    except LegalizeError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.close()

    text = body.decode("utf-8", errors="replace")
    _fm, md_body = parse_frontmatter(text)
    articles = parse_articles(md_body)

    match = next(
        (
            a
            for a in articles
            if a.article_no.jo == query.jo
            and (a.article_no.ui or None) == (query.ui or None)
        ),
        None,
    )

    if match is None:
        return json.dumps(
            {
                "error": (
                    f"{law_name}/{category}에서 {article_no} 조문을 찾을 수 없습니다 "
                    f"(기준일: {target.isoformat()})"
                )
            },
            ensure_ascii=False,
        )

    return json.dumps(
        {
            "schema_version": "1.0",
            "kind": "laws.article",
            "law": law_name,
            "category": category,
            "article_no": match.article_no.model_dump(by_alias=True),
            "status": match.status,
            "annotations": match.annotations,
            "resolved_commit_date": chosen.author_date.date().isoformat(),
            "path": path,
            "content": match.content,
            "parent_structure": match.parent_structure,
        },
        ensure_ascii=False,
    )


@mcp.tool()
def search(
    keyword: str,
    scope: str = "all",
    limit: int = 30,
    strategy: str = "auto",
) -> str:
    """법령 및 판례에서 키워드를 검색합니다.

    Args:
        keyword: 검색 키워드 (예: 부동산 점유취득시효)
        scope: 검색 대상 (laws|precedents|all). 기본값: all
        limit: 최대 결과 수. 기본값: 30
        strategy: 검색 전략 (auto|code|tree|metadata). 기본값: auto.
            code는 GITHUB_TOKEN 필수. auto는 토큰 유무에 따라 자동 선택.
    """
    if scope not in ("laws", "precedents", "all"):
        return json.dumps(
            {"error": "scope는 laws|precedents|all 중 하나여야 합니다."},
            ensure_ascii=False,
        )

    client, cache = _make_client()
    items: list = []
    warnings: list = []
    chosen = strategy

    try:
        chosen = select_strategy(
            token_present=client.token_source != "none",
            scope=scope,  # type: ignore[arg-type]
            user_choice=strategy,
        )

        if scope in ("laws", "all"):
            if chosen == "code" and client.token_source != "none":
                try:
                    items.extend(
                        code_search_items(
                            client,
                            keyword,
                            repo=f"{OWNER}/legalize-kr",
                            source="laws",
                        )
                    )
                except LegalizeError:
                    warnings.append("code-search 실패, tree 전략으로 전환합니다.")
                    items.extend(
                        tree_filter_items(client, cache, keyword, source="laws")
                    )
            else:
                if client.token_source == "none":
                    warnings.append("GITHUB_TOKEN 없음 — tree 전략을 사용합니다.")
                items.extend(
                    tree_filter_items(client, cache, keyword, source="laws")
                )

        if scope in ("precedents", "all"):
            if chosen == "code" and client.token_source != "none":
                items.extend(
                    code_search_items(
                        client,
                        keyword,
                        repo=f"{OWNER}/{PRECEDENTS_REPO}",
                        source="precedents",
                    )
                )
            else:
                items.extend(
                    tree_filter_items(
                        client, cache, keyword,
                        repo=PRECEDENTS_REPO,
                        source="precedents",
                    )
                )

        items = items[:limit]
    except LegalizeError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.close()

    return json.dumps(
        {
            "schema_version": "1.0",
            "kind": "search.result",
            "query": keyword,
            "strategy_used": chosen,
            "token_used": client.token_source != "none",
            "items": items,
            "warnings": warnings,
        },
        ensure_ascii=False,
    )


@mcp.tool()
def precedents_list(
    court: Optional[str] = None,
    type_: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> str:
    """판례 목록을 조회합니다.

    Args:
        court: 법원 필터 (대법원|하급심). 생략 시 전체
        type_: 사건 종류 필터 (민사|형사|가사|행정|특허|...). 생략 시 전체
        page: 페이지 번호. 기본값: 1
        page_size: 페이지당 항목 수. 기본값: 50
    """
    client, cache = _make_client()
    try:
        entries = enumerate_precedents(client, cache)
        total, window, next_page = list_precedents(
            entries, court=court, type_=type_, page=page, page_size=page_size
        )
    except LegalizeError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.close()

    return json.dumps(
        {
            "schema_version": "1.0",
            "kind": "precedents.list",
            "total": total,
            "page": page,
            "next_page": next_page,
            "items": [e.model_dump(by_alias=True) for e in window],
        },
        ensure_ascii=False,
        default=str,
    )


@mcp.tool()
def precedents_get(identifier: str) -> str:
    """판례 전문을 조회합니다.

    Args:
        identifier: 사건번호 (예: 2022다12345), 판례일련번호, 또는 저장소 상대 경로
    """
    client, cache = _make_client()
    try:
        path, body = fetch_by_id_or_path(client, cache, identifier)
    except LegalizeError as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)
    finally:
        client.close()

    text = body.decode("utf-8", errors="replace")
    return json.dumps(
        {
            "schema_version": "1.0",
            "kind": "precedents.get",
            "identifier": identifier,
            "path": path,
            "body": text,
        },
        ensure_ascii=False,
    )


def main() -> None:  # pragma: no cover
    mcp.run()


if __name__ == "__main__":  # pragma: no cover
    main()
