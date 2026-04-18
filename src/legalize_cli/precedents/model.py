"""Pydantic model for a precedent index entry.

Keys use the Korean field names as they appear in ``precedent-kr/metadata.json``.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PrecedentEntry(BaseModel):
    """A single entry in ``precedent-kr/metadata.json``."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    판례일련번호: str
    path: str
    사건번호: str = ""
    사건명: str = ""
    선고일자: Optional[str] = None
    법원명: str = ""
    사건종류: str = ""
    판결유형: str = Field(default="")


__all__ = ["PrecedentEntry"]
