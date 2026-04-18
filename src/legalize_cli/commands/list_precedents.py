"""``legalize precedents ...`` subcommand group."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ..precedents.enumerate import enumerate_precedents
from ..precedents.list import list_precedents
from ..util.cli_common import (
    build_global_opts,
    emit_json,
    handle_domain_error,
    make_client,
)
from ..util.errors import LegalizeError

precedents_app = typer.Typer(
    name="precedents",
    help="Operate on the Korean precedents mirror (legalize-kr/precedent-kr).",
    no_args_is_help=True,
)


@precedents_app.command("list")
def list_precedents_cmd(
    court: Optional[str] = typer.Option(None, "--court", help="Filter by 법원명."),
    type_: Optional[str] = typer.Option(
        None, "--type", help="Filter by 사건종류 (민사|형사|가사|...).",
    ),
    page: int = typer.Option(1, "--page", min=1),
    page_size: int = typer.Option(100, "--page-size", min=1, max=500),
    json_output: bool = typer.Option(False, "--json"),
    token: Optional[str] = typer.Option(None, "--token"),
    no_cache: bool = typer.Option(False, "--no-cache"),
    cache_dir: Optional[Path] = typer.Option(None, "--cache-dir"),
    offline: bool = typer.Option(False, "--offline"),
) -> None:
    """List precedents from the precedent-kr tree."""
    opts = build_global_opts(token, no_cache, cache_dir, offline, json_output)
    client, cache = make_client(opts)

    try:
        entries = enumerate_precedents(client, cache)
        total, window, next_page = list_precedents(
            entries, court=court, type_=type_, page=page, page_size=page_size
        )
    except LegalizeError as exc:
        raise handle_domain_error(exc) from exc
    finally:
        client.close()

    if json_output:
        emit_json(
            {
                "total": total,
                "page": page,
                "page_size": page_size,
                "items": [e.model_dump() for e in window],
                "next_page": next_page,
            },
            kind="precedents.list",
        )
        return

    if not window:
        typer.echo(f"(no precedents match; total={total})")
        return

    truncate_at = 50
    for entry in window[:truncate_at]:
        typer.echo(f"{entry.법원명:<12}  {entry.사건종류:<6}  {entry.사건번호}")
    if len(window) > truncate_at:
        typer.echo(f"... +{len(window) - truncate_at} more (page_size={page_size})")
    typer.echo(f"(page {page}; total={total})")


__all__ = ["precedents_app", "list_precedents_cmd"]
