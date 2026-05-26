from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from rfmcp_core.contracts import (
    ErrorEnvelope,
    ProvenanceKind,
    ProvenanceRecord,
    RepairSessionSummary,
    RepairStepResult,
    SessionStatus,
    Severity,
)
from rfmcp_core.runtime.session import LiveRepairSessionStore


def _placeholder_session(session_id: str) -> RepairSessionSummary:
    return RepairSessionSummary(
        session_id=session_id,
        status=SessionStatus.CLOSED,
        transport="stdio",
        created_at=datetime.now(timezone.utc),
        step_count=0,
    )


class LiveRepairStepper:
    def __init__(
        self,
        store: LiveRepairSessionStore,
        step_executor: Callable[[str, str], None] | None = None,
    ) -> None:
        self._store = store
        self._step_executor = step_executor

    def execute_step(self, session_id: str, instruction: str) -> RepairStepResult:
        record = self._store.get_record(session_id)
        if record is None:
            error = ErrorEnvelope(
                code="session-not-found",
                message=f"Repair session '{session_id}' was not found.",
                severity=Severity.ERROR,
                provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="repair-session-store"),
                retryable=True,
                suggested_next_step="Open a live repair session before executing a repair step.",
                details={"session_id": session_id},
            )
            return RepairStepResult(
                ok=False,
                session=_placeholder_session(session_id),
                step_index=1,
                instruction=instruction,
                detail="No repair step was executed.",
                error=error,
            )

        if record.status != SessionStatus.OPEN:
            error = ErrorEnvelope(
                code="session-not-open",
                message=f"Repair session '{session_id}' is not open for new steps.",
                severity=Severity.ERROR,
                provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="repair-session-store"),
                retryable=True,
                suggested_next_step="Open a new live repair session or inspect the current session status.",
                details={"session_id": session_id, "status": record.status.value},
            )
            summary = self._store.record_error(session_id, error) or record.to_summary()
            return RepairStepResult(
                ok=False,
                session=summary,
                step_index=max(summary.step_count, 0) + 1,
                instruction=instruction,
                detail="No repair step was executed.",
                error=error,
            )

        try:
            if self._step_executor is not None:
                self._step_executor(session_id, instruction)
        except InterruptedError:
            error = ErrorEnvelope(
                code="repair-step-interrupted",
                message="The live repair step was interrupted before it could complete.",
                severity=Severity.ERROR,
                provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="repair-stepper"),
                retryable=True,
                suggested_next_step="Inspect the active session state, then rerun the step or close the session deliberately.",
                details={"session_id": session_id, "instruction": instruction},
            )
            summary = self._store.record_error(session_id, error, status=SessionStatus.INTERRUPTED) or record.to_summary()
            return RepairStepResult(
                ok=False,
                session=summary,
                step_index=max(summary.step_count, 0) + 1,
                instruction=instruction,
                detail="The repair step stopped before it could update the live session.",
                error=error,
            )

        summary = self._store.record_step(session_id, instruction) or record.to_summary()
        return RepairStepResult(
            ok=True,
            session=summary,
            step_index=summary.step_count,
            instruction=instruction,
            detail="Recorded a bounded repair step against the active live session.",
        )
