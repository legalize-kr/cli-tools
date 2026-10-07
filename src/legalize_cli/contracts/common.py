from __future__ import annotations

from datetime import date
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "2.0"
Dataset = Literal["laws", "precedents", "admrules", "ordinances"]
LawSemantic = Literal["공포일자", "시행일자"]
CommitSha = Annotated[str, Field(pattern=r"^[0-9a-f]{40}$")]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Warning(ContractModel):
    code: str
    message: str
    dataset: Optional[Dataset] = None


class RepositorySnapshot(ContractModel):
    repository: str
    ref: CommitSha

    @model_validator(mode="after")
    def validate_ref(self) -> "RepositorySnapshot":
        import re
        if not re.fullmatch(r"[0-9a-f]{40}", self.ref):
            raise ValueError("snapshot ref must be a 40-character commit SHA")
        return self


class SourceReference(ContractModel):
    dataset: Dataset
    repository: str
    path: str
    ref: Optional[CommitSha] = None
    ref_type: Literal["commit", "unknown"]
    github_url: str
    original_url: Optional[str] = None

    @model_validator(mode="after")
    def validate_ref(self) -> "SourceReference":
        import re
        if self.ref_type == "commit" and (self.ref is None or not re.fullmatch(r"[0-9a-f]{40}", self.ref)):
            raise ValueError("commit source ref must be a 40-character SHA")
        if self.ref_type == "unknown" and self.ref is not None:
            raise ValueError("unknown source ref must be null")
        return self


class LawVersion(ContractModel):
    semantic: LawSemantic
    requested_date: date
    resolved_version_date: date
    resolved_commit_date: date
    promulgation_date: Optional[date] = None
    enforcement_date: Optional[date] = None
    law_id: Optional[str] = None
    law_mst: Optional[Union[int, str]] = None
    effective_date_scope: Literal["file"] = "file"


class ResultBase(ContractModel):
    schema_version: Literal["2.0"] = "2.0"
    warnings: list[Warning]


__all__ = [
    "ContractModel", "Dataset", "LawSemantic", "LawVersion",
    "RepositorySnapshot", "ResultBase", "SCHEMA_VERSION", "SourceReference",
    "Warning",
]
