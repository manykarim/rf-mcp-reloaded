from __future__ import annotations

from rfmcp_core.runtime.session import LiveRepairSessionStore
from rfmcp_core.runtime.stepper import LiveRepairStepper


def build_execute_step_tool(
    store: LiveRepairSessionStore,
    *,
    stepper: LiveRepairStepper | None = None,
):
    active_stepper = stepper or LiveRepairStepper(store)

    def rf_execute_repair_step(session_id: str, instruction: str) -> dict:
        result = active_stepper.execute_step(session_id, instruction)
        return result.model_dump(mode="json")

    return rf_execute_repair_step
