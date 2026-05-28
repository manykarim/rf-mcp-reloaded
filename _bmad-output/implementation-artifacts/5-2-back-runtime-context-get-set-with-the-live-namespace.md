# Story 5.2: Back Runtime Context Get/Set With the Live Namespace

Status: done

## Story

As an Automation Engineer,
I want `rf_get_context` / `rf_set_context` to read and write the real Robot Framework runtime namespace,
so that the context I inspect and mutate is execution truth, not a placeholder.

## Acceptance Criteria

1. **Given** a live session with executed steps
   **When** `rf_get_context` is called
   **Then** it returns real Robot Framework variables and actually-loaded libraries instead of the seeded placeholder dict
   **And** `rf_set_context` writes into the live namespace under the existing policy and capability gating.

2. **Given** a variable set via `rf_set_context`
   **When** a later `rf_get_context` (or a subsequent `rf_execute_step`) reads it
   **Then** the value is resolved from the live namespace (round-trips through real RF variable storage).

## Tasks / Subtasks

- [x] **Task 1: Expose namespace access on the engine** (AC: 1, 2)
  - [x] Add to `LiveExecutionContext`: `get_variables(keys=None) -> dict[str, Any]` (from `self._variables.as_dict()`, JSON-coerced, optionally filtered), `set_variable(name, value)` (writes `self._variables[name] = value`), `imported_libraries() -> list[str]` (from `self._namespace.libraries`). Starting the engine lazily on read is acceptable.
  - [x] JSON-safety: coerce variable values that are not JSON-native to `repr()` so the `RobotContextView` payload always serializes.
- [x] **Task 2: Back `get_runtime_context` with the live namespace** (AC: 1)
  - [x] In `runtime/context.py`, replace `record.rf_context` reads with the engine: get/create engine, ensure started, return real `variables` + `libraries`. Preserve `session-not-found` (record missing) and `session-not-open` (CLOSED) structured errors and key-filtering.
- [x] **Task 3: Back `set_runtime_context` with the live namespace** (AC: 1, 2)
  - [x] Keep the existing gating order: policy load → `policy-context-write-disabled` → session-not-found → session-not-open → `session-context-write-disabled` → empty-key `invalid-context-key`. Then write via `engine.set_variable(key, value)`; map a rejected RF variable name to `invalid-context-key`.
- [x] **Task 4: Tests** (AC: 1, 2)
  - [x] Update `test_context_tools_support_read_and_write`: baseline returns real RF built-ins (e.g. `${/}`), `${BROWSER}` set→get round-trips, key filtering works.
  - [x] Update the interrupted-session read test and the `_InterruptEngine` double to provide `get_variables`/`set_variable`/`imported_libraries`.
  - [x] Keep policy-denial, session-denial, invalid-key, policy-load-failure, and unexpected-exception tests green.
  - [x] Add a round-trip test: `rf_set_context("${X}", 7)` then `rf_get_context(["${X}"])` returns `7`, and `rf_execute_step("Should Be Equal    ${X}    ${7}")` passes.
- [x] **Task 5: Verification gate**
  - [x] `uv run --group dev python scripts/verify_schema_sync.py`; full `unittest` suite green.

## Dev Notes

