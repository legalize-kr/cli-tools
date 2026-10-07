from __future__ import annotations

import re
from typing import Optional
from urllib.parse import parse_qsl, quote, urlsplit

import yaml

from ..contracts.common import Dataset, SourceReference


def safe_original_url(value: object) -> Optional[str]:
    if not isinstance(value, str) or re.search(r"[\x00-\x1f\x7f]", value):
        return None
    try:
        parsed = urlsplit(value)
    except ValueError:
        return None
    if parsed.scheme not in ("http", "https") or not parsed.netloc or parsed.username or parsed.password:
        return None
    if any(
        marker in key.lower() for key, _value in parse_qsl(parsed.query)
        for marker in ("token", "secret", "password", "apikey", "api_key", "access_key")
    ):
        return None
    return value


def original_url_from_markdown(text: str) -> Optional[str]:
    frontmatter = re.match(r"\A---\r?\n(.*?)^---(?:\r?\n|\Z)", text, re.MULTILINE | re.DOTALL)
    if frontmatter is None:
        return None
    try:
        data = yaml.safe_load(frontmatter.group(1)) or {}
    except yaml.YAMLError:
        return None
    return safe_original_url(data.get("출처")) if isinstance(data, dict) else None


def make_source(
    *, dataset: Dataset, repo: str, path: str, ref: Optional[str],
    original_url: Optional[str] = None, github_url: Optional[str] = None,
) -> SourceReference:
    if github_url is None:
        selected = ref or "main"
        github_url = f"https://github.com/legalize-kr/{repo}/blob/{selected}/{quote(path, safe='/')}"
    return SourceReference(
        dataset=dataset,
        repository=f"legalize-kr/{repo}",
        path=path,
        ref=ref,
        ref_type="commit" if ref else "unknown",
        github_url=github_url,
        original_url=safe_original_url(original_url),
    )


__all__ = ["make_source", "original_url_from_markdown", "safe_original_url"]
