from __future__ import annotations

from typing import Literal, Optional

from ..documents import TreeDocumentEntry
from .common import RepositorySnapshot, ResultBase, SourceReference


class AdministrativeRuleListResult(ResultBase):
    kind: Literal["admrules.list"] = "admrules.list"
    snapshot: RepositorySnapshot
    total: int
    page: int
    page_size: int
    next_page: Optional[int]
    items: list[TreeDocumentEntry]


class OrdinanceListResult(ResultBase):
    kind: Literal["ordinances.list"] = "ordinances.list"
    snapshot: RepositorySnapshot
    total: int
    page: int
    page_size: int
    next_page: Optional[int]
    items: list[TreeDocumentEntry]


class AdministrativeRuleDocumentResult(ResultBase):
    kind: Literal["admrules.get"] = "admrules.get"
    identifier: str
    source: SourceReference
    body: str
    body_format: Literal["markdown_with_frontmatter"] = "markdown_with_frontmatter"


class OrdinanceDocumentResult(ResultBase):
    kind: Literal["ordinances.get"] = "ordinances.get"
    identifier: str
    source: SourceReference
    body: str
    body_format: Literal["markdown_with_frontmatter"] = "markdown_with_frontmatter"


__all__ = [
    "AdministrativeRuleDocumentResult", "AdministrativeRuleListResult",
    "OrdinanceDocumentResult", "OrdinanceListResult",
]
