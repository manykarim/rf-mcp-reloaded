from __future__ import annotations

from pathlib import Path

from rfmcp_core.models.payloads import ProvenanceKind
from rfmcp_core.observability.events import JsonlEventWriter, WorkflowEvent


def emit_cli_event(path: Path, workflow: str, event_type: str, detail: str, benchmark: bool = False) -> None:
    writer = JsonlEventWriter(path)
    writer.write(
        WorkflowEvent(
            surface="cli",
            workflow=workflow,
            event_type=event_type,
            detail=detail,
            provenance_kind=ProvenanceKind.OBSERVED,
            benchmark=benchmark,
        )
    )
