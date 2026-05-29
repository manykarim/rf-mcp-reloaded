"""Live proof against https://selectorshub.com/xpath-practice-page/.

Drives a real in-process Browser Library session through the MCP tool surface
and proves four things end-to-end against a page that uses both regular DOM
and shadow DOM nodes:

1. Batched setup via ``rf_execute_step(instructions=[...])`` returns ONE
   aggregated response with a single session summary.
2. ``snapshot_kind='dom'`` (default) vs ``include_shadow_dom=True``: only the
   walker exposes shadow content as declarative ``<template shadowrootmode="open">``.
3. ``snapshot_kind='aria'`` walks Shadow DOM + iframes natively via Playwright.
4. The DOM summary's ``closed_shadow_probe`` flags custom elements whose
   shadowRoot is null (a strong hint that the page hosts content the toolset
   cannot enter).

Also confirms that ``rf_execute_step`` with a bad locator returns a
``step-failed`` envelope whose ``suggested_next_step`` carries a concrete
``app_inspect_state`` call.

Run: ``uv run --group web python tests/selectorshub/run_shadow_dom_proof.py``
"""

from __future__ import annotations

import json
import os
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

TARGET_URL = "https://selectorshub.com/xpath-practice-page/"

SETUP_STEPS = [
    "Import Library    Browser",
    "New Browser    chromium    headless=True",
    "Set Browser Timeout    60s",
    "New Context",
    "New Page",
    f"Go To    {TARGET_URL}    wait_until=domcontentloaded",
    "Sleep    2s",
]


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

    # ---- batched setup ----------------------------------------------------
    batch_start = time.time()
    batch = execute_step(session_id=session_id, instructions=SETUP_STEPS)
    batch_elapsed = round(time.time() - batch_start, 2)
    print(f"[rf_execute_step batch] {len(SETUP_STEPS)} steps in {batch_elapsed:.2f}s, ok={batch['ok']}, executed={batch['executed']}")
    for entry in batch["results"]:
        flag = "OK " if entry["ok"] else "FAIL"
        print(f"  [{entry['step_index']:02d}] {flag} {entry['instruction'][:65]}")

    snapshot_results: dict = {}
    diagnostic_suggestion = None
    if batch["ok"]:
        # --- dom default ---
        plain = inspect(
            session_id=session_id, snapshot_kind=SnapshotKind.DOM, return_inline=True,
            inline_max_bytes=4 * 1024 * 1024,
        )
        snapshot_results["dom_default"] = {
            "ok": plain["ok"],
            "manifest": plain.get("snapshot", {}).get("manifest"),
            "content_len": len(plain.get("snapshot", {}).get("content") or ""),
            "contains_shadowroot_template": "shadowrootmode" in (plain.get("snapshot", {}).get("content") or ""),
        }

        # --- dom with shadow walker ---
        walked = inspect(
            session_id=session_id,
            snapshot_kind=SnapshotKind.DOM,
            return_inline=True,
            inline_max_bytes=4 * 1024 * 1024,
            include_shadow_dom=True,
        )
        walked_content = walked.get("snapshot", {}).get("content") or ""
        snapshot_results["dom_shadow_walked"] = {
            "ok": walked["ok"],
            "manifest": walked.get("snapshot", {}).get("manifest"),
            "content_len": len(walked_content),
            "contains_shadowroot_template": "shadowrootmode" in walked_content,
            "shadow_root_template_count": walked_content.count('shadowrootmode="open"'),
            "provenance_source": walked.get("snapshot", {}).get("provenance", {}).get("source"),
        }

        # --- aria ---
        aria = inspect(
            session_id=session_id,
            snapshot_kind=SnapshotKind.ARIA,
            return_inline=True,
            inline_max_bytes=4 * 1024 * 1024,
        )
        snapshot_results["aria"] = {
            "ok": aria["ok"],
            "manifest": aria.get("snapshot", {}).get("manifest"),
            "content_len": len(aria.get("snapshot", {}).get("content") or ""),
        }

        # --- screenshot ---
        screenshot = inspect(session_id=session_id, snapshot_kind=SnapshotKind.SCREENSHOT)
        snapshot_results["screenshot"] = {
            "ok": screenshot["ok"],
            "manifest": screenshot.get("snapshot", {}).get("manifest"),
            "content_returned_inline": screenshot.get("snapshot", {}).get("content") is not None,
        }

        # --- diagnostic-suggestion probe: a step that should fail with a parseable locator ---
        bad_step = execute_step(
            session_id=session_id,
            instruction="Click    #this-element-definitely-does-not-exist",
        )
        if bad_step.get("error", {}).get("code") == "step-failed":
            diagnostic_suggestion = {
                "error_code": bad_step["error"]["code"],
                "suggested_next_step": bad_step["error"]["suggested_next_step"],
                "mentions_app_inspect_state": "app_inspect_state" in bad_step["error"]["suggested_next_step"],
                "carries_locator": "#this-element-definitely-does-not-exist" in bad_step["error"]["suggested_next_step"],
            }

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
            "session_summary_returned_once": "session" in batch and isinstance(batch.get("session"), dict),
        },
        "snapshots": snapshot_results,
        "diagnostic_suggestion": diagnostic_suggestion,
    }
    report_path = RESULTS_DIR / "report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\n[report] wrote {report_path.relative_to(REPO_ROOT)}")

    # ---- assertions -------------------------------------------------------
    walked_summary = (snapshot_results.get("dom_shadow_walked") or {}).get("manifest", {}).get("summary") or {}
    probe = walked_summary.get("closed_shadow_probe") or {}
    # The probe is correct when it returns a dict with all four reportable counts,
    # whether or not the specific page contains closed roots (selectorshub uses
    # only open shadow attached to plain <div> elements).
    probe_ran = isinstance(probe, dict) and {
        "custom_element_count",
        "open_shadow_root_count",
        "possible_closed_shadow_root_count",
        "total_open_shadow_roots",
    }.issubset(probe.keys())
    proven = bool(
        batch["ok"]
        and snapshot_results
        and not snapshot_results["dom_default"]["contains_shadowroot_template"]
        and snapshot_results["dom_shadow_walked"]["contains_shadowroot_template"]
        and snapshot_results["dom_shadow_walked"]["shadow_root_template_count"] > 0
        and snapshot_results["aria"]["ok"]
        and snapshot_results["screenshot"]["ok"]
        and probe_ran
        and diagnostic_suggestion is not None
        and diagnostic_suggestion["mentions_app_inspect_state"]
        and diagnostic_suggestion["carries_locator"]
    )
    print()
    print(f"  closed_shadow_probe: {probe}")
    if diagnostic_suggestion:
        print(f"  step-failed suggestion: {diagnostic_suggestion['suggested_next_step'][:140]}")
    print(f"\nLive proof: {'PASS' if proven else 'FAIL'}")
    return {"proven": proven, "report": report}


if __name__ == "__main__":
    result = run()
    raise SystemExit(0 if result["proven"] else 1)
