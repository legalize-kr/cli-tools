"""``legalize laws article <law> <article-no>`` — point-in-time article extract."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional, cast

import typer

from ..contracts.requests import LawArticleRequest
from ..laws.asof import Semantic
from ..laws.model import ArticleNo
from ..services.context import ServiceContext
from ..services.dates import parse_date_or_today
from ..services.laws import load_law_article
from ..util.article_parse import parse_article_query
from ..util.cli_common import (
    build_global_opts,
    emit_json,
    handle_domain_error,
    make_client,
)
from ..util.errors import LegalizeError
from .list_laws import laws_app


@laws_app.command("article")
def article_cmd(
    law_name: str = typer.Argument(..., metavar="<law-name>"),
    article_no: str = typer.Argument(..., metavar="<article-no>"),
    category: str = typer.Option("법률", "--category"),
    the_date: Optional[str] = typer.Option(None, "--date"),
    semantic: str = typer.Option("공포일자", "--semantic"),
    json_output: bool = typer.Option(False, "--json"),
    token: Optional[str] = typer.Option(None, "--token"),
    no_cache: bool = typer.Option(False, "--no-cache"),
    cache_dir: Optional[Path] = typer.Option(None, "--cache-dir"),
    offline: bool = typer.Option(False, "--offline"),
) -> None:
    """Slice a single article out of a law at a point in time."""
    if semantic not in ("공포일자", "시행일자"):
        raise typer.BadParameter("--semantic must be 공포일자 or 시행일자")

    target = _parse_date(the_date)
    query: ArticleNo = parse_article_query(article_no)

    opts = build_global_opts(token, no_cache, cache_dir, offline, json_output)
    client, cache = make_client(opts)

    try:
        result, fm = load_law_article(
            ServiceContext(client, cache),
            LawArticleRequest(
                law_name=law_name, article_no=article_no, category=category,
                date=target.isoformat(), semantic=cast(Semantic, semantic),
            ),
        )
    except LegalizeError as exc:
        raise handle_domain_error(exc) from exc
    finally:
        client.close()

    if json_output:
        payload = {
            "law": law_name,
            "category": category,
            "semantic": semantic,
            "requested_date": target.isoformat(),
            "resolved_version_date": result.version.resolved_version_date.isoformat(),
            "resolved_commit_date": result.version.resolved_commit_date.isoformat(),
            "resolved_commit_sha": result.source.ref,
            "공포일자": result.version.promulgation_date,
            "시행일자": result.version.enforcement_date,
            "출처": fm.source,
            "법령ID": result.version.law_id,
            "법령MST": result.version.law_mst,
            "file_effective_date_only": True,
            "article_no": result.article_no.model_dump(by_alias=True),
            "status": result.status,
            "annotations": result.annotations,
            "path": result.source.path,
            "content": result.content,
            "parent_structure": result.parent_structure,
        }
        warning = _file_scope_warning(semantic, target, result.version.enforcement_date)
        if warning is not None:
            payload["warning"] = warning
        emit_json(payload, kind="laws.article")
        return

    warning = _file_scope_warning(semantic, target, result.version.enforcement_date)
    if warning is not None:
        typer.echo(f"warning: {warning}", err=True)
    if result.parent_structure:
        typer.echo(" > ".join(result.parent_structure))
    typer.echo(result.content)


# ---- internals --------------------------------------------------------


def _parse_date(raw: Optional[str]) -> date:
    try:
        return parse_date_or_today(raw)
    except LegalizeError as exc:
        raise typer.BadParameter(f"--date must be YYYY-MM-DD ({exc})") from exc


def _file_scope_warning(
    semantic: str, target: date, enforcement_date: Optional[date]
) -> Optional[str]:
    if semantic == "공포일자" and enforcement_date is not None and target < enforcement_date:
        return (
            "선택한 공포일자 버전은 기준일에 아직 시행 전입니다. "
            "시행 중인 파일 버전은 --semantic 시행일자로 조회하세요."
        )
    return None


__all__ = ["article_cmd"]
