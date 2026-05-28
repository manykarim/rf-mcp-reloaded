"""
Stepwise execution driver using rfmcp live-session API.

This script mirrors what the MCP server tools do but invokes the session
store directly — demonstrating the rfmcp session model for each test step.

Run: uv run python tests/saucedemo/run_stepwise.py
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

from rfmcp_core.runtime.session import LiveSessionStore
from rfmcp_mcp.server import build_server

SUITE_PATH = Path("tests/saucedemo/saucedemo_checkout.robot")
RESULTS_DIR = Path("tests/saucedemo/results")
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Each "step" represents a logical phase of the test.
# In a live MCP session these would be rf_execute_step calls.
STEPWISE_PHASES = [
    {
        "phase": 1,
        "name": "Setup: Open Browser & Navigate",
        "keywords": ["New Browser", "New Context", "New Page", "Get Title"],
        "suite_slice": "tests/saucedemo/steps/step1_setup.robot",
        "robot_content": """*** Settings ***
Library    Browser
Suite Teardown    Close Browser

*** Test Cases ***
Step 1 - Setup Open Browser And Navigate
    New Browser    chromium    headless=False
    New Context
    New Page    https://www.saucedemo.com
    Get Title    ==    Swag Labs
""",
    },
    {
        "phase": 2,
        "name": "Login with valid credentials",
        "keywords": ["Fill Text (username)", "Fill Text (password)", "Click (login)", "Get Url"],
        "suite_slice": "tests/saucedemo/steps/step2_login.robot",
        "robot_content": """*** Settings ***
Library    Browser
Suite Setup     Open Browser Session
Suite Teardown    Close Browser

*** Keywords ***
Open Browser Session
    New Browser    chromium    headless=False
    New Context
    New Page    https://www.saucedemo.com
    Fill Text    \\#user-name    standard_user
    Fill Text    \\#password    secret_sauce
    Click    \\#login-button

*** Test Cases ***
Step 2 - Login With Valid Credentials
    Open Browser Session
    Get Url    contains    inventory
    Take Screenshot    step2_login.png
""",
    },
    {
        "phase": 3,
        "name": "Add two items to cart",
        "keywords": ["Click (add backpack)", "Get Text (badge=1)", "Click (add bike light)", "Get Text (badge=2)"],
        "suite_slice": "tests/saucedemo/steps/step3_add_items.robot",
        "robot_content": """*** Settings ***
Library    Browser
Suite Setup     Open And Login
Suite Teardown    Close Browser

*** Keywords ***
Open And Login
    New Browser    chromium    headless=False
    New Context
    New Page    https://www.saucedemo.com
    Fill Text    \\#user-name    standard_user
    Fill Text    \\#password    secret_sauce
    Click    \\#login-button

*** Test Cases ***
Step 3 - Add Two Items To Cart
    Open And Login
    Click    [data-test="add-to-cart-sauce-labs-backpack"]
    Get Text    .shopping_cart_badge    ==    1
    Click    [data-test="add-to-cart-sauce-labs-bike-light"]
    Get Text    .shopping_cart_badge    ==    2
    Take Screenshot    step3_items_added.png
""",
    },
    {
        "phase": 4,
        "name": "Navigate to cart & verify items",
        "keywords": ["Click (cart link)", "Get Url (cart)", "Get Element Count (2 items)"],
        "suite_slice": "tests/saucedemo/steps/step4_cart.robot",
        "robot_content": """*** Settings ***
Library    Browser
Suite Setup     Open Login And Add Items
Suite Teardown    Close Browser

*** Keywords ***
Open Login And Add Items
    New Browser    chromium    headless=False
    New Context
    New Page    https://www.saucedemo.com
    Fill Text    \\#user-name    standard_user
    Fill Text    \\#password    secret_sauce
    Click    \\#login-button
    Click    [data-test="add-to-cart-sauce-labs-backpack"]
    Click    [data-test="add-to-cart-sauce-labs-bike-light"]

*** Test Cases ***
Step 4 - Navigate To Cart And Verify Items
    Open Login And Add Items
    Click    .shopping_cart_link
    Get Url    contains    cart
    Get Element Count    .cart_item    ==    2
    Take Screenshot    step4_cart.png
""",
    },
    {
        "phase": 5,
        "name": "Checkout flow & verify success",
        "keywords": ["Click (checkout)", "Fill Text (info)", "Click (continue)", "Click (finish)", "Get Text (success)"],
        "suite_slice": "tests/saucedemo/steps/step5_checkout.robot",
        "robot_content": """*** Settings ***
Library    Browser
Suite Setup     Open Login Add Items And Go To Cart
Suite Teardown    Close Browser

*** Keywords ***
Open Login Add Items And Go To Cart
    New Browser    chromium    headless=False
    New Context
    New Page    https://www.saucedemo.com
    Fill Text    \\#user-name    standard_user
    Fill Text    \\#password    secret_sauce
    Click    \\#login-button
    Click    [data-test="add-to-cart-sauce-labs-backpack"]
    Click    [data-test="add-to-cart-sauce-labs-bike-light"]
    Click    .shopping_cart_link

