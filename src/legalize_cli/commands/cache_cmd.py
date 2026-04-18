"""``legalize cache info`` and ``legalize cache clear`` subcommands."""

from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Optional

import typer

from ..cache import TTLS, DiskCache, _SUBDIRS
from ..config import DEFAULT_CACHE_DIR
from ..util.cli_common import SCHEMA_VERSION, emit_json

cache_app = typer.Typer(
    name="cache",
    help="Inspect or clear the local disk cache.",
    no_args_is_help=True,
)


def _dir_stats(p: Path) -> tuple[int, int]:
    """Return ``(file_count, total_bytes)`` for a directory."""
    if not p.exists():
        return 0, 0
    count = 0
    total = 0
    for f in p.rglob("*"):
        if f.is_file():
            count += 1
            total += f.stat().st_size
    return count, total


def inspect_cache(cache_dir: Path) -> dict:
    subdirs = {}
    total_files = 0
    total_bytes = 0
    for name in _SUBDIRS:
        fc, bs = _dir_stats(cache_dir / name)
        subdirs[name] = {"files": fc, "bytes": bs, "ttl_seconds": TTLS.get(name, 0)}
        total_files += fc
        total_bytes += bs
    return {
        "cache_dir": str(cache_dir),
        "total_files": total_files,
        "total_bytes": total_bytes,
        "subdirs": subdirs,
    }


def _parse_duration(s: str) -> int:
    """Parse ``7d``, ``12h``, ``1w``, ``30d`` → seconds."""
    s = s.strip().lower()
    multipliers = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
    if s[-1] in multipliers:
        return int(s[:-1]) * multipliers[s[-1]]
    return int(s)


@cache_app.command("info")
def cache_info(
    cache_dir: Optional[Path] = typer.Option(None, "--cache-dir"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Show cache location, sizes, and TTLs."""
    root = cache_dir or DEFAULT_CACHE_DIR
    data = inspect_cache(root)
    if json_output:
        emit_json(data, kind="cache.info")
        return
    typer.echo(f"Cache directory: {data['cache_dir']}")
    typer.echo(f"Total: {data['total_files']} files, {data['total_bytes']:,} bytes")
    typer.echo()
    for name, info in data["subdirs"].items():
        typer.echo(f"  {name:20s} {info['files']:>6d} files  {info['bytes']:>12,} bytes  (TTL {info['ttl_seconds']}s)")


@cache_app.command("clear")
def cache_clear(
    cache_dir: Optional[Path] = typer.Option(None, "--cache-dir"),
    older_than: Optional[str] = typer.Option(None, "--older-than", help="e.g. 7d, 12h, 1w"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    """Remove cached files. Defaults to clearing everything."""
    root = cache_dir or DEFAULT_CACHE_DIR
    if not root.exists():
        if json_output:
            emit_json({"removed": 0, "cache_dir": str(root)}, kind="cache.clear")
        else:
            typer.echo("Cache directory does not exist. Nothing to clear.")
        return

    if json_output and not yes:
        typer.echo("error: --json mode requires --yes for non-interactive use", err=True)
        raise typer.Exit(code=1)

    removed = 0
    if older_than:
        cutoff = time.time() - _parse_duration(older_than)
        for sub in _SUBDIRS:
            d = root / sub
            if not d.exists():
                continue
            for f in d.rglob("*"):
                if f.is_file() and f.stat().st_mtime < cutoff:
                    f.unlink()
                    removed += 1
    else:
        if not yes:
            typer.confirm(f"Clear all cached data in {root}?", abort=True)
        for sub in _SUBDIRS:
            d = root / sub
            if d.exists():
                for f in d.rglob("*"):
                    if f.is_file():
                        removed += 1
                shutil.rmtree(d)
                d.mkdir()

    if json_output:
        emit_json({"removed": removed, "cache_dir": str(root)}, kind="cache.clear")
    else:
        typer.echo(f"Removed {removed} cached file(s).")
