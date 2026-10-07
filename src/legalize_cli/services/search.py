from __future__ import annotations

import httpx

from ..config import ADMRULES_REPO, LAWS_REPO, ORDINANCES_REPO, OWNER, PRECEDENTS_REPO
from ..contracts.common import Warning
from ..contracts.requests import SearchRequest
from ..contracts.search import SearchDatasetOutcome, SearchItem, SearchResult
from ..github.refs import resolve_default_branch_head
from ..search.code_search import code_search_detailed
from ..search.tree_filter import tree_filter_items
from ..util.errors import AuthError, LegalizeError, ParserError
from .context import ServiceContext
from .sources import make_source

DATASETS = (
    ("laws", LAWS_REPO),
    ("precedents", PRECEDENTS_REPO),
    ("admrules", ADMRULES_REPO),
    ("ordinances", ORDINANCES_REPO),
)


def _error_code(exc: Exception) -> str:
    from ..github.search_code import SearchIncompleteError
    from ..util.errors import RateLimitError, RequestBudgetExceededError
    if isinstance(exc, AuthError):
        return "AUTH_REQUIRED"
    if isinstance(exc, SearchIncompleteError):
        return "SEARCH_INCOMPLETE"
    if isinstance(exc, RateLimitError):
        return "RATE_LIMITED"
    if isinstance(exc, RequestBudgetExceededError):
        return "REQUEST_BUDGET_EXCEEDED"
    if isinstance(exc, httpx.TimeoutException):
        return "UPSTREAM_TIMEOUT"
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        if status == 401:
            return "AUTH_FAILED"
        if status == 403:
            return "UPSTREAM_FORBIDDEN"
        if status == 429:
            return "RATE_LIMITED"
    return "UPSTREAM_UNAVAILABLE"


