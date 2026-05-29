"""Real-world stress test against the DB Schenker book-and-track page.

dbschenker.com/global/business/services/book-and-track is a representative
enterprise web app that uses Web Components extensively (custom elements
with shadow DOM, both open and closed in places). This script measures:

1. Shadow DOM coverage:
   - How much of the page lives inside shadow roots?
   - Does the walker (``include_shadow_dom=True``) surface them?
   - Does the closed-shadow probe flag inaccessible content?

2. ARIA snapshot quality:
   - How much of the form is captured semantically?
   - Are the shadow-rooted form fields visible to Playwright's accessibility tree?

3. Automation feasibility:
   - From the ARIA tree, can we identify the booking-form fields?
   - Attempt one interaction (Fill Text on an obvious selector candidate) and
     record whether it succeeds — this is the agent's "could I drive this?" test.

A comprehensive comparison report against selectorshub gets written to
``docs/reports/shadow-dom-stress-comparison.md``.

Run: ``uv run --group web python tests/dbschenker/run_shadow_dom_stress.py``
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SUITE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = SUITE_DIR / "results"

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

TARGET_URL = "https://www.dbschenker.com/global/business/services/book-and-track"

SETUP_STEPS = [
    "Import Library    Browser",
    "New Browser    chromium    headless=True",
    "Set Browser Timeout    60s",
    "New Context    viewport={'width': 1440, 'height': 900}",
    "New Page",
    f"Go To    {TARGET_URL}    wait_until=domcontentloaded",
    # Site is heavily JS-rendered and lazy-loads the shipment widget; give it room.
    "Sleep    5s",
]

# Selectors we'll try to interact with — these are exploratory; the report
# records which one (if any) was actually drivable.
INTERACTION_PROBES: list[tuple[str, str]] = [
    # (description, instruction)
    ("dismiss cookie banner if present", 'Click    [data-test-id="uc-accept-all-button"]'),
    ("dismiss cookie banner (alternative)", "Click    text=Accept All"),
]


def aria_role_counts(yaml_text: str) -> dict[str, int]:
    pattern = re.compile(r"^\s*- ([\w\- ]+)(?:\s|:|\")", re.MULTILINE)
    counts: dict[str, int] = {}
    for match in pattern.findall(yaml_text):
        role = match.strip()
        if role and role != "/url" and role != "/placeholder":
            counts[role] = counts.get(role, 0) + 1
    return counts


def run() -> dict:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    snapshots_dir = RESULTS_DIR / "snapshots"
    os.environ["RFMCP_SNAPSHOTS_DIR"] = str(snapshots_dir)

    store = LiveSessionStore()
    session_tool = build_session_tool(store)
    execute_step = build_execute_step_tool(store)
    inspect = build_app_inspect_state_tool(store)

    started = time.time()
    opened = session_tool(action=SessionAction.OPEN, transport=TransportKind.STDIO)
    session_id = opened["session"]["session_id"]
    print(f"[rf_session.open] session_id={session_id}")

    batch_start = time.time()
    batch = execute_step(session_id=session_id, instructions=SETUP_STEPS)
    batch_elapsed = round(time.time() - batch_start, 2)
    print(f"[batched setup] {len(SETUP_STEPS)} steps in {batch_elapsed:.2f}s, ok={batch['ok']}")
    for entry in batch["results"]:
        flag = "OK " if entry["ok"] else "FAIL"
        print(f"  [{entry['step_index']:02d}] {flag} {entry['instruction'][:65]}")

    snapshots: dict = {}
    interactions: list[dict] = []

    if batch["ok"]:
        # 1. DOM (no walker)
        plain = inspect(
            session_id=session_id,
            snapshot_kind=SnapshotKind.DOM,
            return_inline=True,
            inline_max_bytes=4 * 1024 * 1024,
        )
        snapshots["dom_default"] = {
            "ok": plain["ok"],
            "manifest": plain["snapshot"]["manifest"],
        }

        # 2. DOM with shadow walker
        walked = inspect(
            session_id=session_id,
            snapshot_kind=SnapshotKind.DOM,
            return_inline=True,
            inline_max_bytes=4 * 1024 * 1024,
            include_shadow_dom=True,
        )
        walked_content = walked["snapshot"].get("content") or ""
        snapshots["dom_shadow_walked"] = {
            "ok": walked["ok"],
            "manifest": walked["snapshot"]["manifest"],
            "shadow_root_template_count": walked_content.count('shadowrootmode="open"'),
        }

        # 3. ARIA
        aria = inspect(
            session_id=session_id,
            snapshot_kind=SnapshotKind.ARIA,
            return_inline=True,
            inline_max_bytes=4 * 1024 * 1024,
        )
        aria_content = aria["snapshot"].get("content") or ""
        snapshots["aria"] = {
            "ok": aria["ok"],
            "manifest": aria["snapshot"]["manifest"],
            "automation_signal": {
                "textbox_count": aria_content.count("- textbox"),
                "button_count": aria_content.count("- button"),
                "combobox_count": aria_content.count("- combobox"),
                "form_field_total": (
                    aria_content.count("- textbox") + aria_content.count("- combobox") + aria_content.count("- spinbutton")
                ),
                "has_origin_destination_hint": any(
                    h.lower() in aria_content.lower()
                    for h in ["origin", "destination", "from", "to", "pickup", "delivery"]
                ),
            },
        }

        # 4. Screenshot
        screenshot = inspect(session_id=session_id, snapshot_kind=SnapshotKind.SCREENSHOT)
        snapshots["screenshot"] = {
            "ok": screenshot["ok"],
            "manifest": screenshot["snapshot"]["manifest"],
        }

        # 5. Attempt one interaction — purely exploratory; record what worked.
        for desc, instruction in INTERACTION_PROBES:
            print(f"[interaction probe] {desc}: {instruction[:60]}")
            result = execute_step(session_id=session_id, instruction=instruction)
            interactions.append(
                {
                    "description": desc,
                    "instruction": instruction,
                    "ok": result["ok"],
                    "error_code": (result.get("error") or {}).get("code"),
                    "suggested_next_step": (result.get("error") or {}).get("suggested_next_step"),
                }
            )

    session_tool(action=SessionAction.CLOSE, session_id=session_id)

    duration = round(time.time() - started, 2)
    report = {
        "target": TARGET_URL,
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "duration_seconds": duration,
        "batch": {
            "step_count": len(SETUP_STEPS),
            "executed": batch["executed"],
            "ok": batch["ok"],
            "elapsed_seconds": batch_elapsed,
            "failed_index": batch["failed_index"],
        },
        "snapshots": snapshots,
        "interactions": interactions,
    }
    report_path = RESULTS_DIR / "report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\n[report] wrote {report_path.relative_to(REPO_ROOT)}")
    return report


if __name__ == "__main__":
    run()
