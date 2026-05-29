"""Keyword execution against the live Robot Framework runtime.

The hot path of the live session surface: every authoring / repair / exploration
loop runs many of these. Two calling shapes are supported on the same tool:

- **Single**: ``rf_execute_step(session_id, instruction='Click  #login')`` —
  returns a full ``StepResult``. Use this for the iterative loop where the
  agent decides what to do next after each step.
- **Batched**: ``rf_execute_step(session_id, instructions=['Import Library  Browser',
  'New Browser  chromium  headless=True', ...])`` — runs the list in one MCP
  round-trip. Returns ``{ok, session, executed, results, failed_index}``. The
  session summary appears once at the top level instead of once per step, which
  is the bulk of the token savings vs N sequential calls. Use this for
  deterministic setup / teardown sequences where the agent is already committed.
"""

from __future__ import annotations

from typing import Annotated, Any

from pydantic import Field

from rfmcp_core.contracts import (
    ErrorEnvelope,
    ProvenanceKind,
    ProvenanceRecord,
    Severity,
)
from rfmcp_core.runtime.session import LiveSessionStore
from rfmcp_core.runtime.stepper import LiveStepper


def _error(code: str, message: str, *, next_step: str, details: dict[str, Any] | None = None) -> dict:
    envelope = ErrorEnvelope(
        code=code,
        message=message,
        severity=Severity.ERROR,
        provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="rf_execute_step"),
        retryable=False,
        suggested_next_step=next_step,
        details=details or {},
    )
    return {"ok": False, "error": envelope.model_dump(mode="json")}


def build_execute_step_tool(
    store: LiveSessionStore,
    *,
    stepper: LiveStepper | None = None,
):
    active_stepper = stepper or LiveStepper(store)

    def rf_execute_step(
        session_id: Annotated[
            str,
            Field(description="The id of an open live session (from rf_session action='open')."),
        ],
        instruction: Annotated[
            str | None,
            Field(
                default=None,
                description=(
                    "Single Robot Framework keyword-call line (e.g. '${result}    Evaluate    1 + 2'). "
                    "Cells separated by 2+ spaces. Use this OR instructions, not both."
                ),
            ),
        ] = None,
        instructions: Annotated[
            list[str] | None,
            Field(
                default=None,
                description=(
                    "Batched list of keyword-call lines. Each entry runs as a separate live step "
                    "and is recorded on the session. Use for deterministic setup / teardown sequences."
                ),
            ),
        ] = None,
        stop_on_failure: Annotated[
            bool,
            Field(
                default=True,
                description=(
                    "Batch mode only. When True (default), stop at the first failing step and "
                    "return the partial result. When False, run every instruction even if some fail."
                ),
            ),
        ] = True,
    ) -> dict:
        """Execute one or more Robot Framework keywords in the session's live runtime context.

        Variables, imports, and library state established by previous calls are preserved
        across steps -- batched or not.

        Single mode returns a ``StepResult`` (``{ok, session, step_index, instruction, detail}``;
        on failure also ``error`` with a concrete ``suggested_next_step`` pointing at
        ``app_inspect_state`` when a Browser/Selenium library is loaded).

        Batched mode returns ``{ok, session, executed, results, failed_index}``:
        - ``ok``: True iff every executed step succeeded.
        - ``session``: final ``SessionSummary`` (returned once, not per step — this is the
          batching token win vs N sequential calls).
        - ``executed``: number of instructions actually run (may be less than the input list
          when ``stop_on_failure=True`` fired).
        - ``results``: list of light per-step entries (``ok, step_index, instruction, detail,
          error``) without a repeated session summary.
        - ``failed_index``: zero-based index of the first failing step, or null if none.

        Validation:
        - ``instruction`` XOR ``instructions`` must be set (``missing-input`` / ``conflicting-input``).
        - Empty ``instructions=[]`` is rejected as ``missing-input``.
        """

        if instruction is None and not instructions:
            return _error(
                "missing-input",
                "Provide either 'instruction' (single keyword) or 'instructions' (batch).",
                next_step="Pass instruction='<keyword call>' for a single step or instructions=[...] for a batch.",
            )
        if instruction and instructions:
            return _error(
                "conflicting-input",
                "Pass either 'instruction' (single) or 'instructions' (batch), not both.",
                next_step="Drop one of the two parameters and retry.",
            )

        if instruction is not None:
            result = active_stepper.execute_step(session_id, instruction)
            return result.model_dump(mode="json")

        results: list[dict] = []
        failed_index: int | None = None
        last_session_payload: dict[str, Any] | None = None
        for index, instr in enumerate(instructions or []):
            step_result = active_stepper.execute_step(session_id, instr)
            payload = step_result.model_dump(mode="json")
            last_session_payload = payload.get("session")
            results.append(
                {
                    "ok": payload["ok"],
                    "step_index": payload["step_index"],
                    "instruction": payload["instruction"],
                    "detail": payload["detail"],
                    "error": payload.get("error"),
                }
            )
            if not payload["ok"]:
                failed_index = index
                if stop_on_failure:
                    break

        return {
            "ok": failed_index is None,
            "session": last_session_payload,
            "executed": len(results),
            "results": results,
            "failed_index": failed_index,
        }

    return rf_execute_step
