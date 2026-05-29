"""Live Shadow-DOM proof against https://selectorshub.com/xpath-practice-page/.

Drives a real in-process Browser Library session through the MCP tool surface and
compares three `app_inspect_state` modes on a page known to use both regular DOM
and shadow DOM nodes (the "Shadow DOM" section + the nested-shadow practice
controls on selectorshub.com's XPath practice page):

- ``snapshot_kind='dom'`` (default): regular Get Page Source — shadow content NOT
  serialized.
- ``snapshot_kind='dom', include_shadow_dom=True``: walks open shadow roots via
  ``Evaluate JavaScript`` and emits declarative ``<template shadowrootmode="open">``.
- ``snapshot_kind='aria'``: Playwright-native ARIA snapshot, which traverses Shadow
  DOM + iframes natively.

The script asserts that the shadow-DOM-walked HTML contains the markers that
the regular ``Get Page Source`` cannot expose, and writes a small JSON report
under ``tests/selectorshub/results/`` for the record.

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
    # selectorshub renders shadow widgets after DOMContentLoaded; allow them to mount.
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

    failures: list[dict] = []
    for index, instruction in enumerate(SETUP_STEPS, start=1):
        t0 = time.time()
        result = execute_step(session_id, instruction)
        dt = round(time.time() - t0, 2)
        ok = bool(result.get("ok"))
        print(f"  [{index:02d}] {'OK ' if ok else 'FAIL'} ({dt:>5.2f}s) {instruction[:70]}")
        if not ok:
            failures.append({"step": instruction, "error": result.get("error", {})})
            break

    snapshot_results: dict = {}
    if not failures:
        # 1. Regular DOM snapshot — shadow content NOT expected.
        plain = inspect(
            session_id=session_id, snapshot_kind=SnapshotKind.DOM, return_inline=True,
            inline_max_bytes=4 * 1024 * 1024,  # let everything through for inspection
        )
        snapshot_results["dom_default"] = {
            "ok": plain["ok"],
            "manifest": plain.get("snapshot", {}).get("manifest"),
            "content_len": len(plain.get("snapshot", {}).get("content") or ""),
            "contains_shadowroot_template": "shadowrootmode" in (plain.get("snapshot", {}).get("content") or ""),
        }

        # 2. DOM snapshot with shadow walker.
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
            "error": walked.get("error"),
        }

        # 3. ARIA snapshot — Playwright natively walks shadow + iframes.
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

        # 4. Screenshot — file-first, never inlined.
        screenshot = inspect(session_id=session_id, snapshot_kind=SnapshotKind.SCREENSHOT)
        snapshot_results["screenshot"] = {
            "ok": screenshot["ok"],
            "manifest": screenshot.get("snapshot", {}).get("manifest"),
            "content_returned_inline": screenshot.get("snapshot", {}).get("content") is not None,
        }

    session_tool(action=SessionAction.CLOSE, session_id=session_id)

    duration = round(time.time() - started, 2)
    report = {
        "target": TARGET_URL,
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "session_id": session_id,
        "duration_seconds": duration,
        "setup_failures": failures,
        "snapshots": snapshot_results,
    }
    report_path = RESULTS_DIR / "report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"\n[report] wrote {report_path.relative_to(REPO_ROOT)}")

    # Hard assertions: shadow walker MUST expose markers absent from default DOM.
    proven = bool(
        snapshot_results
        and not snapshot_results["dom_default"]["contains_shadowroot_template"]
        and snapshot_results["dom_shadow_walked"]["contains_shadowroot_template"]
        and snapshot_results["dom_shadow_walked"]["shadow_root_template_count"] > 0
        and snapshot_results["aria"]["ok"]
        and snapshot_results["screenshot"]["ok"]
    )
    print(f"\nShadow-DOM walker proof: {'PASS' if proven else 'FAIL'}")
    return {"proven": proven, "report": report}


if __name__ == "__main__":
    result = run()
    raise SystemExit(0 if result["proven"] else 1)
