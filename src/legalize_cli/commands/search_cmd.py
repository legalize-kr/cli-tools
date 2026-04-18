"""``legalize search <keyword>`` — unified laws + precedents search."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import typer

from ..config import LAWS_REPO, OWNER, PRECEDENTS_REPO
from ..search.code_search import code_search_items
from ..search.strategies import select_strategy
from ..search.tree_filter import tree_filter_items
from ..util.cli_common import (
    build_global_opts,
    emit_json,
    handle_domain_error,
    make_client,
)
from ..util.errors import AuthError, LegalizeError


def register(app: typer.Typer) -> None:
    """Attach the ``search`` command to ``app``."""
    app.command("search", help="Keyword search over laws and precedents.")(search_cmd)


def search_cmd(
    keyword: str = typer.Argument(..., metavar="<keyword>"),
    scope: str = typer.Option("all", "--in"),
    category: Optional[str] = typer.Option(None, "--category"),
    limit: int = typer.Option(50, "--limit", min=1, max=500),
    strategy: str = typer.Option("auto", "--strategy"),
    heavy_content_scan: bool = typer.Option(False, "--heavy-content-scan"),
    yes_exhaust: bool = typer.Option(False, "--yes-exhaust-quota"),
    json_output: bool = typer.Option(False, "--json"),
    token: Optional[str] = typer.Option(None, "--token"),
    no_cache: bool = typer.Option(False, "--no-cache"),
    cache_dir: Optional[Path] = typer.Option(None, "--cache-dir"),
    offline: bool = typer.Option(False, "--offline"),
) -> None:
    """Search mirrored laws and/or precedents by keyword."""
    if scope not in ("laws", "precedents", "all"):
        raise typer.BadParameter("--in must be laws|precedents|all")
    if strategy not in ("auto", "code", "tree", "metadata"):
        raise typer.BadParameter("--strategy must be auto|code|tree|metadata")

    opts = build_global_opts(token, no_cache, cache_dir, offline, json_output)
    client, cache = make_client(opts)
    warnings: List[str] = []
    chosen = strategy

    try:
        chosen = select_strategy(
            token_present=client.token_source != "none",
            scope=scope,  # type: ignore[arg-type]
            user_choice=strategy,
        )

        items: List[dict] = []

        if scope in ("laws", "all"):
            items.extend(
                _laws_items(
                    client,
                    cache,
                    keyword,
                    chosen,
                    heavy_content_scan,
                    yes_exhaust,
                    warnings,
                )
            )
        if scope in ("precedents", "all"):
            items.extend(
                _precedents_items(client, cache, keyword, chosen, warnings)
            )

        items = items[:limit]
    except LegalizeError as exc:
        raise handle_domain_error(exc) from exc
    finally:
        client.close()

    if json_output:
        emit_json(
            {
                "query": keyword,
                "strategy_used": chosen,
                "token_used": client.token_source != "none",
                "items": items,
                "warnings": warnings,
            },
            kind="search.result",
        )
        return

    for item in items:
        typer.echo(f"[{item.get('source', '?')}] {item.get('match_type', '?'):<8}  {item['path']}")
    for warning in warnings:
        typer.echo(f"[warn] {warning}", err=True)


# ---- internals --------------------------------------------------------


def _laws_items(
    client,
    cache,
    keyword: str,
    chosen: str,
    heavy: bool,
    yes_exhaust: bool,
    warnings: List[str],
) -> List[dict]:
    if chosen == "code" and client.token_source != "none":
        try:
            return code_search_items(
                client, keyword, repo=f"{OWNER}/{LAWS_REPO}", source="laws"
            )
        except AuthError:
            warnings.append("code-search failed — falling back to tree")
    if client.token_source == "none":
        warnings.append("no GITHUB_TOKEN — code-search unavailable; using tree strategy")
    return tree_filter_items(
        client,
        cache,
        keyword,
        heavy_content_scan=heavy,
        yes_exhaust=yes_exhaust,
        source="laws",
    )


def _precedents_items(
    client,
    cache,
    keyword: str,
    chosen: str,
    warnings: List[str],
) -> List[dict]:
    if chosen == "code" and client.token_source != "none":
        try:
            return code_search_items(
                client, keyword, repo=f"{OWNER}/{PRECEDENTS_REPO}", source="precedents"
            )
        except AuthError:
            warnings.append("code-search failed for precedents — falling back to tree")
    return tree_filter_items(
        client,
        cache,
        keyword,
        repo=PRECEDENTS_REPO,
        source="precedents",
    )


__all__ = ["register", "search_cmd"]
