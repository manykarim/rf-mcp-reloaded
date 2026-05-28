"""Single-keyword execution against the live Robot Framework runtime.

The hot path of the live session surface: every authoring / repair / exploration
loop runs many of these. Kept as a tool of its own (rather than folded into
``rf_session``) so the signature stays lean — one ``session_id``, one Robot
Framework keyword-call line.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from rfmcp_core.runtime.session import LiveSessionStore
from rfmcp_core.runtime.stepper import LiveStepper


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
            str,
            Field(
                description=(
                    "One Robot Framework keyword-call line, written as the suite would (cells "
                    "separated by 2+ spaces or 4-space groups). Assignments use modern RF7 form "
                    "without trailing ' =' (e.g. '${result}    Evaluate    1 + 2')."
                ),
            ),
        ],
    ) -> dict:
        """Execute one Robot Framework keyword in the session's live runtime context.

        Variables, imports, and library state established by previous calls are
        preserved across steps. Returns a ``StepResult`` (``{ok, session, step}``
        on success; ``{ok: False, session, error}`` on failure).
        """

        result = active_stepper.execute_step(session_id, instruction)
        return result.model_dump(mode="json")

    return rf_execute_step
