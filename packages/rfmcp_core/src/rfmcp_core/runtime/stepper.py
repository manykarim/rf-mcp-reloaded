from __future__ import annotations

from datetime import datetime, timezone

from rfmcp_core.contracts import (
    ErrorEnvelope,
    ProvenanceKind,
    ProvenanceRecord,
    SessionSummary,
    StepResult,
    SessionStatus,
    Severity,
)
from rfmcp_core.runtime.session import LiveSessionStore


def _placeholder_session(session_id: str) -> SessionSummary:
    return SessionSummary(
        session_id=session_id,
        status=SessionStatus.CLOSED,
        transport="stdio",
        created_at=datetime.now(timezone.utc),
        step_count=0,
    )


class LiveStepper:
    """Runs one real Robot Framework keyword per step against the session's live engine."""

    def __init__(self, store: LiveSessionStore) -> None:
        self._store = store

    def execute_step(self, session_id: str, instruction: str) -> StepResult:
        record = self._store.get_record(session_id)
        if record is None:
            error = ErrorEnvelope(
                code="session-not-found",
                message=f"Live session '{session_id}' was not found.",
                severity=Severity.ERROR,
                provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="session-store"),
                retryable=True,
                suggested_next_step="Open a live session before executing a step.",
                details={"session_id": session_id},
            )
            return StepResult(
                ok=False,
                session=_placeholder_session(session_id),
                step_index=1,
                instruction=instruction,
                detail="No step was executed.",
                error=error,
            )

        if record.status != SessionStatus.OPEN:
            error = ErrorEnvelope(
                code="session-not-open",
                message=f"Live session '{session_id}' is not open for new steps.",
                severity=Severity.ERROR,
                provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="session-store"),
                retryable=True,
                suggested_next_step="Open a new live session or inspect the current session status.",
                details={"session_id": session_id, "status": record.status.value},
            )
            summary = self._store.record_error(session_id, error) or record.to_summary()
            return StepResult(
                ok=False,
                session=summary,
                step_index=max(summary.step_count, 0) + 1,
                instruction=instruction,
                detail="No step was executed.",
                error=error,
            )

        engine = self._store.get_or_create_engine(session_id)
        if engine is None:  # session closed between the status check and here
            error = ErrorEnvelope(
                code="session-not-open",
                message=f"Live session '{session_id}' is not open for new steps.",
                severity=Severity.ERROR,
                provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="session-store"),
                retryable=True,
                suggested_next_step="Open a new live session or inspect the current session status.",
                details={"session_id": session_id, "status": SessionStatus.CLOSED.value},
            )
            summary = self._store.record_error(session_id, error) or record.to_summary()
            return StepResult(
                ok=False,
                session=summary,
                step_index=max(summary.step_count, 0) + 1,
                instruction=instruction,
                detail="No step was executed.",
                error=error,
            )
        try:
            outcome = engine.execute(instruction)
        except InterruptedError:
            return self._interrupted(session_id, instruction, record)

        if not outcome.ok:
            error = ErrorEnvelope(
                code="step-failed",
                message=outcome.error_message or "The live keyword step failed.",
                severity=Severity.ERROR,
                provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="live-execution"),
                retryable=True,
                suggested_next_step="Inspect runtime context or application state, then adjust the keyword or arguments and rerun the step.",
                details={
                    "session_id": session_id,
                    "instruction": instruction,
                    "keyword": outcome.keyword,
                    "error_type": outcome.error_type,
                },
            )
            # A failed keyword is still an executed step; record it and surface the failure.
            summary = self._store.record_step(session_id, instruction) or record.to_summary()
            self._store.record_error(session_id, error)
            return StepResult(
                ok=False,
                session=self._store.get_summary(session_id) or summary,
                step_index=summary.step_count,
                instruction=instruction,
                detail=f"Keyword '{outcome.keyword}' executed and failed in the live session.",
                error=error,
            )

        summary = self._store.record_step(session_id, instruction) or record.to_summary()
        detail = f"Executed keyword '{outcome.keyword}' in the live session."
        if outcome.assigned is not None:
            detail += f" Assigned {outcome.assigned} = {outcome.return_value!r}."
        return StepResult(
            ok=True,
            session=summary,
            step_index=summary.step_count,
            instruction=instruction,
            detail=detail,
        )

    def _interrupted(self, session_id: str, instruction: str, record) -> StepResult:
        error = ErrorEnvelope(
            code="step-interrupted",
            message="The live step was interrupted before it could complete.",
            severity=Severity.ERROR,
            provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="stepper"),
            retryable=True,
            suggested_next_step="Inspect the active session state, then rerun the step or close the session deliberately.",
            details={"session_id": session_id, "instruction": instruction},
        )
        summary = self._store.record_error(session_id, error, status=SessionStatus.INTERRUPTED) or record.to_summary()
        return StepResult(
            ok=False,
            session=summary,
            step_index=max(summary.step_count, 0) + 1,
            instruction=instruction,
            detail="The step stopped before it could update the live session.",
            error=error,
        )
