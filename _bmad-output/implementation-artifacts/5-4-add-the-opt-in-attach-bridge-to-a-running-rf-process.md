# Story 5.4: Add the Opt-In Attach Bridge to a Running RF Process

Status: done

## Story

As an Automation Engineer,
I want to attach a live session to an already-running Robot Framework process,
so that I can inspect and step against a live application I already have open.

## Acceptance Criteria

1. **Given** attach is enabled by explicit local policy and a session is opened with `attach_requested=True`
   **When** the execute, context, and inspect tools run
   **Then** they route to the attached external Robot Framework process over a loopback-only, ephemeral-credential bridge
   **And** attach stays disabled by default, is visible to the operator, and can be stopped explicitly.

2. **Given** an attach bridge target
   **When** the bridge host is not a loopback address
   **Then** opening the session is rejected with a structured error (no off-host attach).

3. **Given** the attached process is unreachable
   **When** a tool routes to it
   **Then** a structured error is returned (not a crash), and no new MCP tools are added beyond the existing allowlist.

## Tasks / Subtasks

- [x] **Task 1: Attach engine (bridge client)** (AC: 1, 3)
  - [x] Add `packages/rfmcp_core/src/rfmcp_core/runtime/attach.py` with `AttachExecutionContext` implementing the same surface the stepper/context/snapshot use: `execute(instruction) -> StepExecution`, `get_variables(keys)`, `set_variable(name, value)`, `imported_libraries()`, `query(keyword, args)`, `close()`, and a `started` property.
  - [x] Transport: stdlib `urllib.request` POST of JSON to `http://{host}:{port}/{path}` with an `Authorization: Bearer {token}` header (no new deps). Loopback-only; short timeout. Connection/HTTP errors → `StepExecution(ok=False, error_type="AttachUnavailable", ...)` for `execute`, and raised for `query` (snapshot maps to `snapshot-unavailable`).
  - [x] Map bridge `run_keyword` response → `StepExecution` (ok/keyword/return_value/assigned/error); `${x} =` parsed with the shared `_parse_instruction`.
- [x] **Task 2: Session wiring** (AC: 1)
  - [x] Add `attach_host`, `attach_port`, `attach_token` to `LiveSessionRecord`. `open_session` accepts attach params and generates an ephemeral `attach_token` (uuid4) when `attach_requested`.
  - [x] `get_or_create_engine`: when `record.attach_requested`, build an `AttachExecutionContext` (loopback host/port/token) instead of the in-process `LiveExecutionContext`. Keep the closed-session and `engine_factory` (test) branches.
- [x] **Task 3: Tool + policy gating** (AC: 1, 2)
  - [x] `rf_open_session` gains `attach_host`/`attach_port`. Keep `validate_transport_policy(..., attach_requested=...)` (default-deny). When `attach_requested`, reject a non-loopback `attach_host` with a structured `policy-attach-loopback-only` error before opening.
  - [x] No new tools; allowlist + `MAX_USER_FACING_TOOLS` unchanged.
- [x] **Task 4: Tests** (AC: 1, 2, 3)
  - [x] Default-deny: `attach_requested=True` with default policy → `policy-attach-disabled` (existing coverage retained).
  - [x] Policy-enabled attach + loopback host → `open_session` succeeds and the engine is an `AttachExecutionContext`.
  - [x] Non-loopback attach host → `policy-attach-loopback-only`.
  - [x] Routing: monkeypatch `AttachExecutionContext._post` to return canned bridge responses → `rf_execute_step`/`rf_get_context`/`rf_set_context`/`app_inspect_state` route to the bridge and surface its data.
  - [x] Unreachable bridge (closed loopback port) → `rf_execute_step` returns a structured failure (not a crash).
- [x] **Task 5: Verification gate**
  - [x] `verify_schema_sync.py`; full `unittest` suite green.

## Dev Notes

