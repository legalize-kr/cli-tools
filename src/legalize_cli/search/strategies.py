"""Pick the right strategy given token presence + scope + user choice."""

from __future__ import annotations

from typing import Literal

Scope = Literal["laws", "precedents", "all"]
Strategy = Literal["code", "tree"]


def select_strategy(
    *,
    token_present: bool,
    scope: Scope,
    user_choice: str = "auto",
) -> Strategy:
    """Return the :data:`Strategy` this run should use.

    - Explicit user choice (``code`` / ``tree``) wins.
    - ``auto`` + token → ``code``.
    - ``auto`` + no token → ``tree``.
    """
    if user_choice in ("code", "tree"):
        return user_choice  # type: ignore[return-value]

    # Legacy alias kept for backwards-compat; treated as tree.
    if user_choice == "metadata":
        return "tree"

    if user_choice != "auto":
        raise ValueError(f"unknown strategy {user_choice!r}")

    if token_present:
        return "code"
    return "tree"


__all__ = ["Scope", "Strategy", "select_strategy"]
