from __future__ import annotations

from typing import Literal, Optional

from ..precedents.model import PrecedentEntry
from .common import RepositorySnapshot, ResultBase, SourceReference


class PrecedentListResult(ResultBase):
    kind: Literal["precedents.list"] = "precedents.list"
    snapshot: RepositorySnapshot
    total: int
    page: int
    page_size: int
    next_page: Optional[int]
    items: list[PrecedentEntry]


class PrecedentDocumentResult(ResultBase):
    kind: Literal["precedents.get"] = "precedents.get"
    identifier: str
    source: SourceReference
    body: str
    body_format: Literal["markdown_with_frontmatter"] = "markdown_with_frontmatter"


__all__ = ["PrecedentDocumentResult", "PrecedentListResult"]
