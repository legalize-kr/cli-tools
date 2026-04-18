"""Shared fixtures for Batch B integration tests.

``CapturingMock`` records each request URL so tests can assert absence of
calls to specific endpoints (notably ``/contents/`` for the 34MB metadata
fetch path).
"""

from __future__ import annotations

import json as _json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional

import httpx
import pytest

FIXTURES = Path(__file__).parent.parent / "fixtures"


@dataclass
class CapturingMock:
    """Mock transport that records every request it handles."""

    handler: Callable[[httpx.Request], httpx.Response]
    calls: List[httpx.Request] = field(default_factory=list)

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append(request)
        return self.handler(request)

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self)

    def urls(self) -> List[str]:
        return [str(r.url) for r in self.calls]


def build_mock(routes: Dict[str, object]) -> CapturingMock:
    """Build a mock that routes by URL-path-containment.

    ``routes`` is ordered — earlier keys take precedence on prefix match. The
    value is either a ``httpx.Response`` or a ``(status_code, body)`` tuple.
    """

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        for needle, response in routes.items():
            if needle in url:
                if isinstance(response, httpx.Response):
                    return response
                if isinstance(response, tuple):
                    status, body = response
                    if isinstance(body, (dict, list)):
                        return httpx.Response(status, json=body)
                    if isinstance(body, bytes):
                        return httpx.Response(status, content=body)
                    return httpx.Response(status, text=str(body))
                if callable(response):
                    return response(request)
        return httpx.Response(404, json={"message": f"no route for {url}"})

    return CapturingMock(handler=handler)


@pytest.fixture
def tree_fixture() -> dict:
    return _json.loads((FIXTURES / "github" / "tree_laws_full.json").read_text())


@pytest.fixture
def commits_fixture() -> list:
    return _json.loads((FIXTURES / "github" / "commits_asof.json").read_text())


@pytest.fixture
def precedent_metadata_fixture() -> dict:
    return _json.loads(
        (FIXTURES / "precedents" / "metadata_small.json").read_text()
    )


@pytest.fixture
def sample_precedent_bytes() -> bytes:
    return (FIXTURES / "precedents" / "sample_precedent.md").read_bytes()


@pytest.fixture
def mingbeop_2015_bytes() -> bytes:
    return (FIXTURES / "laws" / "mingbeop_2015.md").read_bytes()


@pytest.fixture
def mingbeop_2024_bytes() -> bytes:
    return (FIXTURES / "laws" / "mingbeop_2024.md").read_bytes()


def install_client_factory(monkeypatch, factory, modules=None):
    """Monkeypatch ``make_client`` in every command module.

    Each ``commands/*.py`` does ``from ..util.cli_common import make_client``,
    which binds a local module-level name. Patching just the source module is
    not enough — we must patch every target.
    """
    if modules is None:
        modules = [
            "legalize_cli.util.cli_common",
            "legalize_cli.commands.list_laws",
            "legalize_cli.commands.list_precedents",
            "legalize_cli.commands.precedent",
            "legalize_cli.commands.asof_cmd",
            "legalize_cli.commands.article",
            "legalize_cli.commands.diff",
            "legalize_cli.commands.search_cmd",
        ]
    for mod in modules:
        monkeypatch.setattr(f"{mod}.make_client", factory, raising=False)
