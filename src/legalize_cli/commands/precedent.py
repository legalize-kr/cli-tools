"""``legalize precedents get <arg>`` — retrieve a single precedent markdown."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ..laws.frontmatter import parse as parse_frontmatter
from ..precedents.fetch import fetch_by_id_or_path
from ..util.cli_common import (
    build_global_opts,
    emit_json,
    handle_domain_error,
    make_client,
)
from ..util.errors import LegalizeError
from .list_precedents import precedents_app


@precedents_app.command("get")
def get_precedent_cmd(
    arg: str = typer.Argument(..., metavar="<사건번호|path>"),
    json_output: bool = typer.Option(False, "--json"),
    token: Optional[str] = typer.Option(None, "--token"),
    no_cache: bool = typer.Option(False, "--no-cache"),
    cache_dir: Optional[Path] = typer.Option(None, "--cache-dir"),
    offline: bool = typer.Option(False, "--offline"),
    legacy_map: Optional[Path] = typer.Option(
        None,
        "--legacy-map",
        help="Path to legacy-paths.json for old→new filename fallback lookup.",
    ),
) -> None:
    """Fetch a single precedent by 사건번호 or repo-relative path."""
    opts = build_global_opts(token, no_cache, cache_dir, offline, json_output)
    client, cache = make_client(opts)

    try:
        path, body = fetch_by_id_or_path(client, cache, arg, legacy_map=legacy_map)
    except LegalizeError as exc:
        raise handle_domain_error(exc) from exc
    finally:
        client.close()

    text = body.decode("utf-8", errors="replace")

    if json_output:
        fm, md_body = parse_frontmatter(text)
        emit_json(
            {
                "path": path,
                "frontmatter": fm.model_dump(by_alias=True, exclude_none=True),
                "body": md_body,
            },
            kind="precedents.get",
        )
        return

    typer.echo(text)


__all__ = ["get_precedent_cmd"]