def _fallback_allowed(exc: Exception) -> bool:
    from ..github.search_code import SearchIncompleteError
    from ..util.errors import RateLimitError, RequestBudgetExceededError
    if isinstance(exc, RequestBudgetExceededError):
        return False
    if isinstance(exc, (AuthError, SearchIncompleteError, RateLimitError, httpx.TimeoutException)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in (401, 403, 429) or exc.response.status_code >= 500
    return isinstance(exc, httpx.RequestError)


def _literal_query(keyword: str) -> str:
    return '"' + keyword.replace("\\", "\\\\").replace('"', '\\"') + '"'


def search_documents(context: ServiceContext, request: SearchRequest) -> SearchResult:
    selected = DATASETS if request.scope == "all" else tuple(
        item for item in DATASETS if item[0] == request.scope
    )
    token_present = context.client.token_source != "none"
    requested_code = request.strategy == "code" or (request.strategy == "auto" and token_present)
    items: list[SearchItem] = []
    outcomes: list[SearchDatasetOutcome] = []
    warnings: list[Warning] = []
    errors: list[Exception] = []

    for dataset, repo in selected:
        if context.budget is not None:
            try:
                context.budget.checkpoint()
            except LegalizeError as exc:
                errors.append(exc)
                outcomes.append(SearchDatasetOutcome(
                    dataset=dataset, actual_strategy="none", searched_fields=[],
                    status="error", total_matches=None, has_more=False,
                    error_code=_error_code(exc),
                ))
                continue
        if requested_code:
            try:
                if not token_present:
                    raise AuthError("code 검색에는 로컬 실행 환경의 GitHub token이 필요합니다.")
                detail = code_search_detailed(
                    context.client, _literal_query(request.keyword),
                    repo=f"{OWNER}/{repo}", limit=request.limit + 1,
                )
                valid = []
                for match in detail.items:
                    repo_info = match.repository or {}
                    full_name = repo_info.get("full_name")
                    if full_name is not None and full_name != f"{OWNER}/{repo}":
                        raise ParserError("검색 결과의 저장소가 요청 범위와 다릅니다.")
                    if not match.path.endswith(".md") or match.path.startswith("/") or any(
                        part in ("", ".", "..") for part in match.path.split("/")
                    ):
                        raise ParserError("검색 결과의 경로가 안전한 Markdown 경로가 아닙니다.")
                    valid.append(match)
                has_more = detail.has_more or len(valid) > request.limit
                for match in valid[:request.limit]:
                    items.append(SearchItem(
                        dataset=dataset, path=match.path, match_type="body",
                        source=make_source(
                            dataset=dataset, repo=repo, path=match.path, ref=None,
                        ),
                    ))
                outcomes.append(SearchDatasetOutcome(
                    dataset=dataset, actual_strategy="code", searched_fields=["body"],
                    status="ok", total_matches=detail.total_count,
                    has_more=has_more, error_code=None,
                ))
                warnings.append(Warning(
                    code="SEARCH_INDEX_NOT_SNAPSHOT",
                    message="GitHub code 검색 인덱스와 특정 저장소 commit의 일치를 보장하지 않습니다.",
                    dataset=dataset,
                ))
                continue
            except (LegalizeError, httpx.HTTPError) as exc:
                if request.strategy == "code":
                    errors.append(exc)
                    outcomes.append(SearchDatasetOutcome(
                        dataset=dataset, actual_strategy="none", searched_fields=[],
                        status="error", total_matches=None, has_more=False,
                        error_code=_error_code(exc),
                    ))
                    continue
                if not _fallback_allowed(exc):
                    raise
                warnings.append(Warning(
                    code="SEARCH_FALLBACK",
                    message="본문 검색 실패 후 저장소 경로 검색으로 전환했습니다.",
                    dataset=dataset,
                ))
                fallback = True
        else:
            fallback = False

        try:
            ref = resolve_default_branch_head(context.client, OWNER, repo)
            raw_items = tree_filter_items(
                context.client, context.cache, request.keyword,
                repo=repo, ref=ref, source=dataset,
            )
            has_more = len(raw_items) > request.limit
            for item in raw_items[:request.limit]:
                items.append(SearchItem(
                    dataset=dataset, path=item["path"], match_type="path",
                    source=make_source(dataset=dataset, repo=repo, path=item["path"], ref=ref),
                ))
            outcomes.append(SearchDatasetOutcome(
                dataset=dataset, actual_strategy="tree", searched_fields=["path"],
                status="fallback" if fallback else "ok", total_matches=len(raw_items),
                has_more=has_more, error_code=None,
            ))
            warnings.append(Warning(
                code="PATH_SEARCH_ONLY",
                message="저장소 경로만 검색했으며 문서 본문은 검색하지 않았습니다.",
                dataset=dataset,
            ))
        except (LegalizeError, httpx.HTTPError) as exc:
            errors.append(exc)
            outcomes.append(SearchDatasetOutcome(
                dataset=dataset, actual_strategy="none", searched_fields=[], status="error",
                total_matches=None, has_more=False, error_code=_error_code(exc),
            ))

    successes = [outcome for outcome in outcomes if outcome.status != "error"]
    if not successes:
        if errors:
            if len({_error_code(error) for error in errors}) > 1:
                raise httpx.ConnectError("서로 다른 데이터셋의 검색 오류")
            raise errors[0]
        raise LegalizeError("요청한 데이터셋을 검색하지 못했습니다.")
    if len(successes) != len(outcomes):
        warnings.append(Warning(
            code="PARTIAL_SEARCH",
            message="일부 데이터셋 검색에 실패하여 부분 결과를 반환합니다.",
            dataset=None,
        ))

    deduped: list[SearchItem] = []
    seen: set[tuple[str, str]] = set()
    for item in items:
        key = (item.dataset, item.path)
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    truncated = len(deduped) > request.limit or any(outcome.has_more for outcome in outcomes)
    if truncated:
        warnings.append(Warning(
            code="SEARCH_LIMIT_REACHED",
            message="추가 일치 결과가 있으나 요청 limit에 맞춰 반환했습니다.",
            dataset=None,
        ))
    return SearchResult(
        query=request.keyword, scope=request.scope,
        requested_strategy=request.strategy, limit=request.limit,
        complete=all(outcome.status == "ok" for outcome in outcomes),
        truncated=truncated, outcomes=outcomes, items=deduped[:request.limit],
        warnings=warnings,
    )


__all__ = ["search_documents"]
