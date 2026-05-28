# Browser Library Flagship Repair Workflow

This document is the operator-facing reference for the Epic 2 flagship Browser Library repair scenario.

## Goal

Repair a failing Robot Framework test that uses Browser Library keywords without a Browser import, while keeping live-state MCP usage bounded and finishing on deterministic CLI proof.

## Where MCP Is Used

MCP is bounded to live-state triage only. This document describes the host-level workflow boundary; the pure Python flagship helper records that boundary but does not invoke host MCP tools itself.

- `rf_session` (action `open`) to create the live repair boundary
- `rf_context` (action `get`) to inspect runtime variables and imported libraries
- `app_inspect_state` to capture approved live application snapshots
- `rf_execute_step` to preserve stepwise live repair context
- `rf_session` (action `close`) to terminate the session explicitly

If live-state access is unavailable, skip this phase and continue entirely on the CLI path.

## Where CLI Takes Over

The deterministic proof path is always CLI-based:

1. Diagnose the failure:

   `rfmcp repair-diagnostics <target.robot> --failure-message '<failure message>' --json`

2. Resolve provenance-aware hints:

   `rfmcp repair-hints <target.robot> --failure-message '<failure message>' --json`

3. Apply the canonical Browser import repair:

   Add `Library    Browser` under `*** Settings ***`.

4. Prove the unrepaired file actually fails:

   `python -m robot --output NONE --report NONE --log NONE <target.robot>`

5. Re-verify deterministically after the patch:

   `rfmcp validate <target.robot> --json`
   `python -m robot --output NONE --report NONE --log NONE <target.robot>`

## Proof Expectations

- The failing test is shaped into structured diagnostics rather than raw logs.
- The hint payload distinguishes curated guidance, provider guidance, official docs pointers, and inferred fallback suggestions.
- The repair step is explicit and attributable.
- The benchmark log captures both the baseline failure and the post-repair rerun success as local JSONL workflow events.
