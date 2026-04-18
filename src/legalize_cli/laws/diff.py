"""Diff two sets of articles.

Three modes:

- ``unified`` — a plain :func:`difflib.unified_diff` over full bodies.
- ``side-by-side`` — two-column text via :class:`difflib.HtmlDiff` is overkill
  for a CLI; we emit a simple left/right text layout instead.
- ``article`` — per-article status computation with rename detection
  (``SequenceMatcher`` ratio ≥ 0.8) and whitespace-only detection.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional, Tuple

from .model import Article, ArticleNo

DiffMode = Literal["unified", "side-by-side", "article"]
ArticleStatus = Literal[
    "modified", "added", "removed", "renamed", "whitespace-only", "unchanged"
]

#: SequenceMatcher ratio threshold for treating a disappeared/added pair as a
#: rename. 0.8 is the plan-prescribed value (§3, §4 Feature 4).
RENAME_SIMILARITY_THRESHOLD = 0.8


@dataclass
class ArticleChange:
    """A per-article entry in ``changes[]`` of the diff JSON payload."""

    article_no: ArticleNo
    status: ArticleStatus
    hunk: Optional[str] = None
    from_article_no: Optional[ArticleNo] = None
    similarity: Optional[float] = None


@dataclass
class DiffResult:
    """Structured result from :func:`diff_laws`."""

    mode: DiffMode
    changes: List[ArticleChange] = field(default_factory=list)
    text: Optional[str] = None  # For unified / side-by-side modes.


def diff_laws(
    a_articles: List[Article],
    b_articles: List[Article],
    *,
    a_body: str = "",
    b_body: str = "",
    mode: DiffMode = "article",
    show_unchanged: bool = False,
) -> DiffResult:
    """Compute a :class:`DiffResult` in the requested mode."""
    if mode == "unified":
        text = "".join(
            difflib.unified_diff(
                a_body.splitlines(keepends=True),
                b_body.splitlines(keepends=True),
                fromfile="a",
                tofile="b",
            )
        )
        return DiffResult(mode=mode, text=text)

    if mode == "side-by-side":
        text = _side_by_side(a_body, b_body)
        return DiffResult(mode=mode, text=text)

    return DiffResult(
        mode="article",
        changes=_article_changes(a_articles, b_articles, show_unchanged=show_unchanged),
    )


# ---- article-mode internals -------------------------------------------


def _article_key(a: Article) -> Tuple[str, Optional[str]]:
    return (a.article_no.jo, a.article_no.ui or None)


def _sort_key(k: Tuple[str, Optional[str]]) -> Tuple[int, int]:
    """Sortable key: (jo_int, ui_int_or_-1). Handles ``ui=None`` safely."""
    jo_s, ui_s = k
    try:
        jo_i = int(jo_s)
    except (TypeError, ValueError):
        jo_i = 0
    try:
        ui_i = int(ui_s) if ui_s is not None else -1
    except (TypeError, ValueError):
        ui_i = -1
    return (jo_i, ui_i)


def _article_changes(
    a_articles: List[Article],
    b_articles: List[Article],
    *,
    show_unchanged: bool,
) -> List[ArticleChange]:
    a_map: Dict[Tuple[str, Optional[str]], Article] = {_article_key(a): a for a in a_articles}
    b_map: Dict[Tuple[str, Optional[str]], Article] = {_article_key(a): a for a in b_articles}

    out: List[ArticleChange] = []
    shared = a_map.keys() & b_map.keys()
    only_a = a_map.keys() - b_map.keys()
    only_b = b_map.keys() - a_map.keys()

    # Shared articles — modified / unchanged / whitespace-only.
    for key in sorted(shared, key=_sort_key):
        a_art, b_art = a_map[key], b_map[key]
        status, hunk = _compare_bodies(a_art, b_art)
        if status == "unchanged" and not show_unchanged:
            continue
        out.append(
            ArticleChange(
                article_no=b_art.article_no,
                status=status,
                hunk=hunk,
            )
        )

    # Rename detection + added/removed fallback.
    rename_pairs, added_leftovers, removed_leftovers = _detect_renames(
        [a_map[k] for k in sorted(only_a, key=_sort_key)],
        [b_map[k] for k in sorted(only_b, key=_sort_key)],
    )

    for removed_article, added_article, ratio in rename_pairs:
        out.append(
            ArticleChange(
                article_no=added_article.article_no,
                status="renamed",
                from_article_no=removed_article.article_no,
                similarity=round(ratio, 4),
                hunk=_unified_article_hunk(removed_article, added_article),
            )
        )

    for art in added_leftovers:
        out.append(ArticleChange(article_no=art.article_no, status="added"))

    for art in removed_leftovers:
        out.append(ArticleChange(article_no=art.article_no, status="removed"))

    return out


def _compare_bodies(a: Article, b: Article) -> Tuple[ArticleStatus, Optional[str]]:
    if a.content == b.content:
        return "unchanged", None
    a_norm = " ".join(a.content.split())
    b_norm = " ".join(b.content.split())
    if a_norm == b_norm:
        return "whitespace-only", None
    hunk = "".join(
        difflib.unified_diff(
            a.content.splitlines(keepends=True),
            b.content.splitlines(keepends=True),
            fromfile=a.heading_text,
            tofile=b.heading_text,
        )
    )
    return "modified", hunk


def _detect_renames(
    removed_side: List[Article],
    added_side: List[Article],
) -> Tuple[List[Tuple[Article, Article, float]], List[Article], List[Article]]:
    """Greedy best-ratio matching, subject to the 0.8 threshold."""
    pairs: List[Tuple[Article, Article, float]] = []
    used_added: set[int] = set()

    for removed in removed_side:
        best_idx = -1
        best_ratio = 0.0
        for idx, added in enumerate(added_side):
            if idx in used_added:
                continue
            ratio = difflib.SequenceMatcher(None, removed.content, added.content).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_idx = idx
        if best_idx >= 0 and best_ratio >= RENAME_SIMILARITY_THRESHOLD:
            pairs.append((removed, added_side[best_idx], best_ratio))
            used_added.add(best_idx)

    paired_removed_ids = {id(r) for r, _a, _ratio in pairs}
    paired_added_ids = {id(a) for _r, a, _ratio in pairs}
    removed_leftovers = [a for a in removed_side if id(a) not in paired_removed_ids]
    added_leftovers = [a for a in added_side if id(a) not in paired_added_ids]
    return pairs, added_leftovers, removed_leftovers


def _unified_article_hunk(a: Article, b: Article) -> str:
    return "".join(
        difflib.unified_diff(
            a.content.splitlines(keepends=True),
            b.content.splitlines(keepends=True),
            fromfile=a.heading_text,
            tofile=b.heading_text,
        )
    )


def _side_by_side(a_body: str, b_body: str) -> str:
    a_lines = a_body.splitlines() or [""]
    b_lines = b_body.splitlines() or [""]
    width = 40
    out: List[str] = []
    for i in range(max(len(a_lines), len(b_lines))):
        left = a_lines[i] if i < len(a_lines) else ""
        right = b_lines[i] if i < len(b_lines) else ""
        out.append(f"{left[:width]:<{width}} | {right[:width]}")
    return "\n".join(out)


__all__ = [
    "ArticleChange",
    "ArticleStatus",
    "DiffMode",
    "DiffResult",
    "RENAME_SIMILARITY_THRESHOLD",
    "diff_laws",
]
