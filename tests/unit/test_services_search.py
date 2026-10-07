from __future__ import annotations

import httpx
import pytest

from legalize_cli.contracts.requests import SearchRequest
from legalize_cli.http import GitHubClient
from legalize_cli.services.context import ServiceContext
from legalize_cli.services.search import search_documents
from legalize_cli.util.errors import AuthError

SHA = "a" * 40


def _context(handler, token_source="none") -> ServiceContext:
    client = GitHubClient(
        token="dummy" if token_source != "none" else None,
        token_source=token_source,
        transport=httpx.MockTransport(handler),
    )
    return ServiceContext(client, None)


def test_no_token_tree_search_is_path_only() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/git/ref/heads/main" in str(request.url):
            return httpx.Response(200, json={"object": {"type": "commit", "sha": SHA}})
        return httpx.Response(200, json={"truncated": False, "tree": [
            {"path": "kr/민법/법률.md", "type": "blob", "sha": "b" * 40},
        ]})

    with _context(handler) as context:
        result = search_documents(context, SearchRequest(keyword="민법", scope="laws"))
    assert result.complete is True
    assert result.outcomes[0].actual_strategy == "tree"
    assert result.outcomes[0].searched_fields == ["path"]
    assert result.items[0].source.ref == SHA
    assert "PATH_SEARCH_ONLY" in [warning.code for warning in result.warnings]


def test_explicit_code_without_token_does_not_fallback() -> None:
    with _context(lambda request: pytest.fail("HTTP should not be called")) as context:
        with pytest.raises(AuthError):
            search_documents(context, SearchRequest(keyword="민법", scope="laws", strategy="code"))


def test_auto_code_failure_falls_back_without_claiming_completeness() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/search/code" in str(request.url):
            return httpx.Response(503)
        if "/git/ref/heads/main" in str(request.url):
            return httpx.Response(200, json={"object": {"type": "commit", "sha": SHA}})
        return httpx.Response(200, json={"truncated": False, "tree": [
            {"path": "kr/민법/법률.md", "type": "blob", "sha": "b" * 40},
        ]})

    with _context(handler, token_source="env") as context:
        result = search_documents(context, SearchRequest(keyword="민법", scope="laws"))
    assert result.complete is False
    assert result.outcomes[0].status == "fallback"
    assert result.outcomes[0].actual_strategy == "tree"
    assert {warning.code for warning in result.warnings} >= {"SEARCH_FALLBACK", "PATH_SEARCH_ONLY"}


def test_partial_failure_is_not_empty_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/legalize-kr/git/ref" in str(request.url):
            return httpx.Response(200, json={"object": {"type": "commit", "sha": SHA}})
        if "/legalize-kr/git/trees" in str(request.url):
            return httpx.Response(200, json={"tree": [], "truncated": False})
        return httpx.Response(503)

    with _context(handler) as context:
        result = search_documents(context, SearchRequest(keyword="무결과", scope="all"))
    assert result.items == []
    assert result.complete is False
    assert len([outcome for outcome in result.outcomes if outcome.status == "error"]) == 3
    assert "PARTIAL_SEARCH" in [warning.code for warning in result.warnings]


def test_code_query_keeps_fixed_repo_and_blob_sha_is_not_commit() -> None:
    queries = []

    def handler(request: httpx.Request) -> httpx.Response:
        queries.append(request.url.params["q"])
        return httpx.Response(200, json={
            "incomplete_results": False,
            "total_count": 1,
            "items": [{
                "path": "kr/민법/법률.md", "sha": "b" * 40,
                "name": "법률.md", "html_url": "https://github.com/legalize-kr/legalize-kr/blob/main/kr/x.md",
                "repository": {"full_name": "legalize-kr/legalize-kr"},
            }],
        })

    with _context(handler, token_source="env") as context:
        result = search_documents(context, SearchRequest(
            keyword='repo:other "민법"', scope="laws", strategy="code",
        ))
    assert len(queries) == 1
    assert queries[0].endswith("repo:legalize-kr/legalize-kr extension:md")
    assert queries[0].startswith('"repo:other \\"민법\\""')
    assert result.items[0].source.ref is None
    assert result.items[0].source.ref_type == "unknown"
    assert result.outcomes[0].searched_fields == ["body"]
    assert "SEARCH_INDEX_NOT_SNAPSHOT" in [warning.code for warning in result.warnings]
