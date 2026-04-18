"""Pydantic models for the laws domain.

``ArticleNo`` is deliberately a **structured object** rather than a string:
callers (including the JSON consumers behind ``--json``) can filter / sort
by ``조`` / ``의`` without re-parsing the text. ``항`` / ``호`` fields exist
today as placeholders for future sub-article addressing; they emit ``null``.

Field names use ASCII aliases internally (``jo``/``ui``/``hang``/``ho``) but
serialize to the Korean keys documented in the plan (``조``/``의``/``항``/
``호``) so JSON output matches the public contract verbatim.
"""

from __future__ import annotations

from datetime import date
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

ArticleStatus = Literal["active", "deleted"]


class ArticleNo(BaseModel):
    """Structured article number.

    Serializes with Korean keys: ``{조, 의, 항, 호}`` — see ``model_config``.
    """

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    jo: str = Field(alias="조")
    ui: Optional[str] = Field(default=None, alias="의")
    hang: Optional[str] = Field(default=None, alias="항")
    ho: Optional[str] = Field(default=None, alias="호")


class Article(BaseModel):
    """A single article block extracted from a law markdown body."""

    model_config = ConfigDict(extra="forbid")

    article_no: ArticleNo
    heading_level: int
    heading_text: str
    content: str
    annotations: List[str] = Field(default_factory=list)
    status: ArticleStatus = "active"
    parent_structure: List[str] = Field(default_factory=list)


class Frontmatter(BaseModel):
    """Laws-repo YAML frontmatter.

    Observed ``법령구분`` values include the canonical four plus ministry-
    specific variants (e.g. ``국토교통부령``); we accept any string and only
    filter when ``--category`` is passed.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    title: Optional[str] = Field(default=None, alias="제목")
    law_mst: Optional[Union[int, str]] = Field(default=None, alias="법령MST")
    law_id: Optional[str] = Field(default=None, alias="법령ID")
    category: Optional[str] = Field(default=None, alias="법령구분")
    ministries: Optional[List[str]] = Field(default=None, alias="소관부처")
    promulgation_date: Optional[date] = Field(default=None, alias="공포일자")
    promulgation_number: Optional[str] = Field(default=None, alias="공포번호")
    enforcement_date: Optional[date] = Field(default=None, alias="시행일자")
    status: Optional[str] = Field(default=None, alias="상태")
    source: Optional[str] = Field(default=None, alias="출처")


class LawFile(BaseModel):
    """Combined view of a parsed law markdown file."""

    model_config = ConfigDict(extra="forbid")

    path: str
    frontmatter: Frontmatter
    articles: List[Article]


__all__ = [
    "ArticleNo",
    "Article",
    "ArticleStatus",
    "Frontmatter",
    "LawFile",
]
