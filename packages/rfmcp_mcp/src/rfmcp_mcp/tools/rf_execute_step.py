from __future__ import annotations

from rfmcp_core.runtime.session import LiveSessionStore
from rfmcp_core.runtime.stepper import LiveStepper


def build_execute_step_tool(
    store: LiveSessionStore,
    *,
    stepper: LiveStepper | None = None,
):
    active_stepper = stepper or LiveStepper(store)

    def rf_execute_step(session_id: str, instruction: str) -> dict:
        result = active_stepper.execute_step(session_id, instruction)
        return result.model_dump(mode="json")

    return rf_execute_step
