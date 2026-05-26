from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .payloads import FailureCategory, ProvenanceRecord


class HintEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hint_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    recovery: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    tags: list[str] = Field(default_factory=list)
    error_codes: list[str] = Field(default_factory=list)
    libraries: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    message_contains: list[str] = Field(default_factory=list)
    categories: list[FailureCategory] = Field(default_factory=list)
    provenance: ProvenanceRecord


class HintPackManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(min_length=1)
    pack_id: str = Field(min_length=1)
    provider_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    description: str = Field(min_length=1)
    hints: list[HintEntry] = Field(default_factory=list)
