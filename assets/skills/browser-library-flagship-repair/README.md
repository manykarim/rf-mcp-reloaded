# Browser Library Flagship Repair

`skill_id`: `browser-library-flagship-repair`

This is the canonical host-agnostic repair workflow for the v1 Browser Library flagship scenario: a failing Robot Framework test that uses Browser keywords but omitted `Library    Browser`.

## Inputs

- A `.robot` test file that fails with a Browser keyword lookup error.
- The observed failure message.
- Optional live-state access during diagnosis.

## MCP Boundary

Use live-state MCP only while runtime context or application inspection adds value. These are host-level steps around the deterministic helper; the Python workflow definition records the boundary but does not call host MCP tools directly.

- `rf_session` (action: open|get|close)
- `rf_context` (action: get|set)
- `app_inspect_state`
- `rf_execute_step`
- `rf_manage_session` (imports, declared variables, setup/teardown, tags)

These tools help triage the failure, but they do not replace the deterministic repair proof.

### Live-state diagnostic order

When the host wires up an MCP session with Browser Library loaded, prefer
`app_inspect_state` snapshot kinds in this order (smallest, most semantic first):

1. **`aria`** — first read for *"what's on the page?"*. ~24× smaller than raw DOM
   on a typical page (~20 KB vs ~500 KB) and includes Shadow DOM + iframes via
   Playwright. Default selector `css=html` returns the whole tree.
2. **`dom_selector`** (`selector="..."`) — when ARIA's role/label isn't enough and
   you need the literal HTML of one subtree.
3. **`dom`** with `include_shadow_dom=True` — full serialized DOM with open shadow
   roots inlined as declarative `<template shadowrootmode="open">`. Largest
   payload; use only when 1 and 2 miss.
4. **`console_log`** — when the symptom looks like a JS exception, not a missing
   element.
5. **`screenshot`** — human-readable proof artifact for retrospectives; never
   inlined (binary), read `manifest.path` directly.

Keep `return_inline=False` (the default) on hot polling loops — the manifest
summary alone is usually enough to decide the next step.

For per-kind requirements (library prerequisites, selector rules, summary
fields, inline caps), see the `app_inspect_state` docstring, which is the
authoritative reference.

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
