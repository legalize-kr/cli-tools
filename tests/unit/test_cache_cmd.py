"""Tests for ``legalize cache info`` and ``legalize cache clear``."""

from __future__ import annotations

import json
import time
from pathlib import Path

from typer.testing import CliRunner

from legalize_cli.__main__ import app
from legalize_cli.cache import _SUBDIRS
from legalize_cli.commands.cache_cmd import _parse_duration, inspect_cache


runner = CliRunner()


def _populate_cache(tmp_path: Path) -> Path:
    for sub in _SUBDIRS:
        d = tmp_path / sub
        d.mkdir(parents=True, exist_ok=True)
        (d / "dummy.bin").write_bytes(b"x" * 100)
    return tmp_path


def test_parse_duration() -> None:
    assert _parse_duration("7d") == 7 * 86400
    assert _parse_duration("12h") == 12 * 3600
    assert _parse_duration("1w") == 604800
    assert _parse_duration("30s") == 30


def test_inspect_cache(tmp_path: Path) -> None:
    cache_dir = _populate_cache(tmp_path)
    data = inspect_cache(cache_dir)
    assert data["total_files"] == len(_SUBDIRS)
    assert data["total_bytes"] == len(_SUBDIRS) * 100
    assert "etag" in data["subdirs"]


def test_inspect_empty(tmp_path: Path) -> None:
    data = inspect_cache(tmp_path / "nonexistent")
    assert data["total_files"] == 0


def test_cache_info_json(tmp_path: Path) -> None:
    cache_dir = _populate_cache(tmp_path)
    result = runner.invoke(app, ["cache", "info", "--cache-dir", str(cache_dir), "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["schema_version"] == "1.0"
    assert data["kind"] == "cache.info"
    assert data["total_files"] == len(_SUBDIRS)


def test_cache_info_pretty(tmp_path: Path) -> None:
    cache_dir = _populate_cache(tmp_path)
    result = runner.invoke(app, ["cache", "info", "--cache-dir", str(cache_dir)])
    assert result.exit_code == 0
    assert "Cache directory:" in result.output


def test_cache_clear_yes(tmp_path: Path) -> None:
    cache_dir = _populate_cache(tmp_path)
    result = runner.invoke(app, ["cache", "clear", "--cache-dir", str(cache_dir), "--yes"])
    assert result.exit_code == 0
    assert "Removed" in result.output
    remaining = sum(1 for _ in cache_dir.rglob("*") if _.is_file())
    assert remaining == 0


def test_cache_clear_json_requires_yes(tmp_path: Path) -> None:
    cache_dir = _populate_cache(tmp_path)
    result = runner.invoke(app, ["cache", "clear", "--cache-dir", str(cache_dir), "--json"])
    assert result.exit_code == 1


def test_cache_clear_json_with_yes(tmp_path: Path) -> None:
    cache_dir = _populate_cache(tmp_path)
    result = runner.invoke(app, ["cache", "clear", "--cache-dir", str(cache_dir), "--json", "--yes"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["schema_version"] == "1.0"
    assert data["kind"] == "cache.clear"
    assert data["removed"] == len(_SUBDIRS)


def test_cache_clear_older_than(tmp_path: Path) -> None:
    cache_dir = _populate_cache(tmp_path)
    # Backdate files
    old_time = time.time() - 86400 * 10
    for sub in _SUBDIRS:
        for f in (cache_dir / sub).iterdir():
            import os
            os.utime(f, (old_time, old_time))
    result = runner.invoke(app, ["cache", "clear", "--cache-dir", str(cache_dir), "--older-than", "7d", "--yes"])
    assert result.exit_code == 0
    assert "Removed" in result.output


def test_cache_clear_nonexistent(tmp_path: Path) -> None:
    result = runner.invoke(app, ["cache", "clear", "--cache-dir", str(tmp_path / "nope"), "--yes"])
    assert result.exit_code == 0
