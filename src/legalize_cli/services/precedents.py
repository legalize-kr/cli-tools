from __future__ import annotations

from ..config import OWNER, PRECEDENTS_REPO
from ..contracts.common import RepositorySnapshot, Warning
from ..contracts.precedents import PrecedentDocumentResult, PrecedentListResult
from ..contracts.requests import PrecedentGetRequest, PrecedentListRequest
from ..github.refs import resolve_default_branch_head
from ..precedents.enumerate import enumerate_precedents
from ..precedents.fetch import fetch_by_id_or_path
from ..precedents.list import list_precedents as paginate_precedents
from .context import ServiceContext
from .sources import make_source, original_url_from_markdown
from .validation import validate_repository_identifier


def list_precedents(context: ServiceContext, request: PrecedentListRequest) -> PrecedentListResult:
    ref = resolve_default_branch_head(context.client, OWNER, PRECEDENTS_REPO)
    entries = enumerate_precedents(context.client, context.cache, ref=ref)
    total, window, next_page = paginate_precedents(
        entries, court=request.court, type_=request.type_, page=request.page, page_size=request.page_size
    )
    return PrecedentListResult(
        snapshot=RepositorySnapshot(repository=f"{OWNER}/{PRECEDENTS_REPO}", ref=ref),
        total=total, page=request.page, page_size=request.page_size,
        next_page=next_page, items=window, warnings=[],
    )


def get_precedent(context: ServiceContext, request: PrecedentGetRequest) -> PrecedentDocumentResult:
    identifier = validate_repository_identifier(request.identifier)
    ref = resolve_default_branch_head(context.client, OWNER, PRECEDENTS_REPO)
    path, body = fetch_by_id_or_path(
        context.client, context.cache, identifier, ref=ref, legacy_map=None
    )
    text = body.decode("utf-8", errors="replace")
    original = original_url_from_markdown(text)
    warnings = [] if original else [Warning(
        code="ORIGINAL_SOURCE_UNAVAILABLE",
        message="문서 frontmatter에서 안전한 공식 원문 URL을 확인할 수 없습니다.",
        dataset="precedents",
    )]
    return PrecedentDocumentResult(
        identifier=request.identifier,
        source=make_source(dataset="precedents", repo=PRECEDENTS_REPO, path=path, ref=ref, original_url=original),
        body=text, warnings=warnings,
    )


__all__ = ["get_precedent", "list_precedents"]
