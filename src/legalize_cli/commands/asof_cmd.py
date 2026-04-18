"""``legalize laws as-of`` and ``legalize laws get`` subcommands.

Named with the ``_cmd`` suffix per plan §3 to avoid shadowing
:mod:`legalize_cli.laws.asof`.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path
from typing import List, Optional

import typer

from ..github.contents import get_file_raw
from ..laws.asof import candidates_for_semantic, resolve_as_of
from ..laws.frontmatter import parse as parse_frontmatter
from ..laws.list import enumerate_laws
from ..laws.revisions import get_revisions
from ..laws.status import filter_by_status
from ..util.cli_common import (
    build_global_opts,
    emit_json,
    handle_domain_error,
    make_client,
)
from ..util.errors import LegalizeError, NotFoundError
from .list_laws import laws_app

#: Limit above which a heavy scan without a token must be confirmed.
_DEFAULT_SCAN_LIMIT = 100


@laws_app.command("as-of")
def as_of_cmd(
    the_date: Optional[str] = typer.Option(
        None, "--date", help="ISO date (YYYY-MM-DD); default: today KST.",
    ),
    category: str = typer.Option("all", "--category"),
    include_repealed: bool = typer.Option(False, "--include-repealed"),
    semantic: str = typer.Option("공포일자", "--semantic"),
    limit: Optional[int] = typer.Option(None, "--limit"),
    yes_exhaust: bool = typer.Option(False, "--yes-exhaust-quota"),
    json_output: bool = typer.Option(False, "--json"),
    token: Optional[str] = typer.Option(None, "--token"),
    no_cache: bool = typer.Option(False, "--no-cache"),
    cache_dir: Optional[Path] = typer.Option(None, "--cache-dir"),
    offline: bool = typer.Option(False, "--offline"),
) -> None:
    """List laws current as of a given date."""
    if semantic not in ("공포일자", "시행일자"):
        raise typer.BadParameter("--semantic must be 공포일자 or 시행일자")

    target = _parse_date(the_date)
    opts = build_global_opts(token, no_cache, cache_dir, offline, json_output)
    client, cache = make_client(opts)

    results = []
    try:
        laws = enumerate_laws(client, cache)
        if category != "all":
            laws = [e for e in laws if e.category == category]

        if limit is not None:
            laws = laws[:limit]

        _preflight_budget(
            client,
            candidates=len(laws),
            yes_exhaust=yes_exhaust,
            token_present=bool(opts.token) or client.token_source != "none",
            default_limit=_DEFAULT_SCAN_LIMIT,
            limit=limit,
        )

        laws = filter_by_status(client, laws, include_repealed=include_repealed)

        for entry in laws:
            commits = get_revisions(client, cache, entry.path)
            chosen = resolve_as_of(commits, target, semantic=semantic)
            if chosen is None:
                continue
            results.append(
                {
                    "name": entry.name,
                    "category": entry.category,
                    "path": entry.path,
                    "resolved_commit_date": chosen.author_date.date().isoformat(),
                }
            )
    except LegalizeError as exc:
        raise handle_domain_error(exc) from exc
    finally:
        client.close()

    if json_output:
        emit_json(
            {
                "requested_date": target.isoformat(),
                "semantic": semantic,
                "items": results,
                "total": len(results),
            },
            kind="laws.asof",
        )
        return

    for row in results:
        typer.echo(f"{row['category']:<12}  {row['name']:<28}  {row['resolved_commit_date']}")
    typer.echo(f"(total={len(results)} as-of {target.isoformat()} ({semantic}))")


@laws_app.command("get")
def get_law_cmd(
    law_name: str = typer.Argument(..., metavar="<law-name>"),
    category: str = typer.Option("법률", "--category"),
    the_date: Optional[str] = typer.Option(None, "--date"),
    semantic: str = typer.Option("공포일자", "--semantic"),
    json_output: bool = typer.Option(False, "--json"),
    token: Optional[str] = typer.Option(None, "--token"),
    no_cache: bool = typer.Option(False, "--no-cache"),
    cache_dir: Optional[Path] = typer.Option(None, "--cache-dir"),
    offline: bool = typer.Option(False, "--offline"),
) -> None:
    """Fetch one law's markdown at a given date."""
    if semantic not in ("공포일자", "시행일자"):
        raise typer.BadParameter("--semantic must be 공포일자 or 시행일자")

    target = _parse_date(the_date)
    path = f"kr/{law_name}/{category}.md"

    opts = build_global_opts(token, no_cache, cache_dir, offline, json_output)
    client, cache = make_client(opts)

    try:
        commits = get_revisions(client, cache, path)
        if not commits:
            raise NotFoundError(f"no revisions found for {path}")
        chosen = resolve_as_of(commits, target, semantic=semantic)
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

    if json_output:
        fm, md_body = parse_frontmatter(text)
        emit_json(
            {
                "law": law_name,
                "category": category,
                "requested_date": target.isoformat(),
                "resolved_commit_date": chosen.author_date.date().isoformat(),
                "path": path,
                "frontmatter": fm.model_dump(by_alias=True, exclude_none=True),
                "body": md_body,
            },
            kind="laws.get",
        )
        return

    typer.echo(text)


# ---- internals --------------------------------------------------------


def _parse_date(raw: Optional[str]) -> date:
    if raw is None:
        return datetime.now(timezone.utc).astimezone().date()
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise typer.BadParameter(f"--date must be YYYY-MM-DD ({exc})") from exc


def _preflight_budget(
    client,
    *,
    candidates: int,
    yes_exhaust: bool,
    token_present: bool,
    default_limit: int,
    limit: Optional[int],
) -> None:
    """Rate-limit pre-flight for scans that fetch N contents at once.

    Refuses if (a) no token AND candidates > default_limit AND user did not
    pass --limit or --yes-exhaust-quota, OR (b) remaining quota is insufficient
    for ``2 × candidates`` worst-case (commits + contents fetches).
    """
    if not token_present and candidates > default_limit and not yes_exhaust and limit is None:
        raise LegalizeError(
            f"would scan {candidates} laws without a token "
            f"(default limit is {default_limit}); "
            "pass --limit N, --yes-exhaust-quota, or set GITHUB_TOKEN"
        )

    rl = getattr(client, "last_rate_limit", None)
    if rl is None:
        return
    needed = 2 * candidates
    if needed > rl.remaining and not yes_exhaust:
        raise LegalizeError(
            f"would exceed rate-limit budget (need {needed}, have {rl.remaining}); "
            "pass --yes-exhaust-quota to proceed or set GITHUB_TOKEN"
        )


__all__ = ["as_of_cmd", "get_law_cmd"]


# Unused imports kept for API parity (``candidates_for_semantic`` is the entry
# point for a future frontmatter-aware 시행일자 scan).
_ = candidates_for_semantic
_ = List