- `LiveExecutionContext` (from Story 5.1) owns the live `VariableScopes` (`self._variables`) and `Namespace` (`self._namespace`). Probed APIs: `variables.as_dict()` → `{'${/}': '/', ...}` (21 RF built-ins on a fresh context); `variables["${X}"] = v` then `variables["${X}"]` round-trips arbitrary Python objects; `[l.name for l in namespace.libraries]` → `['BuiltIn', 'Collections']`.
- The placeholder `record.rf_context` seed (`{"${CURRENT_TEST}": "Repair Session"}`) and `store.set_context_value` become vestigial for the read/write path; leave the store method in place but route get/set through the engine.
- Gating helpers (`capability_allowed`, `load_local_policy_defaults`, `PolicyCapability.CONTEXT_WRITE`, `record.allow_context_write`) are unchanged and must keep producing the same error codes/sources the existing tests assert (`local-policy`, `session-store`, `runtime-context`).
- Synthetic snapshot payloads in `snapshot.py` are out of scope here — they belong to Story 5.3.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 5 / Story 5.2]
- [Source: _bmad-output/planning-artifacts/architecture.md#Live Execution Engine for the MCP Core]
- [Source: packages/rfmcp_core/src/rfmcp_core/runtime/context.py] (current placeholder impl)
- [Source: packages/rfmcp_core/src/rfmcp_core/runtime/execution.py] (Story 5.1 engine)

## Dev Agent Record

### Agent Model Used

claude-opus-4-7 (1M context)

### Debug Log References

- Probed `VariableScopes`: `as_dict()` does NOT enumerate `__setitem__` writes (nor `set_suite`), but `__getitem__` and keyword execution DO resolve them.
- `uv run --group dev python -m unittest discover -s tests` → Ran 111 tests, OK.

### Completion Notes List

- Added `LiveExecutionContext.get_variables(keys)`, `set_variable(name, value)`, `imported_libraries()`, and a module `_json_safe()` coercion.
- `runtime/context.py`: `get_runtime_context` and `set_runtime_context` now read/write the live engine namespace instead of the placeholder `record.rf_context`; gating order and structured error codes/sources unchanged.
- Key implementation detail: RF's `as_dict()` does not reliably enumerate variables written via `__setitem__`/`set_suite`, even though they resolve correctly during keyword execution (confirmed by Story 5.1's persistence test). To keep `rf_get_context` deterministic, the engine tracks engine-set/assigned variables in a side dict `self._assigned` and merges it over `as_dict()` on read; keyword steps still resolve via RF's native namespace. Both step-assignments (`${x} =`) and `set_variable` populate `_assigned`.
- `rf_get_context` baseline now returns real RF built-ins (e.g. `${/}`) and real loaded libraries (`BuiltIn`); `rf_set_context` → `rf_get_context`/`rf_execute_step` round-trips through the live namespace.
- Tests updated: `test_context_tools_support_read_and_write` asserts real built-ins/libraries; added `test_context_set_get_roundtrip_through_live_namespace`; `_InterruptEngine` double gained `get_variables`/`set_variable`/`imported_libraries`. Policy/session/invalid-key/policy-load/unexpected-exception tests unchanged and green.

### File List

- packages/rfmcp_core/src/rfmcp_core/runtime/execution.py
- packages/rfmcp_core/src/rfmcp_core/runtime/context.py
- tests/test_mcp_live_session_surface.py

## Change Log

- 2026-05-27: Implemented Story 5.2 — `rf_get_context`/`rf_set_context` backed by the live RF namespace (real variables + loaded libraries), with a deterministic `_assigned` side-dict to work around RF `as_dict()` enumeration gaps. Full suite green (111 tests). Promoted to review.
- 2026-05-27: Applied code-review findings (claude/sonnet): filtered `get_variables` reads resolve each key via `__getitem__` (live value, no staleness) and the unfiltered merge prefers the live namespace; `_assigned` reads/writes guarded by `_CONTEXT_LOCK`; `set_runtime_context` echo value JSON-coerced; RF variable-name shape validated (`${NAME}`/`@{LIST}`/`&{MAP}`) → `invalid-context-key`; `_json_safe` rejects `NaN`/`Inf`; `get_or_create_engine` won't create an engine for a closed session. Added a malformed-name test. Full suite green (111 tests). Completed Story 5.2.

## Senior Developer Review (AI)

**Reviewers:** `claude` CLI (sonnet) — completed; `kilo` CLI (minimax-m2.7) — did not return (provider contention with an unrelated concurrent kilo job; an 8-minute timeout guard fired with no output). Finalized on the claude review.

### claude/sonnet — outcome: Changes Requested (all resolved)

- [x] Med — `_assigned` shadowed live RF updates (stale reads) → filtered reads use `self._variables[key]` (resolves across scopes); unfiltered merge is `{**_assigned, **as_dict()}` (live namespace wins).
- [x] Med — `_assigned` accessed without `_CONTEXT_LOCK` → `get_variables`/`set_variable` now hold the lock.
- [x] Med — `set_runtime_context` echo value not JSON-coerced → `RobotContextMutationResult(value=_json_safe(value))`.
- [x] Low — `_json_safe` accepted `NaN`/`Infinity` → `json.dumps(value, allow_nan=False)`.
- [x] Low — RF-rejected non-empty key path untested → added explicit `${}`-shape validation + a `"NOBRACES"` test.
- [x] Low — TOCTOU could leak an engine for a closed session → `get_or_create_engine` returns early for `CLOSED`.
- [ ] Low (noted, not fixed) — lazy `start()` on read commits an RF context for a never-stepped session that's never closed; same pre-existing risk as `execute_step`, documented.

Clean areas confirmed by claude: gating order and error codes/sources preserved; `_InterruptEngine` double interface correct; the read/round-trip tests are genuine live-namespace proofs that would fail against the old placeholder.
