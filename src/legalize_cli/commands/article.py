"""``legalize laws article <law> <article-no>`` — point-in-time article extract."""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import typer

from ..github.contents import get_file_raw
from ..laws.articles import parse_articles
from ..laws.asof import resolve_as_of
from ..laws.frontmatter import parse as parse_frontmatter
from ..laws.model import ArticleNo
from ..laws.revisions import get_revisions
from ..util.article_parse import parse_article_query
from ..util.cli_common import (
    build_global_opts,
    emit_json,
    handle_domain_error,
    make_client,
)
from ..util.errors import LegalizeError, NotFoundError
from .list_laws import laws_app


@laws_app.command("article")
def article_cmd(
    law_name: str = typer.Argument(..., metavar="<law-name>"),
    article_no: str = typer.Argument(..., metavar="<article-no>"),
    category: str = typer.Option("법률", "--category"),
    the_date: Optional[str] = typer.Option(None, "--date"),
    json_output: bool = typer.Option(False, "--json"),
    token: Optional[str] = typer.Option(None, "--token"),
    no_cache: bool = typer.Option(False, "--no-cache"),
    cache_dir: Optional[Path] = typer.Option(None, "--cache-dir"),
    offline: bool = typer.Option(False, "--offline"),
) -> None:
    """Slice a single article out of a law at a point in time."""
    query: ArticleNo = parse_article_query(article_no)
    target = _parse_date(the_date)
    path = f"kr/{law_name}/{category}.md"

    opts = build_global_opts(token, no_cache, cache_dir, offline, json_output)
    client, cache = make_client(opts)

    try:
        commits = get_revisions(client, cache, path)
        if not commits:
            raise NotFoundError(f"no revisions for {path}")
        chosen = resolve_as_of(commits, target)
        if chosen is None:
            raise NotFoundError(
                f"no commit at or before {target.isoformat()} for {path}"
            )
        body = get_file_raw(client, "legalize-kr", "legalize-kr", path, ref=chosen.sha)
    except LegalizeError as exc:
        raise handle_domain_error(exc) from exc
    finally:
        client.close()

    text = body.decode("utf-8", errors="replace")
    _fm, md_body = parse_frontmatter(text)
    articles = parse_articles(md_body)

    match = next(
        (
            a
            for a in articles
            if a.article_no.jo == query.jo and (a.article_no.ui or None) == (query.ui or None)
        ),
        None,
    )

    if match is None:
        raise handle_domain_error(
            NotFoundError(
                f"article {article_no} not found in {law_name}/{category} at {target.isoformat()}"
            )
        )

    if json_output:
        emit_json(
            {
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
            kind="laws.article",
        )
        return

    if match.parent_structure:
        typer.echo(" > ".join(match.parent_structure))
    typer.echo(match.content)


# ---- internals --------------------------------------------------------


def _parse_date(raw: Optional[str]) -> date:
    if raw is None:
        return datetime.now(timezone.utc).astimezone().date()
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise typer.BadParameter(f"--date must be YYYY-MM-DD ({exc})") from exc


__all__ = ["article_cmd"]
