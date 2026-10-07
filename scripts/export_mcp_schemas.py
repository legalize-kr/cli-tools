#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from legalize_cli.contracts.documents import (
    AdministrativeRuleDocumentResult, AdministrativeRuleListResult,
    OrdinanceDocumentResult, OrdinanceListResult,
)
from legalize_cli.contracts.errors import ErrorResult
from legalize_cli.contracts.laws import LawArticleResult, LawDiffResult, LawListResult, LawResult
from legalize_cli.contracts.precedents import PrecedentDocumentResult, PrecedentListResult
from legalize_cli.contracts.search import SearchResult

MODELS = {
    "admrules_get.json": AdministrativeRuleDocumentResult,
    "admrules_list.json": AdministrativeRuleListResult,
    "error.json": ErrorResult,
    "laws_article.json": LawArticleResult,
    "laws_diff.json": LawDiffResult,
    "laws_get.json": LawResult,
    "laws_list.json": LawListResult,
    "ordinances_get.json": OrdinanceDocumentResult,
    "ordinances_list.json": OrdinanceListResult,
    "precedents_get.json": PrecedentDocumentResult,
    "precedents_list.json": PrecedentListResult,
    "search.json": SearchResult,
}


def _content(model) -> str:
    return json.dumps(model.model_json_schema(by_alias=True, mode="serialization"), ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = {name: _content(model) for name, model in MODELS.items()}
    if args.check:
        actual_names = {path.name for path in args.output.glob("*.json")} if args.output.exists() else set()
        ok = actual_names == set(expected)
        for name, content in expected.items():
            path = args.output / name
            ok = ok and path.exists() and path.read_text(encoding="utf-8") == content
        return 0 if ok else 1
    args.output.mkdir(parents=True, exist_ok=True)
    for path in args.output.glob("*.json"):
        if path.name not in expected:
            path.unlink()
    for name, content in expected.items():
        (args.output / name).write_text(content, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
