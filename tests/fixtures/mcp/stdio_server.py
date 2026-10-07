"""Fixture-only subprocess launcher; production has no test-mode switch."""

from __future__ import annotations

import httpx

from legalize_cli.http import GitHubClient
from legalize_cli.mcp.server import build_server
from legalize_cli.services.context import ServiceContext

SHA = "a" * 40


def handler(request: httpx.Request) -> httpx.Response:
    url = str(request.url)
    if "/git/ref/heads/main" in url:
        return httpx.Response(200, json={"object": {"type": "commit", "sha": SHA}})
    if "/git/trees/" in url:
        return httpx.Response(200, json={
            "truncated": False,
            "tree": [{"path": "kr/예시법/법률.md", "type": "blob", "sha": "b" * 40}],
        })
    return httpx.Response(404, json={"message": "not found"})


def context_factory() -> ServiceContext:
    return ServiceContext(
        GitHubClient(token=None, token_source="none", transport=httpx.MockTransport(handler)),
        None,
    )


if __name__ == "__main__":
    build_server(context_factory).run(transport="stdio")
