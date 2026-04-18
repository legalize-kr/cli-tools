"""Entry point for the `legalize` CLI.

Wires subcommand groups. The root callback currently only owns ``--version``;
per-subcommand flags live inside each ``commands/*`` module to keep this file
small.
"""

from __future__ import annotations

from typing import Optional

import typer

from . import __version__
from .commands.list_laws import laws_app
from .commands.list_precedents import precedents_app

# Side-effect imports: each of these modules registers one or more commands on
# either ``laws_app`` / ``precedents_app`` when it is imported.
from .commands import precedent as _precedent_cmd  # noqa: F401
from .commands import asof_cmd as _asof_cmd  # noqa: F401
from .commands import article as _article_cmd  # noqa: F401
from .commands import diff as _diff_cmd  # noqa: F401
from .commands import search_cmd as _search_cmd
from .commands.cache_cmd import cache_app
from .commands.auth_cmd import auth_app
from .commands.mcp_cmd import mcp_app

app = typer.Typer(
    name="legalize",
    help="API-first CLI for Korean laws and precedents (legalize-kr).",
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"legalize {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the version and exit.",
    ),
) -> None:
    """Root callback. Subcommands are attached via ``add_typer``."""
    return None


app.add_typer(laws_app, name="laws")
app.add_typer(precedents_app, name="precedents")
app.add_typer(cache_app, name="cache")
app.add_typer(auth_app, name="auth")
app.add_typer(mcp_app, name="mcp")
_search_cmd.register(app)


if __name__ == "__main__":  # pragma: no cover - module entry
    app()
