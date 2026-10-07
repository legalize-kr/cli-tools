from __future__ import annotations

from typing import Literal

from ..config import ADMRULES_REPO, ORDINANCES_REPO, OWNER
from ..contracts.common import RepositorySnapshot, Warning
from ..contracts.documents import (
    AdministrativeRuleDocumentResult,
    AdministrativeRuleListResult,
    OrdinanceDocumentResult,
    OrdinanceListResult,
)
from ..contracts.requests import (
    AdministrativeRuleGetRequest,
    AdministrativeRuleListRequest,
    OrdinanceGetRequest,
    OrdinanceListRequest,
)
from ..documents import enumerate_documents, fetch_document_by_name_or_path, filter_and_paginate_documents
from ..github.refs import resolve_default_branch_head
from .context import ServiceContext
from .sources import make_source, original_url_from_markdown
from .validation import validate_repository_identifier


def _snapshot(context: ServiceContext, repo: str) -> str:
    return resolve_default_branch_head(context.client, OWNER, repo)


def _missing_source_warning(dataset: Literal["admrules", "ordinances"]):
    return Warning(
        code="ORIGINAL_SOURCE_UNAVAILABLE",
        message="문서 frontmatter에서 안전한 공식 원문 URL을 확인할 수 없습니다.",
        dataset=dataset,
    )


def list_administrative_rules(context: ServiceContext, request: AdministrativeRuleListRequest) -> AdministrativeRuleListResult:
    ref = _snapshot(context, ADMRULES_REPO)
    entries = enumerate_documents(context.client, context.cache, repo=ADMRULES_REPO, ref=ref)
    total, window, next_page = filter_and_paginate_documents(
        entries, category=request.type_, parent_contains=request.agency,
        page=request.page, page_size=request.page_size,
    )
    return AdministrativeRuleListResult(
        snapshot=RepositorySnapshot(repository=f"{OWNER}/{ADMRULES_REPO}", ref=ref),
        total=total, page=request.page, page_size=request.page_size,
        next_page=next_page, items=window, warnings=[],
    )


def get_administrative_rule(context: ServiceContext, request: AdministrativeRuleGetRequest) -> AdministrativeRuleDocumentResult:
    identifier = validate_repository_identifier(request.identifier)
    ref = _snapshot(context, ADMRULES_REPO)
    path, body = fetch_document_by_name_or_path(
        context.client, context.cache, identifier, repo=ADMRULES_REPO, ref=ref,
        category=request.type_, parent_contains=request.agency,
    )
    text = body.decode("utf-8", errors="replace")
    original = original_url_from_markdown(text)
    return AdministrativeRuleDocumentResult(
        identifier=request.identifier,
        source=make_source(dataset="admrules", repo=ADMRULES_REPO, path=path, ref=ref, original_url=original),
        body=text, warnings=[] if original else [_missing_source_warning("admrules")],
    )


def list_ordinances(context: ServiceContext, request: OrdinanceListRequest) -> OrdinanceListResult:
    ref = _snapshot(context, ORDINANCES_REPO)
    entries = enumerate_documents(context.client, context.cache, repo=ORDINANCES_REPO, ref=ref)
    total, window, next_page = filter_and_paginate_documents(
        entries, category=request.type_, parent0=request.jurisdiction,
        parent1=request.subdivision, page=request.page, page_size=request.page_size,
    )
    return OrdinanceListResult(
        snapshot=RepositorySnapshot(repository=f"{OWNER}/{ORDINANCES_REPO}", ref=ref),
        total=total, page=request.page, page_size=request.page_size,
        next_page=next_page, items=window, warnings=[],
    )


def get_ordinance(context: ServiceContext, request: OrdinanceGetRequest) -> OrdinanceDocumentResult:
    identifier = validate_repository_identifier(request.identifier)
    ref = _snapshot(context, ORDINANCES_REPO)
    path, body = fetch_document_by_name_or_path(
        context.client, context.cache, identifier, repo=ORDINANCES_REPO, ref=ref,
        category=request.type_, parent0=request.jurisdiction, parent1=request.subdivision,
    )
    text = body.decode("utf-8", errors="replace")
    original = original_url_from_markdown(text)
    return OrdinanceDocumentResult(
        identifier=request.identifier,
        source=make_source(dataset="ordinances", repo=ORDINANCES_REPO, path=path, ref=ref, original_url=original),
        body=text, warnings=[] if original else [_missing_source_warning("ordinances")],
    )


__all__ = [
    "get_administrative_rule", "get_ordinance",
    "list_administrative_rules", "list_ordinances",
]
