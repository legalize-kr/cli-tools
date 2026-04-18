"""``legalize laws diff <a> <b>`` — same-law time diff or cross-statute diff."""

from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import typer

from ..github.contents import get_file_raw
from ..laws.articles import parse_articles
from ..laws.asof import resolve_as_of
from ..laws.diff import diff_laws
from ..laws.frontmatter import parse as parse_frontmatter
from ..laws.revisions import get_revisions
from ..util.cli_common import (
    build_global_opts,
    emit_json,
    handle_domain_error,
    make_client,
)
from ..util.errors import LegalizeError, NotFoundError
from .list_laws import laws_app


@laws_app.command("diff")
def diff_cmd(
    law_a: str = typer.Argument(..., metavar="<law-a>"),
    law_b: str = typer.Argument(..., metavar="<law-b>"),
    date_a: Optional[str] = typer.Option(None, "--date-a"),
    date_b: Optional[str] = typer.Option(None, "--date-b"),
    category_a: str = typer.Option("법률", "--category-a"),
    category_b: str = typer.Option("법률", "--category-b"),
    mode: str = typer.Option("article", "--mode"),
    show_unchanged: bool = typer.Option(False, "--show-unchanged"),
    suppress_cross_warning: bool = typer.Option(
        False, "--suppress-cross-statute-warning",
    ),
    json_output: bool = typer.Option(False, "--json"),
    token: Optional[str] = typer.Option(None, "--token"),
    no_cache: bool = typer.Option(False, "--no-cache"),
    cache_dir: Optional[Path] = typer.Option(None, "--cache-dir"),
    offline: bool = typer.Option(False, "--offline"),
) -> None:
    """Diff two law revisions — primarily same-law time diff."""
    if mode not in ("unified", "side-by-side", "article"):
        raise typer.BadParameter("--mode must be unified|side-by-side|article")

    if law_a != law_b and not suppress_cross_warning:
        sys.stderr.write(
            "[warn] cross-statute diff is structural only; "
            "semantic comparison is not implied\n"
        )

    target_a = _parse_date(date_a)
    target_b = _parse_date(date_b)

    opts = build_global_opts(token, no_cache, cache_dir, offline, json_output)
    client, cache = make_client(opts)

    try:
        path_a = f"kr/{law_a}/{category_a}.md"
        path_b = f"kr/{law_b}/{category_b}.md"

        resolved_a, body_a = _resolve_body(client, cache, path_a, target_a)
        resolved_b, body_b = _resolve_body(client, cache, path_b, target_b)
    except LegalizeError as exc:
        raise handle_domain_error(exc) from exc
    finally:
        client.close()

    _fm_a, md_body_a = parse_frontmatter(body_a.decode("utf-8", errors="replace"))
    _fm_b, md_body_b = parse_frontmatter(body_b.decode("utf-8", errors="replace"))
    articles_a = parse_articles(md_body_a) if mode == "article" else []
    articles_b = parse_articles(md_body_b) if mode == "article" else []

    result = diff_laws(
        articles_a,
        articles_b,
        a_body=md_body_a,
        b_body=md_body_b,
        mode=mode,  # type: ignore[arg-type]
        show_unchanged=show_unchanged,
    )

    if json_output:
        emit_json(
            {
                "a": {
                    "law": law_a,
                    "category": category_a,
                    "date": target_a.isoformat(),
                    "resolved_commit_date": resolved_a.isoformat(),
                },
                "b": {
                    "law": law_b,
                    "category": category_b,
                    "date": target_b.isoformat(),
                    "resolved_commit_date": resolved_b.isoformat(),
                },
                "mode": mode,
                "changes": [
                    _change_to_dict(c) for c in result.changes
                ] if mode == "article" else [],
                "text": result.text if mode != "article" else None,
            },
            kind="laws.diff",
        )
        return

    if mode != "article":
        typer.echo(result.text or "")
        return

    for change in result.changes:
        an = change.article_no
        label = f"제{an.jo}조" + (f"의{an.ui}" if an.ui else "")
        extra = ""
        if change.status == "renamed" and change.from_article_no is not None:
            fa = change.from_article_no
            prev = f"제{fa.jo}조" + (f"의{fa.ui}" if fa.ui else "")
            extra = f"  <- {prev}  (ratio={change.similarity})"
        typer.echo(f"[{change.status:<14}] {label}{extra}")
        if change.hunk:
            typer.echo(change.hunk)


# ---- helpers ----------------------------------------------------------


def _resolve_body(client, cache, path: str, target: date):
    commits = get_revisions(client, cache, path)
    if not commits:
        raise NotFoundError(f"no revisions for {path}")
    chosen = resolve_as_of(commits, target)
    if chosen is None:
        raise NotFoundError(f"no commit at or before {target.isoformat()} for {path}")
    body = get_file_raw(client, "legalize-kr", "legalize-kr", path, ref=chosen.sha)
    return chosen.author_date.date(), body


def _parse_date(raw: Optional[str]) -> date:
    if raw is None:
        return datetime.now(timezone.utc).astimezone().date()
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise typer.BadParameter(f"--date must be YYYY-MM-DD ({exc})") from exc


def _change_to_dict(c) -> dict:
    payload: dict = {
        "article_no": c.article_no.model_dump(by_alias=True),
        "status": c.status,
    }
    if c.hunk is not None:
        payload["hunk"] = c.hunk
    if c.from_article_no is not None:
        payload["from"] = c.from_article_no.model_dump(by_alias=True)
    if c.similarity is not None:
        payload["similarity"] = c.similarity
    return payload


__all__ = ["diff_cmd"]
