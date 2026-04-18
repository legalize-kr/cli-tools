"""``legalize auth status`` subcommand."""

from __future__ import annotations

from typing import Optional

import typer

from ..auth import mask_token, resolve_token
from ..http import GitHubClient
from ..util.cli_common import SCHEMA_VERSION, emit_json

auth_app = typer.Typer(
    name="auth",
    help="Authentication and rate-limit status.",
    no_args_is_help=True,
)


@auth_app.command("status")
def auth_status(
    token: Optional[str] = typer.Option(None, "--token", envvar="GITHUB_TOKEN", help="GitHub token"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Show whether a token is loaded and the current rate-limit state."""
    resolved, source = resolve_token(token)
    prefix = mask_token(resolved) if resolved else None

    rate_info = None
    try:
        client = GitHubClient(token=resolved, token_source=source)
        data = client.get_json("/rate_limit")
        core = data.get("resources", {}).get("core", {})
        rate_info = {
            "limit": core.get("limit"),
            "remaining": core.get("remaining"),
            "reset": core.get("reset"),
            "used": core.get("used"),
        }
    except Exception:
        pass

    if json_output:
        emit_json(
            {
                "token_present": resolved is not None,
                "token_source": source,
                "token_prefix": prefix,
                "rate_limit": rate_info,
            },
            kind="auth.status",
        )
        return

    typer.echo(f"Token: {'present' if resolved else 'not set'} (source: {source})")
    if prefix:
        typer.echo(f"  Prefix: {prefix}")
    if rate_info:
        typer.echo(f"Rate limit: {rate_info['remaining']}/{rate_info['limit']} remaining")
        typer.echo(f"  Used: {rate_info['used']}, Reset: {rate_info['reset']}")
    else:
        typer.echo("Rate limit: unavailable (could not reach GitHub)")
