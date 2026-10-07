from __future__ import annotations

import httpx
import pytest

from legalize_cli.contracts.requests import AdministrativeRuleGetRequest, OrdinanceGetRequest, PrecedentGetRequest
from legalize_cli.http import GitHubClient
from legalize_cli.services.context import ServiceContext
from legalize_cli.services.documents import get_administrative_rule, get_ordinance
from legalize_cli.services.precedents import get_precedent
from legalize_cli.util.errors import AmbiguousMatchError

SHA = "a" * 40
OTHER = "b" * 40


def test_document_path_reads_pinned_sha_not_head() -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if "/git/ref/heads/main" in str(request.url):
            return httpx.Response(200, json={"object": {"type": "commit", "sha": SHA}})
        if request.url.params.get("ref") == SHA:
            return httpx.Response(200, text="---\n출처: https://example.test\n---\nA snapshot")
        return httpx.Response(200, text="B HEAD")

    client = GitHubClient(token=None, token_source="none", transport=httpx.MockTransport(handler))
    with ServiceContext(client, None) as context:
        result = get_administrative_rule(
            context, AdministrativeRuleGetRequest(identifier="기관/고시/예시/본문.md")
        )
    assert result.body.endswith("A snapshot")
    assert result.source.ref == SHA
    assert any("ref=" + SHA in url for url in calls)
    assert all("B HEAD" not in url for url in calls)


def test_precedent_case_number_ambiguity_has_typed_candidates() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if "/git/ref/heads/main" in str(request.url):
            return httpx.Response(200, json={"object": {"type": "commit", "sha": SHA}})
        return httpx.Response(200, json={"tree": [
            {"path": "민사/대법원/A__2026다1.md", "type": "blob", "sha": OTHER},
            {"path": "민사/하급심/B__2026다1.md", "type": "blob", "sha": OTHER},
        ], "truncated": False})

    client = GitHubClient(token=None, token_source="none", transport=httpx.MockTransport(handler))
    with ServiceContext(client, None) as context:
        with pytest.raises(AmbiguousMatchError) as raised:
            get_precedent(context, PrecedentGetRequest(identifier="2026다1"))
    assert raised.value.candidate_total == 2


@pytest.mark.parametrize("dataset", ["precedents", "ordinances"])
def test_other_document_paths_read_the_same_pinned_snapshot(dataset: str) -> None:
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if "/git/ref/heads/main" in str(request.url):
            return httpx.Response(200, json={"object": {"type": "commit", "sha": SHA}})
        if request.url.params.get("ref") == SHA:
            return httpx.Response(200, text="A snapshot")
        return httpx.Response(200, text="B HEAD")

    client = GitHubClient(token=None, token_source="none", transport=httpx.MockTransport(handler))
    with ServiceContext(client, None) as context:
        if dataset == "precedents":
            result = get_precedent(context, PrecedentGetRequest(identifier="민사/대법원/예시.md"))
        else:
            result = get_ordinance(context, OrdinanceGetRequest(identifier="서울특별시/_본청/조례/예시/본문.md"))
    assert result.body == "A snapshot"
    assert result.source.ref == SHA
    assert any("ref=" + SHA in url for url in calls)
