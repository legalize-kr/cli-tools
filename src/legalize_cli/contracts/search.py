from __future__ import annotations

from typing import Literal, Optional

from .common import ContractModel, Dataset, ResultBase, SourceReference


class SearchDatasetOutcome(ContractModel):
    dataset: Dataset
    actual_strategy: Literal["code", "tree", "none"]
    searched_fields: list[Literal["body", "path"]]
    status: Literal["ok", "fallback", "error"]
    total_matches: Optional[int]
    has_more: bool
    error_code: Optional[str]


class SearchItem(ContractModel):
    dataset: Dataset
    path: str
    match_type: Literal["body", "path"]
    source: SourceReference


class SearchResult(ResultBase):
    kind: Literal["search.result"] = "search.result"
    query: str
    scope: Literal["laws", "precedents", "admrules", "ordinances", "all"]
    requested_strategy: Literal["auto", "code", "tree", "metadata"]
    limit: int
    complete: bool
    truncated: bool
    outcomes: list[SearchDatasetOutcome]
    items: list[SearchItem]


__all__ = ["SearchDatasetOutcome", "SearchItem", "SearchResult"]
