# Story 2.1: Expose a Bounded Live Repair Session Surface

Status: done

## Story

As an Automation Engineer,
I want a bounded live repair session surface,
so that I can step through a repair investigation without recreating runtime state on every action.

## Acceptance Criteria

1. **Given** the architecture reserves MCP for live-state needs only  
   **When** the live repair session story is implemented  
   **Then** the MCP package exposes only the allowlisted session and stepwise-repair tools over `stdio` and loopback-only HTTP  
   **And** session lifecycle, policy gating, and interrupted-step failures all use the shared structured error path  
   **And** stateless helpers such as grounding, scaffolding, and general generation are not registered as MCP tools.

2. **Given** a maintainer attempts to expand the repair surface later  
   **When** the boundary is reviewed  
   **Then** every added tool must be justified by a live-state need  
   **And** the docs make the MCP-versus-CLI decision boundary explicit.

## Tasks / Subtasks

- [x] Add the shared live-session runtime primitives in `rfmcp_core.runtime`. (AC: 1)
- [x] Add MCP policy and transport gating helpers for `stdio` and loopback-only HTTP. (AC: 1)
- [x] Implement the bounded MCP tool registry with only session lifecycle and stepwise repair tools. (AC: 1, 2)
- [x] Add server entrypoints and transport wiring that preserve the allowlist boundary. (AC: 1)
- [x] Document the MCP-versus-CLI boundary and the live-state justification for each MCP tool. (AC: 2)
- [x] Add tests covering allowlist enforcement, policy failures, interrupted-step errors, and transport defaults. (AC: 1, 2)

## Dev Notes

- Scope discipline matters more than feature breadth in this story. Do not add Robot context inspection, application snapshots, or stateless helpers here; those belong to later Epic 2 stories or Epic 3 CLI work.
- Keep the initial MCP user-facing tool count at five or fewer, consistent with the PRD assumption for the v1 live-state core.
- Reuse the shared `ErrorEnvelope`, `ProvenanceRecord`, and `Severity` contracts from `rfmcp_core.contracts`; do not invent MCP-only error payloads.
- Reuse the local policy defaults and capability checks added in Story 1.5. Attach-like behavior stays disabled by default, and HTTP exposure must remain loopback-only unless an explicit policy change is made.
- Align new files to the architecture skeleton:
  - `packages/rfmcp_core/src/rfmcp_core/runtime/session.py`
  - `packages/rfmcp_core/src/rfmcp_core/runtime/stepper.py`
  - `packages/rfmcp_mcp/src/rfmcp_mcp/server.py`
  - `packages/rfmcp_mcp/src/rfmcp_mcp/tools/_registry.py`
  - `packages/rfmcp_mcp/src/rfmcp_mcp/tools/rf_execute_step.py`
  - `packages/rfmcp_mcp/src/rfmcp_mcp/security/attach_policy.py`
  - `packages/rfmcp_mcp/src/rfmcp_mcp/transports/stdio.py`
  - `packages/rfmcp_mcp/src/rfmcp_mcp/transports/http.py`
- The bounded v1 allowlist for this story should stay focused on repair-session primitives only:
  - start/open live repair session
  - inspect live repair session status
  - execute one repair step within the active session
  - stop/close live repair session
- Error cases that must be exercised in tests:
  - policy denies HTTP or attach-style capability
  - session not found / session already closed
  - interrupted repair step returns shared structured failure output
  - non-allowlisted helper is absent from the registry
- Update contributor-facing docs so the MCP-vs-CLI boundary is explicit and maintainers can review future additions against a written rule rather than memory.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv lock`
- `uv run --group dev python scripts/export_json_schemas.py`
- `uv run --group dev python scripts/verify_schema_sync.py`
- `python3 scripts/verify_workspace_structure.py`
- `uv run --group dev python -m unittest discover -s tests -v`
- `uv run --group dev python - <<'PY' ... await build_server().list_tools() ...`
- `claude -p --dangerously-skip-permissions --model sonnet --no-session-persistence`
- `claude -p --dangerously-skip-permissions --model opus --no-session-persistence`

### Completion Notes List

- Added schema-backed live repair session and step result payloads to the shared contract layer and exported JSON Schemas for them.
- Added an in-memory live repair session store and stepper that preserve bounded session state and surface interrupted-step failures through the shared error envelope.
- Added MCP policy gating, loopback-only HTTP checks, an explicit four-tool allowlist, and FastMCP server/transport entrypoints that keep stateless helpers out of the MCP surface.
- Added written MCP-versus-CLI boundary documentation and tests covering allowlist enforcement, policy rejection, loopback-only HTTP, and shared structured failure outputs.
- Removed the unused `session_guard` skeleton during review hardening so the live repair boundary has one authoritative enforcement path instead of dead drift-prone helpers.
- Cleared external review on the final implementation state with Claude Sonnet and Claude Opus after applying the review findings.

### File List

- README.md
- _bmad-output/implementation-artifacts/2-1-expose-a-bounded-live-repair-session-surface.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- assets/schemas/repair-session.schema.json
- assets/schemas/repair-step-result.schema.json
- docs/mcp-live-repair-boundary.md
- packages/rfmcp_core/src/rfmcp_core/contracts/__init__.py
- packages/rfmcp_core/src/rfmcp_core/contracts/repair.py
- packages/rfmcp_core/src/rfmcp_core/models/__init__.py
- packages/rfmcp_core/src/rfmcp_core/models/payloads.py
- packages/rfmcp_core/src/rfmcp_core/runtime/__init__.py
- packages/rfmcp_core/src/rfmcp_core/runtime/session.py
- packages/rfmcp_core/src/rfmcp_core/runtime/stepper.py
- packages/rfmcp_mcp/pyproject.toml
- packages/rfmcp_mcp/src/rfmcp_mcp/security/attach_policy.py
- packages/rfmcp_mcp/src/rfmcp_mcp/server.py
- packages/rfmcp_mcp/src/rfmcp_mcp/tools/__init__.py
- packages/rfmcp_mcp/src/rfmcp_mcp/tools/_registry.py
- packages/rfmcp_mcp/src/rfmcp_mcp/tools/rf_close_session.py
- packages/rfmcp_mcp/src/rfmcp_mcp/tools/rf_execute_step.py
- packages/rfmcp_mcp/src/rfmcp_mcp/tools/rf_get_session.py
- packages/rfmcp_mcp/src/rfmcp_mcp/tools/rf_open_session.py
- packages/rfmcp_mcp/src/rfmcp_mcp/transports/http.py
- packages/rfmcp_mcp/src/rfmcp_mcp/transports/stdio.py
- pyproject.toml
- scripts/export_json_schemas.py
- tests/test_mcp_live_repair_surface.py
- uv.lock

## Change Log

- 2026-05-25: Created Story 2.1 implementation brief from Epic 2 planning artifacts and architecture constraints.
- 2026-05-25: Implemented the bounded live repair session surface, transport/policy gates, schemas, documentation, and tests; promoted story to review.
- 2026-05-25: Applied Sonnet and Opus review fixes for unsupported transport handling, retryability semantics, HTTP startup failure envelopes, MCP-level interruption coverage, policy-load failure handling, and story artifact accuracy.
- 2026-05-25: Completed Story 2.1 after Sonnet and Opus returned clean final review outcomes and the full local verification suite passed.
