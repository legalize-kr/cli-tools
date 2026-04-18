"""Pick the right strategy given token presence + scope + user choice."""

from __future__ import annotations

from typing import Literal

Scope = Literal["laws", "precedents", "all"]
Strategy = Literal["code", "tree", "metadata"]


def select_strategy(
    *,
    token_present: bool,
    scope: Scope,
    user_choice: str = "auto",
) -> Strategy:
    """Return the :data:`Strategy` this run should use.

    - Explicit user choice (``code`` / ``tree`` / ``metadata``) wins.
    - ``auto`` + token + (laws | all) → ``code``.
    - ``auto`` + no token + precedents → ``metadata``.
    - ``auto`` + no token + laws | all → ``tree``.
    """
    if user_choice in ("code", "tree", "metadata"):
        return user_choice  # type: ignore[return-value]

    if user_choice != "auto":
        raise ValueError(f"unknown strategy {user_choice!r}")

    if scope == "precedents":
        return "metadata"
    if token_present:
        return "code"
    return "tree"


__all__ = ["Scope", "Strategy", "select_strategy"]