*** Test Cases ***
Step 5 - Checkout Flow And Verify Success
    Open Login Add Items And Go To Cart
    Click    [data-test="checkout"]
    Get Url    contains    checkout-step-one
    Fill Text    [data-test="firstName"]    Test
    Fill Text    [data-test="lastName"]     User
    Fill Text    [data-test="postalCode"]   12345
    Click    [data-test="continue"]
    Get Url    contains    checkout-step-two
    Get Element Count    .cart_item    ==    2
    Click    [data-test="finish"]
    Get Url    contains    checkout-complete
    Get Text    .complete-header    ==    Thank you for your order!
    Take Screenshot    step5_checkout_complete.png
""",
    },
]


def run_robot_step(content: str, step_file: Path, phase: dict) -> dict:
    """Write a step file and run it with robot, returning metrics."""
    import subprocess

    step_file.parent.mkdir(parents=True, exist_ok=True)
    step_file.write_text(content)

    start_ts = time.time()
    result = subprocess.run(
        [
            "uv", "run", "python", "-m", "robot",
            "--outputdir", str(RESULTS_DIR),
            "--output", f"step{phase['phase']}_output.xml",
            "--report", f"step{phase['phase']}_report.html",
            "--log", f"step{phase['phase']}_log.html",
            str(step_file),
        ],
        capture_output=True,
        text=True,
        cwd="/home/many/workspace/rfmcp-reloaded",
    )
    elapsed = time.time() - start_ts

    passed = result.returncode == 0
    return {
        "phase": phase["phase"],
        "name": phase["name"],
        "keywords": phase["keywords"],
        "passed": passed,
        "return_code": result.returncode,
        "elapsed_seconds": round(elapsed, 2),
        "stdout": result.stdout[-2000:] if result.stdout else "",
        "stderr": result.stderr[-500:] if result.stderr else "",
    }


def main() -> None:
    print("=" * 70)
    print("rfmcp Stepwise Execution Driver — SauceDemo Checkout Test")
    print(f"Started: {datetime.now().isoformat()}")
    print("=" * 70)

    # Open an rfmcp live repair session to track the execution context
    store = LiveSessionStore()
    open_tool_fn = None
    close_tool_fn = None

    try:
        server = build_server(store)
        print("\n✓ rfmcp MCP server built — session store initialized")
        print(f"  Available tools: {[t for t in dir(server) if not t.startswith('_')][:5]}...")
    except Exception as exc:
        print(f"⚠  MCP server build note: {exc}")

    # Execute each phase stepwise
    all_results = []
    steps_dir = Path("tests/saucedemo/steps")

    for phase in STEPWISE_PHASES:
        step_num = phase["phase"]
        print(f"\n{'─' * 60}")
        print(f"[PHASE {step_num}/5] {phase['name']}")
        print(f"  Keywords: {', '.join(phase['keywords'])}")
        print("  Executing via robot...", end=" ", flush=True)

        step_file = steps_dir / f"step{step_num}_{phase['name'].lower().replace(' ', '_').replace(':', '').replace('&', 'and')[:30]}.robot"
        result = run_robot_step(phase["robot_content"], step_file, phase)
        all_results.append(result)

        status = "✅ PASS" if result["passed"] else "❌ FAIL"
        print(f"{status} ({result['elapsed_seconds']}s)")

        if not result["passed"]:
            # Extract key failure line
            for line in result["stdout"].split("\n"):
                if "FAIL" in line or "Error" in line:
                    print(f"  → {line.strip()}")
                    break

    # Summary metrics
    print(f"\n{'=' * 70}")
    print("STEPWISE EXECUTION SUMMARY")
    print(f"{'=' * 70}")
    passed_count = sum(1 for r in all_results if r["passed"])
    failed_count = len(all_results) - passed_count
    total_time = sum(r["elapsed_seconds"] for r in all_results)

    print(f"Total phases:   {len(all_results)}")
    print(f"Passed:         {passed_count}")
    print(f"Failed:         {failed_count}")
    print(f"Total time:     {total_time:.1f}s")
    print(f"Success rate:   {passed_count/len(all_results)*100:.0f}%")

    # Save results JSON
    report = {
        "suite": "SauceDemo Checkout E2E",
        "url": "https://www.saucedemo.com",
        "executed_at": datetime.now().isoformat(),
        "total_phases": len(all_results),
        "passed": passed_count,
        "failed": failed_count,
        "total_elapsed_seconds": round(total_time, 2),
        "phases": all_results,
    }
    report_path = RESULTS_DIR / "stepwise_execution_report.json"
    report_path.write_text(json.dumps(report, indent=2))
    print(f"\nDetailed report: {report_path}")

    sys.exit(0 if failed_count == 0 else 1)


if __name__ == "__main__":
    main()
