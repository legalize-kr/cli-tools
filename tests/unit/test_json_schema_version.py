"""Unit test: every ``--json`` payload carries ``schema_version == "1.0"``."""

from __future__ import annotations

import json

from legalize_cli.util.cli_common import SCHEMA_VERSION, emit_json


def test_schema_version_is_1_0() -> None:
    assert SCHEMA_VERSION == "1.0"


def test_emit_json_prefixes_schema_and_kind(capsys) -> None:
    emit_json({"items": [1, 2, 3]}, kind="laws.list")
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["schema_version"] == "1.0"
    assert payload["kind"] == "laws.list"
    assert payload["items"] == [1, 2, 3]


def test_emit_json_serializes_date(capsys) -> None:
    from datetime import date

    emit_json({"day": date(2020, 1, 2)}, kind="test.kind")
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["day"] == "2020-01-02"