- Policy gating already exists: `validate_transport_policy(attach_requested=True)` → `policy-attach-disabled` unless `PolicyCapability.ATTACH` is enabled (`rfmcp_mcp/security/attach_policy.py`). 5.4 only adds the bridge that activates once attach is allowed.
- Keep the bridge client in `rfmcp_core.runtime` (it is a runtime engine variant), NOT in `rfmcp_mcp`, to preserve the core←mcp layering (core must not import mcp). Put a small loopback check in `attach.py` (mirror of `_is_loopback_host`).
- Bridge protocol mirrors the reference `manykarim/rf-mcp` `ExternalRFClient` (loopback `127.0.0.1:7317`, token, `_post(path, payload)`, `run_keyword`, `get_variables`, `set_variable`). The external RF-side listener is the operator's responsibility (out of scope); this story ships the MCP-side client + wiring.
- The attach engine must satisfy the same duck-typed interface the stepper (`execute`), context (`get_variables`/`set_variable`/`imported_libraries`), and snapshot (`imported_libraries`/`get_variables`/`query`) call — so no changes are needed in those modules.
- No external RF listener exists in this environment, so the live round-trip is proven with a monkeypatched `_post` (routing) + a real closed-port connection (unreachable handling).

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 5 / Story 5.4]
- [Source: _bmad-output/planning-artifacts/architecture.md#Live Execution Engine for the MCP Core]
- [Source: _bmad-output/planning-artifacts/prds/prd-rfmcp-reloaded-2026-05-23/prd.md#6.1 Attach-Style Safety]
- [Source: packages/rfmcp_mcp/src/rfmcp_mcp/security/attach_policy.py]
- Reference: `manykarim/rf-mcp` `src/robotmcp/components/execution/external_rf_client.py`.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7 (1M context)

### Debug Log References

- `uv run --group dev python -m unittest discover -s tests` → Ran 115 tests, OK.
- `uv run --group dev python scripts/verify_schema_sync.py` → Schema sync OK.
- `python3 scripts/verify_workspace_structure.py` → OK.

### Completion Notes List

- Added `runtime/attach.py` `AttachExecutionContext` — an engine variant that proxies `execute`/`get_variables`/`set_variable`/`imported_libraries`/`query`/`close` to an external RF process via stdlib `urllib` JSON POST (loopback, `Authorization: Bearer <ephemeral token>`, 5s timeout). Connection errors → `AttachUnavailable` `StepExecution` (execute) or raise (query). Reuses `_parse_instruction`/`_json_safe` from the in-process engine; same duck-typed interface so stepper/context/snapshot are unchanged.
- `LiveSessionRecord` gained `attach_host`/`attach_port`/`attach_token`; `open_session` generates an ephemeral `attach_token` (uuid4) when `attach_requested`; `get_or_create_engine` builds an `AttachExecutionContext` for attach sessions (else in-process), preserving the closed-session guard and `engine_factory` test seam.
- `rf_open_session` gained `attach_host`/`attach_port` and rejects a non-loopback attach host with `policy-attach-loopback-only` (after the existing default-deny `policy-attach-disabled`). No new tools; allowlist unchanged.
- Attach remains disabled by default (policy `PolicyCapability.ATTACH`), loopback-only, ephemeral-credentialed, and closable.
- Honest scope: the external RF-side listener is the operator's responsibility (the reference `manykarim/rf-mcp` ships one). This story implements the MCP-side client + wiring; routing is proven with a monkeypatched `_post`, unreachable handling with a real closed loopback port.

### File List

- packages/rfmcp_core/src/rfmcp_core/runtime/attach.py (new)
- packages/rfmcp_core/src/rfmcp_core/runtime/session.py
- packages/rfmcp_mcp/src/rfmcp_mcp/tools/rf_open_session.py
- tests/test_mcp_live_session_surface.py

## Change Log

- 2026-05-27: Implemented Story 5.4 — opt-in attach bridge (`AttachExecutionContext`) routing live-session ops to an external loopback RF process with ephemeral credentials; session wiring + `rf_open_session` loopback gating; attach stays default-off. Full suite green (115 tests). Promoted to review.
- 2026-05-27: Applied code-review findings (claude/sonnet): the ephemeral `attach_token` (plus `attach_host`/`attach_port`) is now surfaced in `SessionSummary` so the operator can configure their listener; `_post` brackets IPv6 literals; `set_variable`/`query` wrap network errors as descriptive `RuntimeError`s; `set_runtime_context` maps a post-validation write failure to a new `context-write-failed` code (not a misleading `invalid-context-key`); removed the dead `is_loopback_host` from `attach.py`; routing test extended to prove `set_context` + `app_inspect_state` + `get_libraries` go through the bridge with hard assertions. Schemas regenerated; full suite green (115 tests). Completed Story 5.4.

## Senior Developer Review (AI)

**Reviewers:** `claude` CLI (sonnet) — completed (7 findings); `kilo` CLI (minimax-m2.7) — timed out with no output (provider contention with an unrelated concurrent kilo job). Finalized on the claude review.

### claude/sonnet — outcome: Changes Requested (all resolved)

- [x] High — ephemeral token was server-generated but never shared, so the listener couldn't validate it → `SessionSummary` now returns `attach_token`/`attach_host`/`attach_port` for the operator to configure the listener.
- [x] Med — attach `set_variable` network error surfaced as `invalid-context-key` → `set_variable` raises a descriptive `RuntimeError`, and `set_runtime_context` maps post-validation write failures to `context-write-failed` (retryable).
- [x] Med — IPv6 loopback (`::1`) produced a malformed URL → `_post` brackets IPv6 literals.
- [x] Med — routing test didn't cover `set_context`/`app_inspect_state` → extended with `set_variable`/`get_libraries` assertions and hard equality on the bridge variables.
- [x] Low — dead `is_loopback_host` in `attach.py` diverging from the policy version → removed.
- [x] Low — `query` leaked raw urllib errors → wraps them as a descriptive `RuntimeError`.
- [x] Low — routing assertion too weak → now asserts `get_variables` in calls + exact bridge variable dict.

Clean areas confirmed by claude: default-deny ordering correct; gate sequence has no `None`/non-loopback slip-through; **core←mcp layering preserved** (attach imports only `rfmcp_core`; session's engine imports are deferred); `close_session` null-clears engine inside the lock then closes outside; CLOSED-session guard consistent; duck-typed interface complete; per-session token ephemerality correct.
