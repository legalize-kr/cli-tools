"""Parse the markdown body of a law into a list of :class:`Article` blocks.

Key design choices (see plan §5):

- **Single heading-level-agnostic regex** matches ``^#+\\s*제N조(?:의M)?`` —
  we do not hard-code ``#####`` because law markdown uses various depths.
- **Per-document heading level** is determined as the most common depth
  among matched article lines. All other matches must use that same level
  (monotonicity); any violation raises :class:`AmbiguousHeadingLevelError`
  (exit code 5).
- Non-article headings of the same or shallower depth (e.g. ``## 제1장 총칙``)
  are fine — the ``조`` suffix distinguishes article headings from
  chapter/section headings.
- Each article block runs from its heading through the next article heading
  at the same depth OR the next strictly-shallower heading OR EOF.
- 삭제 detection: an empty body OR a body matching ``삭제 [<YYYY.M.D>]``.
- ``전문개정 YYYY.M.D`` (and variants) inside a body surface as
  :attr:`Article.annotations`.
- ``parent_structure`` is built by walking preceding headings of depth
  shallower than the article level.
"""

from __future__ import annotations

from collections import Counter
from typing import List, Optional, Tuple

import regex as re

from ..util.errors import AmbiguousHeadingLevelError
from .model import Article, ArticleNo

#: Matches any article heading, capturing depth + 조 + optional 의.
_ARTICLE_HEAD_RE = re.compile(
    r"^(?P<hashes>\#+)\s*제\s*(?P<jo>\d+)\s*조(?:\s*의\s*(?P<ui>\d+))?"
    r"(?:\s*\((?P<title>[^)\n]*)\))?\s*$"
)

#: Matches any markdown heading (for parent_structure walking).
_ANY_HEAD_RE = re.compile(r"^(?P<hashes>\#+)\s*(?P<text>.+?)\s*$")

#: Body that is exactly the 삭제 marker (with optional date annotation).
_DELETED_BODY_RE = re.compile(r"^\s*삭제\s*(?:<[^>]*>)?\s*$")

#: Captures ``[전문개정 YYYY.M.D]``, ``[본조신설 YYYY.M.D]`` etc.
_ANNOTATION_RE = re.compile(r"\[(?P<tag>[^\[\]\n]+?)\]")


def parse_articles(body: str) -> List[Article]:
    """Extract articles from a law markdown body."""
    if not body:
        return []

    lines = body.splitlines()
    article_hits = _find_article_headings(lines)

    if not article_hits:
        return []

    article_level = _determine_article_level(article_hits)

    # Monotonicity check: every article heading must use ``article_level``.
    mismatched = [hit for hit in article_hits if hit.depth != article_level]
    if mismatched:
        raise AmbiguousHeadingLevelError(
            "article headings appear at multiple depths: "
            f"expected {article_level}, found "
            f"{sorted({h.depth for h in mismatched})}"
        )

    return [
        _build_article(lines, hit, article_hits, article_level, idx)
        for idx, hit in enumerate(article_hits)
    ]


# ---- internal helpers --------------------------------------------------


class _Hit:
    __slots__ = ("line_index", "depth", "jo", "ui", "title")

    def __init__(self, line_index: int, depth: int, jo: str, ui: Optional[str], title: Optional[str]) -> None:
        self.line_index = line_index
        self.depth = depth
        self.jo = jo
        self.ui = ui
        self.title = title


def _find_article_headings(lines: List[str]) -> List[_Hit]:
    hits: List[_Hit] = []
    for idx, line in enumerate(lines):
        m = _ARTICLE_HEAD_RE.match(line)
        if not m:
            continue
        hits.append(
            _Hit(
                line_index=idx,
                depth=len(m.group("hashes")),
                jo=m.group("jo"),
                ui=m.group("ui"),
                title=m.group("title"),
            )
        )
    return hits


def _determine_article_level(hits: List[_Hit]) -> int:
    depths = Counter(h.depth for h in hits)
    return depths.most_common(1)[0][0]


def _build_article(
    lines: List[str],
    hit: _Hit,
    all_hits: List[_Hit],
    article_level: int,
    index: int,
) -> Article:
    start = hit.line_index
    end = _find_block_end(lines, start, article_level, all_hits, index)

    heading_text = lines[start].strip()
    body_lines = lines[start + 1 : end]
    content_body = "\n".join(body_lines).strip("\n")

    status = "deleted" if _is_deleted(content_body) else "active"

    # Preserve the heading line + blank + body in ``content`` for round-tripping.
    content = "\n".join([lines[start], *body_lines]).rstrip()

    annotations = _extract_annotations(content_body)
    parent_structure = _parent_structure(lines, start, article_level)

    return Article(
        article_no=ArticleNo(jo=hit.jo, ui=hit.ui, hang=None, ho=None),
        heading_level=article_level,
        heading_text=heading_text,
        content=content,
        annotations=annotations,
        status=status,
        parent_structure=parent_structure,
    )


def _find_block_end(
    lines: List[str],
    start: int,
    article_level: int,
    all_hits: List[_Hit],
    index: int,
) -> int:
    """End index (exclusive) for the article block starting at ``start``."""
    # Next article heading at the same level OR next strictly-shallower
    # heading OR EOF — whichever comes first.
    next_article_line = (
        all_hits[index + 1].line_index if index + 1 < len(all_hits) else len(lines)
    )
    for i in range(start + 1, next_article_line):
        m = _ANY_HEAD_RE.match(lines[i])
        if not m:
            continue
        depth = len(m.group("hashes"))
        if depth < article_level:
            return i
    return next_article_line


def _is_deleted(content_body: str) -> bool:
    stripped = content_body.strip()
    if not stripped:
        return True
    # Only a single-line body counts — multi-line "삭제" + other text is
    # ambiguous enough to leave as active.
    if "\n" in stripped:
        return False
    return bool(_DELETED_BODY_RE.match(stripped))


def _extract_annotations(content_body: str) -> List[str]:
    """Surface ``[전문개정 ...]`` / ``[본조신설 ...]`` / ``[개정 ...]`` tags."""
    found: List[str] = []
    for m in _ANNOTATION_RE.finditer(content_body):
        tag = m.group("tag").strip()
        if any(prefix in tag for prefix in ("전문개정", "본조신설", "개정", "조문제목")):
            found.append(tag)
    return found


def _parent_structure(lines: List[str], start: int, article_level: int) -> List[str]:
    """Walk backwards accumulating shallower-level headings (top-most first)."""
    chain: List[Tuple[int, str]] = []
    seen_depths: set[int] = set()
    for i in range(start - 1, -1, -1):
        m = _ANY_HEAD_RE.match(lines[i])
        if not m:
            continue
        depth = len(m.group("hashes"))
        if depth >= article_level:
            continue
        if depth in seen_depths:
            continue
        seen_depths.add(depth)
        chain.append((depth, m.group("text").strip()))
    # Sort by depth ascending so top-most (편) comes first.
    chain.sort(key=lambda pair: pair[0])
    return [text for _depth, text in chain]


__all__ = ["parse_articles"]
