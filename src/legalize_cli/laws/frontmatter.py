"""Parse the YAML frontmatter block at the top of a law markdown file.

The parser tolerates:

- A leading UTF-8 BOM (``\\ufeff``).
- CR/LF line endings (normalized to ``\\n`` before YAML parse).
- Missing frontmatter (returns an empty :class:`Frontmatter` + the full body).
- Both list-valued and scalar-valued ``소관부처`` (pipeline historically wrote
  a single string for single-ministry laws).

On read, every string value is NFC-normalized so downstream comparisons are
stable regardless of the upstream encoding choice.
"""

from __future__ import annotations

from typing import Tuple

import regex as re
import yaml

from ..util.errors import ParserError
from ..util.normalize import normalize_text
from .model import Frontmatter

_FRONTMATTER_RE = re.compile(
    r"""
    \A                 # start of string (after optional BOM removal)
    ---[ \t]*\r?\n     # opening fence
    (?P<yaml>.*?)      # yaml body (non-greedy)
    \r?\n---[ \t]*\r?\n
    (?P<body>.*)\Z     # markdown body
    """,
    re.VERBOSE | re.DOTALL,
)


def parse(text: str) -> Tuple[Frontmatter, str]:
    """Return ``(frontmatter, body)``.

    When no frontmatter block is present, an empty :class:`Frontmatter` is
    returned alongside the verbatim input (minus BOM / CR normalization).
    """
    if text is None:
        raise ParserError("frontmatter: input is None")

    text = normalize_text(text).replace("\r\n", "\n").replace("\r", "\n")

    m = _FRONTMATTER_RE.match(text)
    if not m:
        return Frontmatter(), text

    try:
        data = yaml.safe_load(m.group("yaml")) or {}
    except yaml.YAMLError as exc:
        raise ParserError(f"frontmatter: invalid YAML ({exc})") from exc

    if not isinstance(data, dict):
        raise ParserError("frontmatter: top level must be a mapping")

    data = _normalize_values(data)

    # Pydantic accepts Korean aliases; we pass the dict verbatim.
    return Frontmatter.model_validate(data), m.group("body")


def _normalize_values(data: dict) -> dict:
    """NFC-normalize strings; coerce scalar ``소관부처`` to a single-item list."""
    normalized: dict = {}
    for key, value in data.items():
        if isinstance(value, str):
            normalized[key] = normalize_text(value)
        else:
            normalized[key] = value

    ministries = normalized.get("소관부처")
    if isinstance(ministries, str):
        normalized["소관부처"] = [normalized["소관부처"]]
    return normalized


__all__ = ["parse"]
