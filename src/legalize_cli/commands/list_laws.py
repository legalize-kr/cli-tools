"""``legalize laws ...`` subcommand group.

Step 6 lands ``list``. Later steps attach ``get``, ``as-of``, ``article``,
``diff`` to the same ``laws_app`` so the subtree layout is consistent.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ..laws.list import LAW_CATEGORIES, enumerate_laws, filter_and_paginate
from ..util.cli_common import (
    build_global_opts,
    emit_json,
    handle_domain_error,
    make_client,
)
from ..util.errors import LegalizeError

#: Shared ``laws`` subcommand group; other command modules import and extend it.
laws_app = typer.Typer(
    name="laws",
    help="Operate on the Korean laws mirror (legalize-kr/legalize-kr).",
    no_args_is_help=True,
)


@laws_app.command("list")
def list_laws_cmd(
    category: str = typer.Option(
        "all",
        "--category",
        help="Filter by 법령구분 (법률|시행령|시행규칙|대통령령|all).",
    ),
    page: int = typer.Option(1, "--page", min=1, help="1-indexed page number."),
    page_size: int = typer.Option(
        100,
        "--page-size",
        min=1,
        max=500,
        help="Items per page (max 500).",
    ),
    json_output: bool = typer.Option(False, "--json", help="Emit JSON to stdout."),
    token: Optional[str] = typer.Option(None, "--token", help="GitHub token override."),
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass disk cache."),
    cache_dir: Optional[Path] = typer.Option(
        None, "--cache-dir", help="Override cache dir.",
    ),
    offline: bool = typer.Option(False, "--offline", help="Refuse any network call."),
) -> None:
    """List mirrored Korean laws."""
    if category not in ("all", *LAW_CATEGORIES):
        raise typer.BadParameter(
            f"--category must be one of {', '.join(('all', *LAW_CATEGORIES))}"
        )

    opts = build_global_opts(token, no_cache, cache_dir, offline, json_output)
    client, cache = make_client(opts)

    try:
        all_laws = enumerate_laws(client, cache)
        total, window, next_page = filter_and_paginate(
            all_laws, category=category, page=page, page_size=page_size
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
            kind="laws.list",
        )
        return

    if not window:
        typer.echo(f"(no laws match; total={total})")
        return

    typer.echo(f"{'category':<12}  {'name':<28}  path")
    typer.echo(f"{'-' * 12}  {'-' * 28}  {'-' * 40}")
    truncate_at = 50
    for entry in window[:truncate_at]:
        typer.echo(f"{entry.category:<12}  {entry.name:<28}  {entry.path}")
    if len(window) > truncate_at:
        typer.echo(f"... +{len(window) - truncate_at} more (page_size={page_size})")
    typer.echo(f"(page {page}/{-(-total // page_size)}; total={total})")


__all__ = ["laws_app", "list_laws_cmd"]
