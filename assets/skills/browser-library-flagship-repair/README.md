# Browser Library Flagship Repair

`skill_id`: `browser-library-flagship-repair`

This is the canonical host-agnostic repair workflow for the v1 Browser Library flagship scenario: a failing Robot Framework test that uses Browser keywords but omitted `Library    Browser`.

## Inputs

- A `.robot` test file that fails with a Browser keyword lookup error.
- The observed failure message.
- Optional live-state access during diagnosis.

## MCP Boundary

Use live-state MCP only while runtime context or application inspection adds value. These are host-level steps around the deterministic helper; the Python workflow definition records the boundary but does not call host MCP tools directly.

- `rf_open_session`
- `rf_get_context`
- `app_inspect_state`
- `rf_execute_step`
- `rf_close_session`

These tools help triage the failure, but they do not replace the deterministic repair proof.

## CLI Takeover

Deterministic CLI commands take over for the repair proof path:

1. `rfmcp repair-diagnostics <target.robot> --failure-message '<failure message>' --json`
2. `rfmcp repair-hints <target.robot> --failure-message '<failure message>' --json`
3. Apply `Library    Browser` under `*** Settings ***`.
4. `python -m robot --output NONE --report NONE --log NONE <target.robot>`
5. `rfmcp validate <target.robot> --json`

Use `rfmcp_skills.render_fallback_commands(...)` when you need executable shell commands rendered from the canonical examples.

## Expected Outcome

- Diagnostics identify the missing Browser library import.
- Hints distinguish curated, provider, official-docs, and inferred guidance.
- The deterministic repair step inserts `Library    Browser`.
- Baseline execution fails before the patch, and validation plus rerun proof confirm the original missing-import failure condition is cleared afterward.
