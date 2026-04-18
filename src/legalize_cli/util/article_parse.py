"""Parse a user-supplied article query into a canonical :class:`ArticleNo`.

Accepted spellings for the same article:

- ``제839조`` / ``839`` / ``839조``
- ``제839조의2`` / ``839조의2`` / ``839-2`` / ``제839-2``

The parser is tolerant: leading ``제``, interior whitespace, and the hyphen
shorthand all collapse to the canonical object ``{조: "839", 의: "2"}``.
"""

from __future__ import annotations

import regex as re

from ..laws.model import ArticleNo
from .errors import ParserError

_QUERY_RE = re.compile(
    r"""
    ^\s*
    제?\s*                    # optional 제 prefix
    (?P<jo>\d+)               # 조 number
    (?:
        \s*조                 # explicit 조
        (?:\s*의\s*(?P<ui1>\d+))?
        |
        \s*-\s*(?P<ui2>\d+)   # or hyphen shorthand (839-2)
    )?
    \s*$
    """,
    re.VERBOSE,
)


def parse_article_query(q: str) -> ArticleNo:
    """Normalize an article query to :class:`ArticleNo`.

    :raises ParserError: the input cannot be interpreted as an article number.
    """
    m = _QUERY_RE.match(q or "")
    if not m:
        raise ParserError(f"cannot parse article query: {q!r}")

    ui = m.group("ui1") or m.group("ui2")
    return ArticleNo(jo=m.group("jo"), ui=ui, hang=None, ho=None)


__all__ = ["parse_article_query"]
