"""``GET /search/code`` wrapper — requires a GitHub token."""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict

from ..http import GitHubClient
from ..util.errors import AuthError


class CodeMatch(BaseModel):
    """A single ``/search/code`` item."""

    model_config = ConfigDict(extra="ignore")

    path: str
    sha: str
    name: str
    html_url: Optional[str] = None


def search_code(
    client: GitHubClient,
    query: str,
    *,
    repo: str,
    per_page: int = 30,
) -> List[CodeMatch]:
    """Run a ``/search/code`` query restricted to ``repo``.

    :raises AuthError: if the client has no token attached.
    """
    if client.token_source == "none":
        raise AuthError(
            "/search/code requires a GitHub token; set GITHUB_TOKEN or pass --token"
        )

    q = f"{query} repo:{repo} extension:md"
    payload = client.get_json(
        "/search/code",
        params={"q": q, "per_page": per_page},
        cache_ttl=3600,
    )
    items = payload.get("items", [])
    return [CodeMatch.model_validate(item) for item in items]


__all__ = ["CodeMatch", "search_code"]
