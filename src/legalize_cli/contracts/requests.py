from __future__ import annotations

import re
import unicodedata
from typing import Annotated, Literal, Optional

from pydantic import ConfigDict, Field, StrictBool, StrictInt, field_validator, model_validator

from .common import ContractModel, LawSemantic

LAW_CATEGORIES = Literal["법률", "시행령", "시행규칙", "대통령령"]
LAW_LIST_CATEGORIES = Literal["법률", "시행령", "시행규칙", "대통령령", "all"]
LawName = Annotated[str, Field(min_length=1, max_length=200)]
ArticleQuery = Annotated[str, Field(min_length=1, max_length=40)]
Identifier = Annotated[str, Field(min_length=1, max_length=1024)]
ShortFilter = Annotated[str, Field(min_length=1, max_length=200)]
DateString = Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f]")
ENCODED_TRAVERSAL_RE = re.compile(r"%(?:2f|5c|2e)", re.IGNORECASE)


class RequestModel(ContractModel):
    model_config = ConfigDict(extra="forbid", strict=True)


def _clean(value: str, *, max_length: int, label: str) -> str:
    if CONTROL_RE.search(value):
        raise ValueError(f"{label}에는 제어문자를 사용할 수 없습니다.")
    value = unicodedata.normalize("NFC", value.strip())
    if not value or len(value) > max_length:
        raise ValueError(f"{label}은 1~{max_length}자의 제어문자 없는 문자열이어야 합니다.")
    return value


def _safe_identifier(value: str) -> str:
    value = _clean(value, max_length=1024, label="identifier")
    if ENCODED_TRAVERSAL_RE.search(value) or "\\" in value:
        raise ValueError("인코딩된 경로 구분자와 역슬래시는 허용되지 않습니다.")
    if value in (".", ".."):
        raise ValueError("상위 경로는 허용되지 않습니다.")
    if "://" in value or re.match(r"^[A-Za-z]:", value) or value.startswith("/"):
        raise ValueError("URL과 절대 경로는 허용되지 않습니다.")
    if "/" in value:
        parts = value.split("/")
        if any(part in ("", ".", "..") for part in parts) or not value.endswith(".md"):
            raise ValueError("저장소 상대 Markdown 경로만 허용됩니다.")
    return value


