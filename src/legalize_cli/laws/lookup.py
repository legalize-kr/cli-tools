"""Shared frontmatter-aware law revision lookup for CLI and MCP callers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional
from urllib.parse import quote
import re

from ..cache import DiskCache
from ..config import LAWS_REPO, OWNER
from ..github.commits import CommitInfo
from ..github.contents import get_file_raw
from ..http import GitHubClient
from .asof import ResolvedAsOf, Semantic, resolve_as_of_with_frontmatter
from .frontmatter import parse as parse_frontmatter
from .model import Frontmatter
from .revisions import get_revisions
from ..util.errors import AmbiguousMatchError, InputValidationError, ParserError
from ..contracts.requests import LawGetRequest


@dataclass(frozen=True)
class ResolvedLawFile:
    """A selected law file, retaining the fetched source bytes for its caller."""

    resolution: ResolvedAsOf
    raw: bytes


def resolve_law_file_as_of(
    client: GitHubClient,
    cache: Optional[DiskCache],
    path: str,
    target_date: date,
    semantic: Semantic,
    *,
    owner: str = OWNER,
    repo: str = LAWS_REPO,
) -> Optional[ResolvedLawFile]:
    """Fetch and select one law revision under a file-level date semantic.

    A single invocation memoizes each revision body and frontmatter. This is
    essential for 시행일자 lookup: selection reads candidate frontmatters and
    the successful candidate is then used again by the presentation layer.
    """
    commits = get_revisions(client, cache, path, owner=owner, repo=repo)
    if not commits:
        return None

    raw_by_sha: dict[str, bytes] = {}
    frontmatter_by_sha: dict[str, Frontmatter] = {}

    def get_raw(commit: CommitInfo) -> bytes:
        if commit.sha not in raw_by_sha:
            raw_by_sha[commit.sha] = get_file_raw(
                client, owner, repo, path, ref=commit.sha
            )
        return raw_by_sha[commit.sha]

    def get_frontmatter(commit: CommitInfo) -> Frontmatter:
        if commit.sha not in frontmatter_by_sha:
            text = get_raw(commit).decode("utf-8", errors="replace")
            frontmatter_by_sha[commit.sha] = parse_frontmatter(text)[0]
        return frontmatter_by_sha[commit.sha]

    resolution = resolve_as_of_with_frontmatter(
        commits, target_date, semantic, get_frontmatter
    )
    if resolution is None:
        return None
    return ResolvedLawFile(resolution=resolution, raw=get_raw(resolution.commit))


__all__ = ["ResolvedLawFile", "resolve_law_file_as_of"]


def resolve_law_path(client: GitHubClient, law_name: str, category: str) -> tuple[str, str, str]:
    """Resolve an exact family or require a choice for duplicate law names."""
    try:
        request = LawGetRequest(law_name=law_name, category=category)
    except ValueError as exc:
        raise InputValidationError("법령명 또는 전체 경로와 법령 구분을 확인하세요.") from exc
    name, category = request.law_name, request.category
    if "/" in name:
        match = re.fullmatch(r"kr/([^/]+)/(법률|시행령|시행규칙|대통령령)(?:\([^/]+\))?\.md", name)
        assert match is not None
        return match[1], name, match[2]
    directory = "kr/" + name.replace(" ", "")
    key = f"{directory}/{category}"
    entries = client.get_json(f"/repos/{OWNER}/{LAWS_REPO}/contents/{quote(directory, safe='/')}")
    if not isinstance(entries, list):
        raise ParserError("법령 디렉터리 응답은 파일 목록이어야 합니다.")
    candidates = sorted(entry["path"] for entry in entries
        if isinstance(entry, dict) and entry.get("type") == "file"
        and isinstance(entry.get("path"), str)
        and (entry["path"] == key + ".md" or
             (entry["path"].startswith(key + "(") and entry["path"].endswith(").md"))))
    if len(candidates) > 1:
        raise AmbiguousMatchError("같은 이름의 법령 파일이 여러 개입니다. 전체 경로를 지정하세요.", candidates)
    return name, candidates[0] if candidates else key + ".md", category
