from __future__ import annotations

from dataclasses import dataclass

from ..config import LAWS_REPO, OWNER
from ..contracts.common import LawVersion, RepositorySnapshot, Warning
from ..contracts.laws import (
    ArticleChangeResult,
    LawArticleResult,
    LawDiffResult,
    LawDiffVersion,
    LawListResult,
    LawResult,
)
from ..contracts.requests import LawArticleRequest, LawDiffRequest, LawGetRequest, LawListRequest
from ..laws.articles import parse_articles
from ..laws.diff import diff_laws
from ..laws.frontmatter import parse as parse_frontmatter
from ..laws.list import enumerate_laws, filter_and_paginate
from ..laws.lookup import ResolvedLawFile, resolve_law_file_as_of, resolve_law_path
from ..util.article_parse import parse_article_query
from ..util.errors import ArticleNotFoundError, InputValidationError, VersionNotFoundError
from .context import ServiceContext
from .dates import parse_date_or_today
from .sources import make_source


@dataclass(frozen=True)
class LoadedLaw:
    result: LawResult
    raw_text: str


def _warnings(target, semantic: str, enforcement_date, *, side: str | None = None) -> list[Warning]:
    prefix = f"{side}: " if side else ""
    warnings = [Warning(
        code="FILE_LEVEL_EFFECTIVE_DATE_ONLY",
        message=prefix + "파일 단위 날짜 선택이며 조문별 시행일과 경과조치를 판정하지 않습니다.",
        dataset="laws",
    )]
    if semantic == "공포일자" and enforcement_date is not None and target < enforcement_date:
        warnings.insert(0, Warning(
            code="NOT_YET_EFFECTIVE",
            message=prefix + "선택한 공포일자 버전은 기준일에 아직 시행 전입니다.",
            dataset="laws",
        ))
    return warnings


def _resolve(context: ServiceContext, request: LawGetRequest, *, raw_date: str | None = None) -> tuple[str, str, object, ResolvedLawFile]:
    display, path, _category = resolve_law_path(context.client, request.law_name, request.category)
    target = parse_date_or_today(raw_date if raw_date is not None else request.date)
    resolved = resolve_law_file_as_of(
        context.client, context.cache, path, target, request.semantic
    )
    if resolved is None:
        raise VersionNotFoundError(
            f"{target.isoformat()} 기준 {request.semantic} 버전을 찾을 수 없습니다."
        )
    return display, path, target, resolved


def _version_source(display: str, path: str, target, request: LawGetRequest, resolved: ResolvedLawFile):
    raw_text = resolved.raw.decode("utf-8", errors="replace")
    fm, body = parse_frontmatter(raw_text)
    version = LawVersion(
        semantic=request.semantic,
        requested_date=target,
        resolved_version_date=resolved.resolution.semantic_date,
        resolved_commit_date=resolved.resolution.commit.author_date.date(),
        promulgation_date=fm.promulgation_date,
        enforcement_date=fm.enforcement_date,
        law_id=fm.law_id,
        law_mst=fm.law_mst,
    )
    source = make_source(
        dataset="laws", repo=LAWS_REPO, path=path,
        ref=resolved.resolution.commit.sha, original_url=fm.source,
    )
    return raw_text, fm, body, version, source


def _source_warnings(source, *, side: str | None = None) -> list[Warning]:
    if source.original_url is not None:
        return []
    prefix = f"{side}: " if side else ""
    return [Warning(
        code="ORIGINAL_SOURCE_UNAVAILABLE",
        message=prefix + "문서 frontmatter에서 안전한 공식 원문 URL을 확인할 수 없습니다.",
        dataset="laws",
    )]


def get_law(context: ServiceContext, request: LawGetRequest) -> LoadedLaw:
    display, path, target, resolved = _resolve(context, request)
    raw_text, fm, body, version, source = _version_source(display, path, target, request, resolved)
    return LoadedLaw(
        result=LawResult(
            law=display, category=request.category, version=version, source=source,
            frontmatter=fm, body=body,
            warnings=_warnings(target, request.semantic, fm.enforcement_date) + _source_warnings(source),
        ),
        raw_text=raw_text,
    )