def _optional_short(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return _clean(value, max_length=200, label="filter")


def _date(value: Optional[str]) -> Optional[str]:
    if value is None:
        return value
    from datetime import date as Date
    if not DATE_RE.fullmatch(value):
        raise ValueError("날짜는 YYYY-MM-DD 형식이어야 합니다.")
    Date.fromisoformat(value)
    return value


class PaginationRequest(RequestModel):
    page: StrictInt = Field(default=1, ge=1, le=10_000)
    page_size: StrictInt = Field(default=50, ge=1, le=100)


class LawListRequest(PaginationRequest):
    category: LAW_LIST_CATEGORIES = "all"


class LawGetRequest(RequestModel):
    law_name: LawName
    category: LAW_CATEGORIES = "법률"
    date: Optional[DateString] = None
    semantic: LawSemantic = "공포일자"

    @field_validator("law_name")
    @classmethod
    def validate_law_name(cls, value: str) -> str:
        value = _clean(value, max_length=200, label="law_name")
        value = _safe_identifier(value)
        if "/" in value and not re.fullmatch(
            r"kr/[^/]+/(법률|시행령|시행규칙|대통령령)(?:\([^/]+\))?\.md", value
        ):
            raise ValueError("law_name은 법령명 또는 목록에 있는 법령 Markdown 경로여야 합니다.")
        return value

    @model_validator(mode="after")
    def use_path_category(self):
        if "/" in self.law_name:
            self.category = self.law_name.rsplit("/", 1)[1].split("(", 1)[0].removesuffix(".md")
        return self

    @field_validator("date")
    @classmethod
    def validate_date(cls, value: Optional[str]) -> Optional[str]:
        return _date(value)


class LawArticleRequest(LawGetRequest):
    article_no: ArticleQuery

    @field_validator("article_no")
    @classmethod
    def validate_article_no(cls, value: str) -> str:
        return _clean(value, max_length=40, label="article_no")


class LawDiffRequest(RequestModel):
    law_name: LawName
    date_a: DateString
    date_b: DateString
    category: LAW_CATEGORIES = "법률"
    semantic: LawSemantic = "공포일자"
    mode: Literal["article", "unified"] = "article"
    show_unchanged: StrictBool = False

    @field_validator("law_name")
    @classmethod
    def validate_law_name(cls, value: str) -> str:
        return LawGetRequest.validate_law_name(value)

    @model_validator(mode="after")
    def use_path_category(self):
        if "/" in self.law_name:
            self.category = self.law_name.rsplit("/", 1)[1].split("(", 1)[0].removesuffix(".md")
        return self

    @field_validator("date_a", "date_b")
    @classmethod
    def validate_diff_date(cls, value: str) -> str:
        return _date(value)  # type: ignore[return-value]

    @model_validator(mode="after")
    def validate_order(self) -> "LawDiffRequest":
        if self.date_a > self.date_b:
            raise ValueError("date_a는 date_b보다 늦을 수 없습니다.")
        return self


class PrecedentListRequest(PaginationRequest):
    court: Optional[ShortFilter] = None
    type_: Optional[ShortFilter] = None

    @field_validator("court", "type_")
    @classmethod
    def validate_filters(cls, value: Optional[str]) -> Optional[str]:
        return _optional_short(value)


class PrecedentGetRequest(RequestModel):
    identifier: Identifier

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        return _safe_identifier(value)


class AdministrativeRuleListRequest(PaginationRequest):
    type_: Optional[ShortFilter] = None
    agency: Optional[ShortFilter] = None

    @field_validator("type_", "agency")
    @classmethod
    def validate_filters(cls, value: Optional[str]) -> Optional[str]:
        return _optional_short(value)


class AdministrativeRuleGetRequest(RequestModel):
    identifier: Identifier
    type_: Optional[ShortFilter] = None
    agency: Optional[ShortFilter] = None

    @field_validator("type_", "agency")
    @classmethod
    def validate_filters(cls, value: Optional[str]) -> Optional[str]:
        return _optional_short(value)

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        return _safe_identifier(value)


class OrdinanceListRequest(PaginationRequest):
    type_: Optional[ShortFilter] = None
    jurisdiction: Optional[ShortFilter] = None
    subdivision: Optional[ShortFilter] = None

    @field_validator("type_", "jurisdiction", "subdivision")
    @classmethod
    def validate_filters(cls, value: Optional[str]) -> Optional[str]:
        return _optional_short(value)


class OrdinanceGetRequest(RequestModel):
    identifier: Identifier
    type_: Optional[ShortFilter] = None
    jurisdiction: Optional[ShortFilter] = None
    subdivision: Optional[ShortFilter] = None

    @field_validator("type_", "jurisdiction", "subdivision")
    @classmethod
    def validate_filters(cls, value: Optional[str]) -> Optional[str]:
        return _optional_short(value)

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, value: str) -> str:
        return _safe_identifier(value)


class SearchRequest(RequestModel):
    keyword: LawName
    scope: Literal["laws", "precedents", "admrules", "ordinances", "all"] = "all"
    limit: StrictInt = Field(default=30, ge=1, le=100)
    strategy: Literal["auto", "code", "tree", "metadata"] = "auto"

    @field_validator("keyword")
    @classmethod
    def validate_keyword(cls, value: str) -> str:
        return _clean(value, max_length=200, label="keyword")


REQUEST_MODELS = {
    "laws_list": LawListRequest,
    "laws_get": LawGetRequest,
    "laws_article": LawArticleRequest,
    "laws_diff": LawDiffRequest,
    "precedents_list": PrecedentListRequest,
    "precedents_get": PrecedentGetRequest,
    "admrules_list": AdministrativeRuleListRequest,
    "admrules_get": AdministrativeRuleGetRequest,
    "ordinances_list": OrdinanceListRequest,
    "ordinances_get": OrdinanceGetRequest,
    "search": SearchRequest,
}


__all__ = [name for name in globals() if name.endswith("Request")] + ["REQUEST_MODELS"]
