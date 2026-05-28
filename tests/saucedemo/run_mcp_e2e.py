"""MCP-driven end-to-end web authoring against SauceDemo.

Drives the SauceDemo checkout scenario through the REAL rfmcp MCP tools, one
keyword per step, against a single persistent live in-process Browser session
(the Epic 5 live execution engine). This is exactly what a coding-agent host
does: translate a natural-language scenario into keyword steps, execute them
step-wise in a live session (inspecting state as it goes), then build the final
Robot Framework suite from the steps that actually worked — and prove it runs.

Run: uv run --group web python tests/saucedemo/run_mcp_e2e.py
"""

from __future__ import annotations

import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from rfmcp_core.robot import render_suite_text
from rfmcp_core.runtime.session import LiveSessionStore
from rfmcp_mcp.tools.app_inspect_state import build_app_inspect_state_tool
from rfmcp_mcp.tools.rf_close_session import build_close_session_tool
from rfmcp_mcp.tools.rf_execute_step import build_execute_step_tool
from rfmcp_mcp.tools.rf_get_context import build_get_context_tool
from rfmcp_mcp.tools.rf_get_session import build_get_session_tool
from rfmcp_mcp.tools.rf_open_session import build_open_session_tool

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SUITE_DIR = Path(__file__).resolve().parent
RESULTS_DIR = SUITE_DIR / "results"

# Natural-language scenarios, translated by the agent into live keyword steps.
# (intent, instruction). Selectors avoid a leading '#' so the same lines are valid
# both as live steps and as cells in the generated .robot suite.
SCENARIOS: dict[str, list[tuple[str, str]]] = {
    "checkout": [
        ("Open the web site", "Import Library    Browser"),
        ("Open the web site", "New Browser    chromium    headless=True"),
        ("Open the web site", "Set Browser Timeout    60s"),
        ("Open the web site", "New Context"),
        ("Open the web site", "New Page"),
        ("Open the web site", "Go To    https://www.saucedemo.com    wait_until=domcontentloaded"),
        ("Open the web site", "Get Title    ==    Swag Labs"),
        ("Log in with valid credentials", "Fill Text    id=user-name    standard_user"),
        ("Log in with valid credentials", "Fill Text    id=password    secret_sauce"),
        ("Log in with valid credentials", "Click    id=login-button"),
        ("Log in with valid credentials", "Get Url    *=    inventory.html"),
        ("Add two items to cart", 'Click    [data-test="add-to-cart-sauce-labs-backpack"]'),
        ("Add two items to cart", 'Click    [data-test="add-to-cart-sauce-labs-bike-light"]'),
        ("Assert items were added to cart", "Get Text    .shopping_cart_badge    ==    2"),
        ("Assert items were added to cart", "Click    .shopping_cart_link"),
        ("Assert items were added to cart", "Get Url    *=    cart.html"),
        ("Assert items were added to cart", "Get Element Count    .cart_item    ==    2"),
        ("Perform checkout", 'Click    [data-test="checkout"]'),
        ("Perform checkout", 'Fill Text    [data-test="firstName"]    Many'),
        ("Perform checkout", 'Fill Text    [data-test="lastName"]    Tester'),
        ("Perform checkout", 'Fill Text    [data-test="postalCode"]    12345'),
        ("Perform checkout", 'Click    [data-test="continue"]'),
        ("Perform checkout", "Get Url    *=    checkout-step-two.html"),
        ("Perform checkout", 'Click    [data-test="finish"]'),
        ("Assert checkout is complete", "Get Url    *=    checkout-complete.html"),
        ("Assert checkout is complete", "Get Text    .complete-header    ==    Thank you for your order!"),
        ("Close browser", "Close Browser"),
    ],
    # Negative scenario: a locked-out user must be rejected with the error banner.
    "locked-out-login": [
        ("Open the web site", "Import Library    Browser"),
        ("Open the web site", "New Browser    chromium    headless=True"),
        ("Open the web site", "Set Browser Timeout    60s"),
        ("Open the web site", "New Context"),
        ("Open the web site", "New Page"),
        ("Open the web site", "Go To    https://www.saucedemo.com    wait_until=domcontentloaded"),
        ("Log in with a locked-out user", "Fill Text    id=user-name    locked_out_user"),
        ("Log in with a locked-out user", "Fill Text    id=password    secret_sauce"),
        ("Log in with a locked-out user", "Click    id=login-button"),
        ("Assert login is rejected", 'Get Text    [data-test="error"]    *=    locked out'),
        ("Assert user stays on login page", "Get Url    ==    https://www.saucedemo.com/"),
        ("Close browser", "Close Browser"),
    ],
}


