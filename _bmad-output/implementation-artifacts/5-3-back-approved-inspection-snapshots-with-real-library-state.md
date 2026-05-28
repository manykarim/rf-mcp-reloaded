# Story 5.3: Back Approved Inspection Snapshots With Real Library State

Status: done

## Story

As an Automation Engineer,
I want `app_inspect_state` to capture real application state from the live loaded libraries,
so that repair decisions use the actual app instead of synthetic fixtures.

## Acceptance Criteria

1. **Given** a live session whose loaded libraries can provide a snapshot kind
   **When** `app_inspect_state` is requested for an approved kind
   **Then** the snapshot is captured from the real library instance/keyword with provenance `OBSERVED`
   **And** the synthetic `repair-session-fixture` payloads are removed.

2. **Given** a snapshot kind no loaded library can provide (e.g. `dom` with no browser open)
   **When** `app_inspect_state` is requested
   **Then** a structured `snapshot-unavailable` error is returned (retryable, `OBSERVED`), not a fabricated payload.

3. **Given** policy and per-session capability gating
   **When** snapshots are requested
   **Then** the existing `policy-inspection-disabled`, `session-snapshot-disabled`, `unsupported-snapshot-kind`, `session-not-found`, and `session-not-open` paths are preserved.

## Tasks / Subtasks

- [x] **Task 1: Add a non-recording keyword query on the engine** (AC: 1, 2)
  - [x] `LiveExecutionContext.query(keyword, args=None) -> Any`: runs a keyword via the live runner (real RF, args resolved) and returns its value WITHOUT recording a step; raises on not-found/failure. Reuses `_run_keyword` under the lock + stream suppression.
- [x] **Task 2: Add provenance to the snapshot contract** (AC: 1)
  - [x] Add `provenance: ProvenanceRecord` to `InspectionSnapshotResult` (`models/payloads.py`); regenerate `inspection-snapshot-result.schema.json`.
- [x] **Task 3: Rewrite `capture_inspection_snapshot` to source real state** (AC: 1, 2, 3)
  - [x] Keep gating order: `unsupported-snapshot-kind` → policy load/`policy-inspection-disabled` → `session-not-found`/`session-not-open` → `session-snapshot-disabled`.
  - [x] `app_context`: build a real payload from the live engine (`imported_libraries()`, variable names from `get_variables()`), provenance `OBSERVED`, source `live-session`. Always available for an open/interrupted session.
  - [x] `dom`: try `Get Page Source` (Browser) then `Get Source` (Selenium) via `engine.query`. `screenshot`: try `Take Screenshot`. First success → `InspectionSnapshotResult(payload={"keyword": kw, "value": _json_safe(val)}, provenance=OBSERVED source=<keyword>)`.
  - [x] `accessibility` / `last_api_response`: no first-class live keyword in v1 → fall through to `snapshot-unavailable`.
  - [x] When no candidate keyword resolves/succeeds → `snapshot-unavailable` (retryable, `OBSERVED` source `live-execution`, `details` includes attempted keywords + last error).
  - [x] Remove `_synthetic_snapshot_payload`.
- [x] **Task 4: Tests** (AC: 1, 2, 3)
  - [x] Rewrite `test_approved_inspection_snapshots_and_denials_are_structured`: `app_context` → ok with real `loaded_libraries` (incl. `BuiltIn`) and `provenance.kind == observed`; `dom`/`screenshot` (no browser loaded) → `snapshot-unavailable`; keep `unsupported-snapshot-kind`, `session-not-found`, `session-snapshot-disabled`, `policy-inspection-disabled`, `session-not-open` assertions (note: an allowed-kind that has no live source now returns `snapshot-unavailable`, not a payload).
  - [x] Update the interrupted-session test to request `app_context` (works against the `_InterruptEngine` double) and add `query` to the double.
- [x] **Task 5: Verification gate**
  - [x] Export schemas + `verify_schema_sync.py`; full `unittest` suite green.

## Dev Notes

