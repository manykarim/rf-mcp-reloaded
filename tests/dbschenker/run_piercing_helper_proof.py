"""Live proof of the shadow-piercing helper (cross-review proposal #2 refined)
against selectorshub's xpath-practice-page.

Scenario:
1. Setup browser + navigate.
2. Capture ARIA (this writes role-locator hints into the session record).
3. Run a step with a deliberately bad CSS selector whose tokens overlap with a
   known ARIA hint label (e.g. ``[data-test=submit-button]`` while a
   ``button "Submit"`` hint exists).
4. Assert ``suggested_next_step`` includes the role-locator alternative.

This runs against a real page so the proof rides on the same path an agent
would hit.

Run: ``uv run --group web python tests/selectorshub/run_piercing_helper_proof.py``
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RESULTS_DIR = Path(__file__).resolve().parent / "results"

for path in [
    REPO_ROOT / "packages" / "rfmcp_core" / "src",
    REPO_ROOT / "packages" / "rfmcp_mcp" / "src",
]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rfmcp_core.contracts import SessionAction, SnapshotKind, TransportKind  # noqa: E402
from rfmcp_core.runtime.session import LiveSessionStore  # noqa: E402
from rfmcp_mcp.tools.app_inspect_state import build_app_inspect_state_tool  # noqa: E402
from rfmcp_mcp.tools.rf_execute_step import build_execute_step_tool  # noqa: E402
from rfmcp_mcp.tools.rf_session import build_session_tool  # noqa: E402


def main() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    os.environ["RFMCP_SNAPSHOTS_DIR"] = str(RESULTS_DIR / "snapshots")

    store = LiveSessionStore()
    session_tool = build_session_tool(store)
    execute = build_execute_step_tool(store)
    inspect = build_app_inspect_state_tool(store)

    started = time.time()
    sid = session_tool(action=SessionAction.OPEN, transport=TransportKind.STDIO)["session"]["session_id"]
    print(f"[rf_session.open] {sid}")

    setup = execute(
        session_id=sid,
        instructions=[
            "Import Library    Browser",
            "New Browser    chromium    headless=True",
            "Set Browser Timeout    60s",
            "New Context",
            "New Page",
            "Go To    https://www.dbschenker.com/global/business/services/book-and-track    wait_until=domcontentloaded",
            "Sleep    3s",
        ],
    )
    if not setup["ok"]:
        idx = setup["failed_index"]
        bad = setup["results"][idx] if idx is not None else None
        print(f"[setup] failed at index {idx}: {bad}")
        session_tool(action=SessionAction.CLOSE, session_id=sid)
        return 1

    # Capture ARIA so role-locator hints land on the session record.
    aria = inspect(session_id=sid, snapshot_kind=SnapshotKind.ARIA)
    hint_count = len(aria["snapshot"]["manifest"]["summary"].get("selector_hints", []))
    print(f"[aria] {hint_count} role-locator hints captured")
    # Show the first few so we know what's available for matching.
    for h in aria["snapshot"]["manifest"]["summary"]["selector_hints"][:5]:
        print(f"  - {h['locator']}")

    # Pick a selector whose tokens overlap with a real hint label. Selectorshub
    # has a 'Submit' button (per its Dummy Form) → try a bad data-test selector
    # that includes the word 'submit'.
    bad_step = execute(session_id=sid, instruction="Click    [data-test=submit-now]")
    print()
    print(f"[bad-step] ok={bad_step['ok']}")
    suggestion = (bad_step.get("error") or {}).get("suggested_next_step") or ""
    print(f"[bad-step.suggested_next_step]")
    print(f"  {suggestion}")
    print()

    hit_role_locator = "role=" in suggestion and "matched ARIA hint" in suggestion
    print(f"shadow-piercing helper engaged: {'PASS' if hit_role_locator else 'NO MATCH'}")

    session_tool(action=SessionAction.CLOSE, session_id=sid)
    print(f"\nelapsed: {round(time.time() - started, 2)}s")
    return 0 if hit_role_locator else 1


if __name__ == "__main__":
    raise SystemExit(main())
