# Story 2.2: Add Robot Framework Context Access and Approved Inspection Snapshots

Status: done

## Story

As an Automation Engineer,
I want explicit Robot Framework context access and approved inspection snapshots,
so that a repair session can retrieve the evidence needed for diagnosis without broadening the MCP surface arbitrarily.

## Acceptance Criteria

1. **Given** the bounded repair session surface exists  
   **When** context and inspection support is implemented  
   **Then** the runtime layer supports Robot Framework context get/set operations plus approved application inspection snapshots such as DOM, accessibility, screenshots, or last API response where policy allows  
   **And** those capabilities remain explicitly bounded to the allowlisted MCP tools.

2. **Given** a requested snapshot or context action exceeds local policy or session capabilities  
   **When** the request is evaluated  
   **Then** the call is denied through the shared structured error path  
   **And** the denial preserves provenance and the next safe action for the operator or skill.

## Tasks / Subtasks

- [x] Add shared runtime models and services for Robot Framework context access and approved inspection snapshots. (AC: 1, 2)
- [x] Add explicit policy and session-capability gating for snapshot capture and context mutation. (AC: 2)
- [x] Extend the MCP allowlist with bounded context and inspection tools only. (AC: 1, 2)
- [x] Keep inspection outputs attributable and machine-usable without widening the MCP boundary. (AC: 1, 2)
- [x] Add tests for allowed context access, approved snapshots, policy denials, and session-capability denials. (AC: 1, 2)

## Dev Notes

- Keep this story inside the existing live repair surface. Do not add general library lookup, generation helpers, or broader debugging utilities.
- The allowed v1 additions here map to the architecture skeleton and PRD consequences:
  - `rf_get_context`
  - `rf_set_context`
  - `app_inspect_state`
- Approved snapshot categories are explicitly bounded: DOM, accessibility snapshot, screenshot, last API response, and current app context where a live repair session already exists.
- Any denial must return the shared `ErrorEnvelope` with observed provenance and an actionable next step. Raw exceptions or ad hoc dictionaries are not acceptable.
- Attach-style sensitivity still matters in this story even without opening a broader attach surface. Snapshot and context access should remain local-only, session-bound, and capability-checked.
- Prefer schema-backed payloads for context and snapshot results so later repair diagnostics and hinting work can consume them without translation drift.
- Use the existing `LiveRepairSessionStore` boundary rather than inventing a second session system. If session-scoped capability data is needed, extend the existing runtime record carefully.
- Keep MCP tool count within the story’s bounded live-state scope. Every added tool must be justified by runtime-context or approved-inspection need.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run --group dev python scripts/export_json_schemas.py`
- `uv run --group dev python scripts/verify_schema_sync.py`
- `uv run --group dev python -m unittest discover -s tests -v`
- `uv run --group dev python -m unittest tests.test_mcp_live_repair_surface -v`
- `python3 -m compileall packages/rfmcp_core/src/rfmcp_core packages/rfmcp_mcp/src/rfmcp_mcp tests`

### Completion Notes List

- Added schema-backed runtime context and inspection snapshot payloads to the shared contract layer and exported committed JSON Schemas for them.
- Extended the live repair session runtime record with bounded Robot Framework context state and approved snapshot capability metadata instead of introducing a second session system.
- Added bounded MCP tools for `rf_get_context`, `rf_set_context`, and `app_inspect_state`, plus structured denials for local-policy and session-capability violations.
- Hardened the MCP tool boundary so unexpected exceptions, invalid context keys, and policy-load failures all stay on the shared structured error path without mutating session state prematurely.
- Updated inspection snapshots to be explicitly synthetic, attributable, and session-derived so repair agents can distinguish placeholders from real application evidence.
- Updated the live repair boundary documentation and local policy defaults so context mutation and snapshot capture remain explicit, local, and machine-readable.
- Multiple 300-second Claude Sonnet reviews were used to drive fixes; the final 300-second Claude Opus review returned `PASS`.

### File List

- _bmad-output/implementation-artifacts/2-2-add-robot-framework-context-access-and-approved-inspection-snapshots.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- assets/policy/local-defaults.json
- assets/schemas/inspection-snapshot-result.schema.json
- assets/schemas/robot-context-mutation-result.schema.json
- assets/schemas/robot-context-view.schema.json
- docs/mcp-live-repair-boundary.md
- packages/rfmcp_core/src/rfmcp_core/contracts/__init__.py
- packages/rfmcp_core/src/rfmcp_core/contracts/runtime.py
- packages/rfmcp_core/src/rfmcp_core/models/__init__.py
- packages/rfmcp_core/src/rfmcp_core/models/payloads.py
- packages/rfmcp_core/src/rfmcp_core/models/policy.py
- packages/rfmcp_core/src/rfmcp_core/policy/capabilities.py
- packages/rfmcp_core/src/rfmcp_core/policy/enforcement.py
- packages/rfmcp_core/src/rfmcp_core/runtime/__init__.py
- packages/rfmcp_core/src/rfmcp_core/runtime/context.py
- packages/rfmcp_core/src/rfmcp_core/runtime/session.py
- packages/rfmcp_core/src/rfmcp_core/runtime/snapshot.py
- packages/rfmcp_mcp/src/rfmcp_mcp/tools/_registry.py
- packages/rfmcp_mcp/src/rfmcp_mcp/tools/app_inspect_state.py
- packages/rfmcp_mcp/src/rfmcp_mcp/tools/rf_get_context.py
- packages/rfmcp_mcp/src/rfmcp_mcp/tools/rf_set_context.py
- scripts/export_json_schemas.py
- tests/test_mcp_live_repair_surface.py

## Change Log

- 2026-05-25: Created Story 2.2 implementation brief from Epic 2 planning artifacts and runtime inspection constraints.
- 2026-05-25: Implemented bounded runtime context access, approved inspection snapshots, policy/session gating, and schema-backed tests; promoted story to review.
- 2026-05-25: Applied Sonnet-driven review fixes for contract drift, structured error handling, acceptance coverage, invalid-key mutation safety, and attributable synthetic snapshots; final Claude Opus review passed and story was marked done.