- Environment reality (probed): `Browser` is importable but needs Playwright/node + an open page to yield DOM/screenshots; `SeleniumLibrary`/`RequestsLibrary` are not installed. So in CI/this env `dom`/`screenshot` deterministically return `snapshot-unavailable` (no capable library loaded in a default session), and `app_context` returns real data. This is the honest, testable behavior.
- A default session loads `BuiltIn`, `Collections` only (see `LiveSessionRecord.libraries`); browser/selenium libraries are not auto-imported, so live DOM requires a session that imported them and drove a page — out of scope to fully exercise here, but the real code path is implemented and used.
- `InspectionSnapshotResult` currently has no provenance field; adding one is a deliberate public-surface change consistent with the `OBSERVED`/`ErrorEnvelope` provenance model (pre-v1, cheapest now).
- Do not change `app_inspect_state` tool wiring or the allowlist; only the capture implementation + contract.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 5 / Story 5.3]
- [Source: _bmad-output/planning-artifacts/prds/prd-rfmcp-reloaded-2026-05-23/prd.md#FR-2]
- [Source: packages/rfmcp_core/src/rfmcp_core/runtime/snapshot.py] (current synthetic impl)
- [Source: packages/rfmcp_core/src/rfmcp_core/runtime/execution.py] (engine)

## Dev Agent Record

### Agent Model Used

claude-opus-4-7 (1M context)

### Debug Log References

- `uv run --group dev python scripts/export_json_schemas.py` → 18 schemas (inspection-snapshot-result now carries `provenance`).
- `uv run --group dev python scripts/verify_schema_sync.py` → Schema sync OK.
- `uv run --group dev python -m unittest discover -s tests` → Ran 111 tests, OK.

### Completion Notes List

- Added `LiveExecutionContext.query(keyword, args)` — runs a keyword for its value via the live runner without recording a step (used for snapshot capture).
- Added `provenance: ProvenanceRecord` to `InspectionSnapshotResult`; regenerated the schema.
- Rewrote `capture_inspection_snapshot`: gating order preserved; `app_context` returns real live state (`loaded_libraries`, variable names) with `OBSERVED`/`live-session` provenance; `dom`→`Get Page Source`/`Get Source`, `screenshot`→`Take Screenshot` via `engine.query` with `keyword:<name>` provenance; `accessibility`/`last_api_response` have no v1 live source; any kind with no resolving/ succeeding keyword returns a structured `snapshot-unavailable` error (retryable, `OBSERVED`, attempted-keywords + last error in details). Removed `_synthetic_snapshot_payload`.
- Tests rewritten: `app_context` proves real library state; `dom`/`screenshot`/`accessibility`/`last_api_response` return `snapshot-unavailable` in a default (no-browser) session; gating/denial assertions preserved; interrupted-session test now reads `app_context`.
- Honest scope note: real DOM/screenshot capture requires a session that imported and drove Browser/Selenium (Playwright/node + open page); the code path is implemented and exercised against a real RF runner, but a live browser is not available in this environment, so those kinds are proven via the unavailable path here.

### File List

- packages/rfmcp_core/src/rfmcp_core/runtime/execution.py
- packages/rfmcp_core/src/rfmcp_core/runtime/snapshot.py
- packages/rfmcp_core/src/rfmcp_core/models/payloads.py
- assets/schemas/inspection-snapshot-result.schema.json
- tests/test_mcp_live_session_surface.py

## Change Log

- 2026-05-27: Implemented Story 5.3 — `app_inspect_state` sources real state from live library keywords (`app_context` from real session state; DOM/screenshot via real RF keywords) with `OBSERVED` provenance, returns structured `snapshot-unavailable` when no live source exists, and removes the synthetic fixtures. Added `provenance` to the snapshot contract. Full suite green (111 tests). Promoted to review.
- 2026-05-27: Applied code-review findings (claude/sonnet): null-engine TOCTOU guards in `get_runtime_context`/`set_runtime_context`/`execute_step`/`capture_inspection_snapshot` (closed-session race now returns `session-not-open`/`reads`/`mutation` instead of `tool-execution-failed`); removed the wrong-context `BuiltIn().run_keyword` fallback (raise on missing `get_runner`); double-checked `self._started` inside the lock in `start()`; unregister RF's global console LOGGER so it can't write to the stdio JSON-RPC channel; `_json_safe` base64-encodes `bytes`/`bytearray`. Full suite green (111 tests). Completed Story 5.3.

## Senior Developer Review (AI)

**Reviewers:** `claude` CLI (sonnet) — completed (9 findings); `kilo` CLI (minimax-m2.7) — timed out with no output (provider contention with an unrelated concurrent kilo job; 7-minute guard). Finalized on the claude review.

### claude/sonnet — outcome: Changes Requested (all resolved)

- [x] High — `get_runtime_context` deref of a `None` engine (closed-session TOCTOU) → null guard returns `session-not-open` (reads).
- [x] High — `execute_step` same TOCTOU → null guard returns `session-not-open`.
- [x] Med — `capture_inspection_snapshot` TOCTOU swallowed as `snapshot-unavailable` → null guard returns `session-not-open`.
- [x] Med — `BuiltIn().run_keyword` fallback was dead in RF7 and would run in the wrong (process-global) context → removed; raise if `get_runner` is absent.
- [x] Med — `start()` checked `_started` before the lock (double-init/leak race) → re-check inside the lock.
- [x] Med — RF global `LOGGER` could write console output to fd 1 (stdio JSON-RPC) bypassing the `sys.stdout` swap → `LOGGER.unregister_console_logger()` on context start.
- [x] Low — `set_runtime_context` TOCTOU returned misleading `invalid-context-key` → null guard returns `session-not-open` (mutation).
- [x] Low — `_json_safe(bytes)` produced an inflated `repr()` → base64-encode bytes.
- [x] Low — dead `get_runner` fallback comment invited unsafe reuse → removed with the fallback.

The TOCTOU null-engine class was introduced by Story 5.2's closed-session guard in `get_or_create_engine` (which returns `None` for a closed session); the call-site guards close it. Clean areas confirmed by claude: rename completeness, both `InspectionSnapshotResult` sites supply `provenance`, synthetic payload fully removed, schema consistent, gating order correct, `snapshot-unavailable` is a legitimate proof.
