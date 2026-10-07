"""``legalize laws as-of`` and ``legalize laws get`` subcommands.

Named with the ``_cmd`` suffix per plan §3 to avoid shadowing
:mod:`legalize_cli.laws.asof`.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional, cast

import typer

from ..contracts.requests import LawGetRequest
from ..laws.asof import Semantic
from ..laws.list import enumerate_laws
from ..laws.lookup import resolve_law_file_as_of
from ..services.context import ServiceContext
from ..services.dates import parse_date_or_today
from ..services.laws import get_law
from ..util.cli_common import (
    build_global_opts,
    emit_json,
    handle_domain_error,
    make_client,
)
from ..util.errors import LegalizeError
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
    """List law files selected as of a given date."""
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

        for entry in laws:
            resolved = resolve_law_file_as_of(
                client, cache, entry.path, target, cast(Semantic, semantic)
            )
            if resolved is None:
                continue
            if not include_repealed and resolved.resolution.frontmatter.status == "폐지":
                continue
            results.append(
                {
                    "name": entry.name,
                    "category": entry.category,
                    "path": entry.path,
                    "resolved_version_date": resolved.resolution.semantic_date.isoformat(),
                    "resolved_commit_date": resolved.resolution.commit.author_date.date().isoformat(),
                    "resolved_commit_sha": resolved.resolution.commit.sha,
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
        typer.echo(f"{row['category']:<12}  {row['name']:<28}  {row['resolved_version_date']}")
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
    opts = build_global_opts(token, no_cache, cache_dir, offline, json_output)
    client, cache = make_client(opts)

    try:
        loaded = get_law(
            ServiceContext(client, cache),
            LawGetRequest(law_name=law_name, category=category, date=target.isoformat(), semantic=cast(Semantic, semantic)),
        )
    except LegalizeError as exc:
        raise handle_domain_error(exc) from exc
    finally:
        client.close()

    result = loaded.result
    text = loaded.raw_text
    fm = result.frontmatter
    md_body = result.body
    warning = _file_scope_warning(semantic, target, fm.enforcement_date)

    if json_output:
        payload = {
            "law": result.law,
            "category": result.category,
            "semantic": semantic,
            "requested_date": target.isoformat(),
            "resolved_version_date": result.version.resolved_version_date.isoformat(),
            "resolved_commit_date": result.version.resolved_commit_date.isoformat(),
            "resolved_commit_sha": result.source.ref,
            "path": result.source.path,
            "frontmatter": fm.model_dump(by_alias=True, exclude_none=True),
            "file_effective_date_only": True,
            "body": md_body,
        }
        if warning is not None:
            payload["warning"] = warning
        emit_json(payload, kind="laws.get")
        return

    if warning is not None:
        typer.echo(f"warning: {warning}", err=True)
    typer.echo(text)


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
    for the minimum ``2 × candidates`` request estimate. ``시행일자`` can read
    more candidate frontmatters, so its actual request count may be higher.
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
