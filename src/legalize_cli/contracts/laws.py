from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field

from ..laws.model import ArticleNo, Frontmatter
from ..laws.list import LawEntry
from .common import ContractModel, LawVersion, RepositorySnapshot, ResultBase, SourceReference


class LawResult(ResultBase):
    kind: Literal["laws.get"] = "laws.get"
    law: str
    category: str
    version: LawVersion
    source: SourceReference
    frontmatter: Frontmatter
    body: str


class LawArticleResult(ResultBase):
    kind: Literal["laws.article"] = "laws.article"
    law: str
    category: str
    version: LawVersion
    source: SourceReference
    article_no: ArticleNo
    status: Literal["active", "deleted"]
    annotations: list[str]
    parent_structure: list[str]
    content: str


class LawListResult(ResultBase):
    kind: Literal["laws.list"] = "laws.list"
    snapshot: RepositorySnapshot
    total: int
    page: int
    page_size: int
    next_page: Optional[int]
    items: list[LawEntry]


class LawDiffVersion(ContractModel):
    version: LawVersion
    source: SourceReference


class ArticleChangeResult(ContractModel):
    article_no: ArticleNo
    status: Literal["modified", "added", "removed", "renamed", "whitespace-only", "unchanged"]
    hunk: Optional[str] = None
    from_article_no: Optional[ArticleNo] = None
    similarity: Optional[float] = None


class LawDiffResult(ResultBase):
    kind: Literal["laws.diff"] = "laws.diff"
    law: str
    category: str
    a: LawDiffVersion
    b: LawDiffVersion
    mode: Literal["article", "unified"]
    changes: list[ArticleChangeResult] = Field(default_factory=list)
    text: Optional[str] = None


__all__ = [
    "ArticleChangeResult", "LawArticleResult", "LawDiffResult", "LawDiffVersion",
    "LawListResult", "LawResult",
]
