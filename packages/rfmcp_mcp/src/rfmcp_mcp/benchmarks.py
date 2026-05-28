"""End-to-end proof that the repair loop works over the live MCP surface.

Drives the real MCP tools against a fresh in-process live session: reproduce a
failure live, inspect, repair, and re-run to a pass — exercising real Robot
Framework keyword execution (Stories 5.1-5.4), not a CLI subprocess or synthetic
results. Produces a small benchmark proof pack.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from rfmcp_core.runtime.session import LiveSessionStore
from rfmcp_mcp.tools.app_inspect_state import build_app_inspect_state_tool
from rfmcp_mcp.tools.rf_close_session import build_close_session_tool
from rfmcp_mcp.tools.rf_execute_step import build_execute_step_tool
from rfmcp_mcp.tools.rf_get_context import build_get_context_tool
from rfmcp_mcp.tools.rf_open_session import build_open_session_tool
from rfmcp_mcp.tools.rf_set_context import build_set_context_tool

# A failure that needs no browser: ${STATUS} is unset, so the assertion fails live;
# the repair sets it, and the identical re-run then passes.
_REPAIR_STEP = "Should Be Equal    ${STATUS}    PASS"


class LiveMcpProofCall(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: str
    ok: bool
    detail: str = ""


class LiveMcpProof(BaseModel):
    model_config = ConfigDict(extra="forbid")

    surface: str = "mcp"
    scenario: str = "live-mcp-repair"
    runnable_success: bool
    tool_calls: int = Field(ge=0)
    failed_tool_calls: int = Field(ge=0)
    reproduced_failure: bool
    repaired: bool
    rerun_ok: bool
    calls: list[LiveMcpProofCall] = Field(default_factory=list)


def _require_proof_policy() -> None:
    """Fail loudly if local policy can't grant the capabilities the proof needs.

    Keeps a policy misconfiguration from masquerading as a failed repair proof.
    """

    from rfmcp_core.policy.capabilities import PolicyCapability
    from rfmcp_core.policy.enforcement import capability_allowed
    from rfmcp_core.policy.loader import load_local_policy_defaults

    try:
        policy = load_local_policy_defaults()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Live MCP proof requires a loadable local policy: {exc}") from exc
    for capability in (PolicyCapability.CONTEXT_WRITE, PolicyCapability.INSPECTION_SNAPSHOT):
        if not capability_allowed(policy, capability):
            raise RuntimeError(
                f"Live MCP proof requires the {capability} policy capability to be enabled."
            )


def run_live_mcp_repair_proof() -> LiveMcpProof:
    _require_proof_policy()

    store = LiveSessionStore()
    open_session = build_open_session_tool(store)
    execute_step = build_execute_step_tool(store)
    get_context = build_get_context_tool(store)
    set_context = build_set_context_tool(store)
    inspect_state = build_app_inspect_state_tool(store)
    close_session = build_close_session_tool(store)

    calls: list[LiveMcpProofCall] = []

    def record(tool: str, response: dict, detail: str = "") -> dict:
        calls.append(LiveMcpProofCall(tool=tool, ok=bool(response.get("ok")), detail=detail))
        return response

    def proof(reproduced: bool, repaired: bool, rerun_ok: bool) -> LiveMcpProof:
        return LiveMcpProof(
            runnable_success=reproduced and repaired and rerun_ok,
            tool_calls=len(calls),
            failed_tool_calls=sum(1 for call in calls if not call.ok),
            reproduced_failure=reproduced,
            repaired=repaired,
            rerun_ok=rerun_ok,
            calls=list(calls),
        )

    session_id: str | None = None
    reproduced_failure = repaired = rerun_ok = False
    try:
        opened = record("rf_open_session", open_session("stdio"))
        if not opened.get("ok"):
            return proof(False, False, False)
        session_id = opened["session"]["session_id"]

        broken = record("rf_execute_step", execute_step(session_id, _REPAIR_STEP), "reproduce failure")
        # A genuine repair starts from a real keyword failure, not a session/lifecycle error.
        reproduced_failure = (not broken["ok"]) and broken.get("error", {}).get("code") == "step-failed"

        record("rf_get_context", get_context(session_id), "diagnose runtime context")
        record("app_inspect_state", inspect_state(session_id, "app_context"), "inspect app context")

        repair = record("rf_set_context", set_context(session_id, "${STATUS}", "PASS"), "apply repair")
        repaired = bool(repair["ok"])

        rerun = record("rf_execute_step", execute_step(session_id, _REPAIR_STEP), "rerun proof")
        rerun_ok = bool(rerun["ok"])
    finally:
        if session_id is not None:
            # Always tear down the live RF context so EXECUTION_CONTEXTS never leaks.
            record("rf_close_session", close_session(session_id))

    return proof(reproduced_failure, repaired, rerun_ok)


def write_live_mcp_proof_pack(output_path: Path) -> LiveMcpProof:
    proof = run_live_mcp_repair_proof()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(proof.model_dump(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return proof
