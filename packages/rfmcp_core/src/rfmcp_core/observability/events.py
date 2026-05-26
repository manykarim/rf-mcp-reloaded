from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from rfmcp_core.models.payloads import ProvenanceKind


class WorkflowEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    surface: str = Field(min_length=1)
    workflow: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    provenance_kind: ProvenanceKind
    benchmark: bool = False
    metadata: dict[str, str] = Field(default_factory=dict)


class JsonlEventWriter:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: WorkflowEvent) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(f"{json.dumps(event.model_dump(), sort_keys=True)}\n")