def load_law_article(context: ServiceContext, request: LawArticleRequest) -> tuple[LawArticleResult, object]:
    try:
        query = parse_article_query(request.article_no)
    except Exception as exc:
        raise InputValidationError("유효한 조문 번호를 입력하세요.") from exc
    display, path, target, resolved = _resolve(context, request)
    _raw_text, fm, body, version, source = _version_source(display, path, target, request, resolved)
    match = next((article for article in parse_articles(body)
                  if article.article_no.jo == query.jo
                  and (article.article_no.ui or None) == (query.ui or None)), None)
    if match is None:
        raise ArticleNotFoundError(
            f"선택된 {display}/{request.category} 버전에서 {request.article_no}을 찾을 수 없습니다."
        )
    result = LawArticleResult(
        law=display, category=request.category, version=version, source=source,
        article_no=match.article_no, status=match.status,
        annotations=match.annotations, parent_structure=match.parent_structure,
        content=match.content,
        warnings=_warnings(target, request.semantic, fm.enforcement_date) + _source_warnings(source),
    )
    return result, fm


def get_law_article(context: ServiceContext, request: LawArticleRequest) -> LawArticleResult:
    return load_law_article(context, request)[0]


def list_laws(context: ServiceContext, request: LawListRequest) -> LawListResult:
    from ..github.refs import resolve_default_branch_head
    ref = resolve_default_branch_head(context.client, OWNER, LAWS_REPO)
    entries = enumerate_laws(context.client, context.cache, ref=ref)
    total, window, next_page = filter_and_paginate(
        entries, category=None if request.category == "all" else request.category,
        page=request.page, page_size=request.page_size,
    )
    return LawListResult(
        snapshot=RepositorySnapshot(repository=f"{OWNER}/{LAWS_REPO}", ref=ref),
        total=total, page=request.page, page_size=request.page_size,
        next_page=next_page, items=window, warnings=[],
    )


def compare_law_versions(context: ServiceContext, request: LawDiffRequest) -> LawDiffResult:
    base = {"law_name": request.law_name, "category": request.category, "semantic": request.semantic}
    req_a = LawGetRequest(**base, date=request.date_a)
    req_b = LawGetRequest(**base, date=request.date_b)
    display_a, path_a, target_a, resolved_a = _resolve(context, req_a)
    _display_b, path_b, target_b, resolved_b = _resolve(context, req_b)
    _raw_a, fm_a, body_a, version_a, source_a = _version_source(display_a, path_a, target_a, req_a, resolved_a)
    _raw_b, fm_b, body_b, version_b, source_b = _version_source(display_a, path_b, target_b, req_b, resolved_b)
    result = diff_laws(
        parse_articles(body_a) if request.mode == "article" else [],
        parse_articles(body_b) if request.mode == "article" else [],
        a_body=body_a, b_body=body_b, mode=request.mode,
        show_unchanged=request.show_unchanged,
    )
    warnings = _warnings(target_a, request.semantic, fm_a.enforcement_date, side="A")
    warnings += _warnings(target_b, request.semantic, fm_b.enforcement_date, side="B")
    warnings += _source_warnings(source_a, side="A") + _source_warnings(source_b, side="B")
    warnings.append(Warning(
        code="STRUCTURAL_DIFF_ONLY",
        message="Markdown 구조 비교이며 법적 의미나 효력 변화의 자동 판정이 아닙니다.",
        dataset="laws",
    ))
    changes = [ArticleChangeResult(
        article_no=item.article_no, status=item.status, hunk=item.hunk,
        from_article_no=item.from_article_no, similarity=item.similarity,
    ) for item in result.changes]
    return LawDiffResult(
        law=display_a, category=request.category,
        a=LawDiffVersion(version=version_a, source=source_a),
        b=LawDiffVersion(version=version_b, source=source_b),
        mode=request.mode, changes=changes, text=result.text, warnings=warnings,
    )


__all__ = ["LoadedLaw", "compare_law_versions", "get_law", "get_law_article", "list_laws", "load_law_article"]
