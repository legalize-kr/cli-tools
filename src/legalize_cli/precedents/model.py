"""Pydantic model for a precedent entry derived from the repo tree path.

Path structure: ``{사건종류}/{법원등급}/{법원명}_{선고일자}_{사건번호}.md``
e.g. ``민사/대법원/대법원_2002-09-27_2000다10048.md``
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class PrecedentEntry(BaseModel):
    """A single precedent entry derived from the tree path."""

    model_config = ConfigDict(extra="forbid")

    path: str
    사건종류: str
    법원명: str
    사건번호: str
    판례일련번호: str  # = path; stable identifier without metadata.json


__all__ = ["PrecedentEntry"]
