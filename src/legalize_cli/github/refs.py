from __future__ import annotations

import re

from ..http import GitHubClient
from ..util.errors import ParserError

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def resolve_default_branch_head(client: GitHubClient, owner: str, repo: str) -> str:
    payload = client.get_json(f"/repos/{owner}/{repo}/git/ref/heads/main")
    obj = payload.get("object", {}) if isinstance(payload, dict) else {}
    sha = obj.get("sha")
    if obj.get("type") != "commit" or not isinstance(sha, str) or not _SHA_RE.fullmatch(sha):
        raise ParserError(f"{owner}/{repo} main ref가 유효한 commit SHA를 반환하지 않았습니다.")
    return sha


__all__ = ["resolve_default_branch_head"]
