from __future__ import annotations

import re
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


_BROWSER_LIBS = {"browser", "seleniumlibrary"}

# Common locator prefixes / shapes used by Browser Library and SeleniumLibrary.
# We don't need to enumerate every form — these cover the prefixes agents reach
# for most often when authoring web scenarios.
_LOCATOR_PREFIX_RE = re.compile(
    r"^("
    r"css\s*=|"           # css=...
    r"xpath\s*=|"         # xpath=...
    r"id\s*=|"            # id=...
    r"name\s*=|"          # name=...
    r"text\s*=|"          # text=...
    r"data-test\s*=|"     # data-test=...
    r"role\s*=|"          # role=...
    r"link\s*=|"
    r"partial link\s*=|"
    r"tag\s*=|"
    r"class\s*=|"
    r"//|"                # raw xpath
    r"\(/|"               # raw xpath starting with grouping
    r"\[[^\]]+\]|"        # attribute selector: [data-test="..."]
    r"\.[A-Za-z_-]|"      # css class .foo
    r"#[A-Za-z_-]"        # css id #foo
    r")",
    re.IGNORECASE,
)


def _looks_like_locator(cell: str) -> bool:
    stripped = cell.strip()
    if not stripped or stripped.startswith(("$", "@", "&")):  # RF variable
        return False
    return bool(_LOCATOR_PREFIX_RE.match(stripped))


def _split_cells(instruction: str) -> list[str]:
    """Split a Robot Framework keyword-call line into cells (2+ spaces or tab)."""
    stripped = instruction.rstrip()
    return [c for c in re.split(r"  +|\t+", stripped) if c]


def _diagnostic_next_step(
    instruction: str,
    libraries: list[str],
    session_id: str,
    *,
    has_possible_closed_shadow_roots: bool = False,
    possible_closed_shadow_root_count: int = 0,
) -> str:
    """Build an actionable suggested_next_step for a failed Browser/Selenium step.

    Returns a concrete app_inspect_state call when a Browser-family library is
    loaded — preferring dom_selector with the failing locator when one is
    parseable, falling back to aria for "what's on the page?" inspections.
    When the session has already observed possibly-closed shadow roots, the
    dom_selector hint is **replaced** with a hard advisory pointing at ARIA
    (closed shadow content is inaccessible by the platform contract — re-trying
    dom_selector is wasted calls). This is cross-review proposal #1.
    Returns a generic guidance string otherwise.
    """

    libs_lower = {lib.lower() for lib in libraries}
    if not (libs_lower & _BROWSER_LIBS):
        return (
            "Inspect runtime context or application state, then adjust the keyword or "
            "arguments and rerun the step."
        )

    cells = _split_cells(instruction)
    locator = next((cell for cell in cells[1:] if _looks_like_locator(cell)), None)

    if has_possible_closed_shadow_roots:
        # Closed shadow content is inaccessible by the platform contract — do
        # not loop on dom_selector. Point at ARIA, which Playwright walks
        # natively across open shadow + iframe boundaries, and warn loudly so
        # the agent stops trying flat CSS selectors that cannot match.
        suffix = (
            f" The session has observed {possible_closed_shadow_root_count} "
            "custom element(s) whose shadowRoot is null (likely closed shadow); "
            "dom_selector cannot reach inside closed shadow roots — switch strategy."
        )
        if locator:
            safe = locator.replace("'", "\\'")
            return (
                f"call app_inspect_state(session_id='{session_id}', snapshot_kind='aria') "
                f"to inspect the page's semantic tree -- the selector '{safe}' may point at "
                "content inside a closed shadow root that no selector can match."
                + suffix
            )
        return (
            f"call app_inspect_state(session_id='{session_id}', snapshot_kind='aria') to "
            "inspect the page's semantic tree." + suffix
        )

    if locator:
        # Escape single quotes for inclusion in the suggested call string.
        safe = locator.replace("'", "\\'")
        return (
            f"call app_inspect_state(session_id='{session_id}', snapshot_kind='dom_selector', "
            f"selector='{safe}') to read the actual HTML at that locator, or snapshot_kind='aria' "
            "to see the page's semantic tree."
        )
    return (
        f"call app_inspect_state(session_id='{session_id}', snapshot_kind='aria') to inspect "
        "the page's semantic tree (Playwright walks Shadow DOM + iframes natively)."
    )


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
            try:
                loaded_libraries = list(engine.imported_libraries())
            except Exception:
                loaded_libraries = list(record.libraries)
            error = ErrorEnvelope(
                code="step-failed",
                message=outcome.error_message or "The live keyword step failed.",
                severity=Severity.ERROR,
                provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="live-execution"),
                retryable=True,
                suggested_next_step=_diagnostic_next_step(
                    instruction,
                    loaded_libraries,
                    session_id,
                    has_possible_closed_shadow_roots=record.has_possible_closed_shadow_roots,
                    possible_closed_shadow_root_count=record.possible_closed_shadow_root_count,
                ),
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
