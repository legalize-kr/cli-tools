from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from ..auth import resolve_token
from ..cache import DiskCache
from ..config import DEFAULT_CACHE_DIR
from ..http import GitHubClient
from .limits import RequestBudget


@dataclass
class ServiceContext:
    client: GitHubClient
    cache: Optional[DiskCache]
    budget: Optional[RequestBudget] = None

    def __enter__(self) -> "ServiceContext":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.client.close()


ContextFactory = Callable[[], ServiceContext]


def default_context_factory() -> ServiceContext:
    token, source = resolve_token()
    cache = DiskCache(DEFAULT_CACHE_DIR)
    budget = RequestBudget()
    client = GitHubClient(token=token, token_source=source, cache=cache, budget=budget)
    return ServiceContext(client=client, cache=cache, budget=budget)


__all__ = ["ContextFactory", "ServiceContext", "default_context_factory"]