def build_final_suite(name: str, recorded_steps: list[str], *, record=None) -> str:  # noqa: ANN001
    """Assemble a canonically-formatted Robot suite via ``robot.api.parsing``.

    Delegates to ``render_suite_text``, which builds the parsing-model File from the
    recorded steps + declarative manifest (imports/variables/setups/teardowns/tags) and
    calls ``File.save`` for canonical RF7 output (modern ``AS`` alias, no obsolete
    ``${r} =``, proper section ordering, proper escaping).
    """

    title = name.replace("-", " ").title()
    kwargs: dict = {"test_case_name": f"Saucedemo {title}", "body_steps": recorded_steps}
    if record is not None:
        kwargs.update(
            declared_variables=record.declared_variables,
            suite_setup=record.suite_setup,
            suite_teardown=record.suite_teardown,
            test_setup=record.test_setup,
            test_teardown=record.test_teardown,
            test_tags=record.test_tags,
            test_case_setup=record.test_case_setup,
            test_case_teardown=record.test_case_teardown,
            test_case_tags=record.test_case_tags,
        )
    return render_suite_text(**kwargs)


def run_robot(name: str, suite_path: Path) -> dict:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    start = time.time()
    completed = subprocess.run(
        [
            "uv", "run", "--group", "web", "python", "-m", "robot",
            "--outputdir", str(RESULTS_DIR),
            "--output", f"{name}_output.xml",
            "--log", f"{name}_log.html",
            "--report", f"{name}_report.html",
            str(suite_path),
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
    )
    return {
        "ok": completed.returncode == 0,
        "return_code": completed.returncode,
        "elapsed_seconds": round(time.time() - start, 2),
        "command": ["python", "-m", "robot", str(suite_path)],
        "output_excerpt": (completed.stdout or "")[-1500:],
    }


def run_scenario(name: str, steps: list[tuple[str, str]], tools: dict) -> dict:
    print(f"\n{'─' * 72}\nSCENARIO: {name}\n{'─' * 72}")
    store = LiveSessionStore()
    open_session = tools["open"](store)
    execute_step = tools["step"](store)
    get_session = tools["session"](store)
    inspect_state = tools["inspect"](store)
    close_session = tools["close"](store)

    tool_calls = 0
    failed_tool_calls = 0
    issues: list[dict] = []
    step_log: list[dict] = []

    session_id = open_session("stdio")["session"]["session_id"]
    tool_calls += 1
    print(f"[rf_open_session] session_id={session_id}")

    aborted = False
    for index, (intent, instruction) in enumerate(steps, start=1):
        start = time.time()
        result = execute_step(session_id, instruction)
        tool_calls += 1
        elapsed = round(time.time() - start, 3)
        ok = bool(result.get("ok"))
        step_log.append(
            {
                "index": index,
                "intent": intent,
                "instruction": instruction,
                "ok": ok,
                "elapsed_seconds": elapsed,
                "detail": result.get("detail", ""),
            }
        )
        print(f"  [{index:02d}] {'OK ' if ok else 'FAIL'} ({elapsed:>5.2f}s) {instruction[:58]}")
        if not ok:
            failed_tool_calls += 1
            error = result.get("error", {})
            dom = inspect_state(session_id, "dom")  # live snapshot to diagnose
            tool_calls += 1
            issues.append(
                {
                    "scenario": name,
                    "index": index,
                    "intent": intent,
                    "instruction": instruction,
                    "error_code": error.get("code"),
                    "error_message": error.get("message", "")[:300],
                    "dom_available": bool(dom.get("ok")),
                }
            )
            print(f"        -> {error.get('code')}: {error.get('message', '')[:120]}")
            aborted = True
            break

    session_state = get_session(session_id)
    tool_calls += 1
    record_snapshot = store.get_record(session_id)
    recorded_steps = list(record_snapshot.steps) if record_snapshot else []
    close_session(session_id)
    tool_calls += 1

    scenario_passed = not aborted
    suite_rel = None
    final_suite_result = {"ok": False, "reason": "scenario did not complete"}
    if scenario_passed and recorded_steps:
        suite_path = SUITE_DIR / f"saucedemo_{name.replace('-', '_')}_authored.robot"
        suite_path.write_text(
            build_final_suite(name, recorded_steps, record=record_snapshot), encoding="utf-8"
        )
        suite_rel = str(suite_path.relative_to(REPO_ROOT))
        print(f"[build suite] wrote {suite_rel} ({len(recorded_steps)} steps); running with robot...")
        final_suite_result = run_robot(name, suite_path)
        print(f"[build suite] runnable: {final_suite_result['ok']} ({final_suite_result['elapsed_seconds']}s)")

    return {
        "scenario": name,
        "total_steps": len(steps),
        "executed_steps": len(step_log),
        "passed_steps": sum(1 for s in step_log if s["ok"]),
        "failed_steps": sum(1 for s in step_log if not s["ok"]),
        "scenario_passed": scenario_passed,
        "tool_calls": tool_calls,
        "failed_tool_calls": failed_tool_calls,
        "failed_tool_call_rate": round(failed_tool_calls / tool_calls, 3) if tool_calls else 0.0,
        "total_step_seconds": round(sum(s["elapsed_seconds"] for s in step_log), 2),
        "recorded_session_steps": len(recorded_steps),
        "final_suite": suite_rel,
        "final_suite_runnable": bool(final_suite_result.get("ok")),
        "final_suite_run": final_suite_result,
        "issues": issues,
        "steps": step_log,
        "session_state": session_state.get("session", {}),
    }


def main() -> int:
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    print("=" * 72)
    print("rfmcp MCP-driven E2E — SauceDemo (live stepwise authoring + build suite)")
    print(f"Started: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 72)

    tools = {
        "open": build_open_session_tool,
        "step": build_execute_step_tool,
        "session": build_get_session_tool,
        "context": build_get_context_tool,
        "inspect": build_app_inspect_state_tool,
        "close": build_close_session_tool,
    }

    results = [run_scenario(name, steps, tools) for name, steps in SCENARIOS.items()]

    report = {
        "url": "https://www.saucedemo.com",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "surface": "mcp-live-session",
        "engine": "in-process Browser (Playwright)",
        "scenarios": results,
        "summary": {
            "scenarios": len(results),
            "scenarios_passed": sum(1 for r in results if r["scenario_passed"]),
            "suites_built_and_runnable": sum(1 for r in results if r["final_suite_runnable"]),
            "total_tool_calls": sum(r["tool_calls"] for r in results),
            "total_failed_tool_calls": sum(r["failed_tool_calls"] for r in results),
            "total_issues": sum(len(r["issues"]) for r in results),
            "total_step_seconds": round(sum(r["total_step_seconds"] for r in results), 2),
        },
    }
    report_path = RESULTS_DIR / "mcp_e2e_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    s = report["summary"]
    print("\n" + "=" * 72)
    print("AGGREGATE METRICS")
    print("=" * 72)
    for r in results:
        print(
            f"  {r['scenario']:<18} passed={r['scenario_passed']!s:<5} "
            f"steps={r['passed_steps']}/{r['total_steps']} "
            f"runnable={r['final_suite_runnable']!s:<5} "
            f"calls={r['tool_calls']} fails={r['failed_tool_calls']} issues={len(r['issues'])}"
        )
    print(
        f"\n  scenarios passed:          {s['scenarios_passed']}/{s['scenarios']}\n"
        f"  suites built + runnable:   {s['suites_built_and_runnable']}/{s['scenarios']}\n"
        f"  total MCP tool calls:      {s['total_tool_calls']}\n"
        f"  total failed tool calls:   {s['total_failed_tool_calls']}\n"
        f"  total issues collected:    {s['total_issues']}\n"
        f"  total step time:           {s['total_step_seconds']}s\n"
        f"\n  report: {report_path}"
    )

    all_ok = all(r["scenario_passed"] and r["final_suite_runnable"] for r in results)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
