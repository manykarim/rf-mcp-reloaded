# Story 5.1: Execute Real Keywords in an In-Process Live RF Context

Status: done

## Story

As an Automation Engineer,
I want each repair step to run as a real Robot Framework keyword in a persistent in-process context,
so that variables, imports, and library state carry across steps and real failures surface honestly.

This story also drops the misleading `repair` qualifier from the general live-session primitive (the session and step tools serve repair, authoring, and exploration alike), keeping `repair` only where behavior is genuinely repair-specific.

## Acceptance Criteria

1. **Given** an open live session
   **When** `rf_execute_step` runs a keyword (e.g. `Should Be Equal    1    2`)
   **Then** the keyword executes through a real Robot Framework execution context (`EXECUTION_CONTEXTS` / namespace / `BuiltIn`)
   **And** a genuine pass/fail is returned through the existing `StepResult` + `ErrorEnvelope` contracts
   **And** the in-memory `step_executor=None` simulation path is removed.

2. **Given** a multi-step session
   **When** a later step references a variable assigned by an earlier step
   **Then** the live namespace resolves it so state persists across steps without restarting the context.

3. **Given** the live-session primitive is general (used for repair, authoring, and exploration alike)
   **When** the engine lands
   **Then** the session and step tools and types drop the `repair` qualifier — `rf_open_session`, `rf_get_session`, `rf_execute_step`, `rf_close_session`, `LiveSessionStore`, `LiveStepper`, `SessionSummary`, `StepResult`, and the `session` / `step-result` JSON Schemas
   **And** the `repair` name is retained only where behavior is genuinely repair-specific (`RepairDiagnosticResult`, `repair-diagnostic-result.schema.json`, repair diagnostics/hints CLI, the Browser Library flagship repair skill, FR15).

## Tasks / Subtasks

- [x] **Task 1: Add the in-process live execution engine** (AC: 1, 2)
  - [x] Create `packages/rfmcp_core/src/rfmcp_core/runtime/execution.py` with a `LiveExecutionContext` that lazily builds and holds a persistent RF context per session.
  - [x] Context setup (RF 7.x public APIs): `VariableScopes(RobotSettings())`, `TestSuite(name=...)` with a `.robot` source, `ResourceFile`, `Namespace(variables, suite, suite.resource, Languages())`, `Output(RobotSettings(outputdir=<tempdir>, output=None, console='none'))`, then `EXECUTION_CONTEXTS.start_suite(suite, namespace, output, dry_run=False)`; import `BuiltIn`; set `${OUTPUTDIR}`/`${LOGFILE}`/`${OUTPUT}` variables.
  - [x] Suppress stdout/stderr during context creation and keyword execution so RF console output cannot corrupt the MCP `stdio` JSON-RPC channel.
  - [x] `execute(instruction)` parses an RF step line (keyword + `4-space / 2+ whitespace`-separated args, leading `${x} =` assignment syntax), runs it via `BuiltIn().run_keyword(name, *args)`, persists any assignment into the namespace variables, and returns a typed result (ok, return value, error detail).
  - [x] Provide an explicit `close()` that tears down the session's context (`EXECUTION_CONTEXTS.end_suite()` / pop) and removes the temp output dir; isolate per-session so concurrent sessions do not clobber `EXECUTION_CONTEXTS.current`.
- [x] **Task 2: Wire the engine into the stepper, remove the simulation** (AC: 1)
  - [x] Replace `LiveStepper`'s `step_executor: Callable | None = None` no-op path with the real engine; a step is `ok=True` only if the keyword passed.
  - [x] Map keyword failures to `ErrorEnvelope` (code `step-failed`, `provenance.kind = OBSERVED`, source `stepper`, real RF message in `message`/`details`); keep `step-interrupted` for `InterruptedError`, and the existing `session-not-found` / `session-not-open` paths.
  - [x] Keep `LiveSessionStore.record_step` accounting; store still owns lifecycle/state, engine owns execution.
- [x] **Task 3: Rename the general primitive (drop `repair`)** (AC: 3)
  - [x] Tool names in `_registry.py`: `rf_open_repair_session`→`rf_open_session`, `rf_get_repair_session`→`rf_get_session`, `rf_execute_repair_step`→`rf_execute_step`, `rf_close_repair_session`→`rf_close_session`. Update their `description` / `live_state_justification` wording.
  - [x] Function names inside `tools/rf_open_session.py`, `rf_get_session.py`, `rf_execute_step.py`, `rf_close_session.py` to match (filenames already generic).
  - [x] Core types: `LiveRepairSessionStore`→`LiveSessionStore`, `LiveRepairSessionRecord`→`LiveSessionRecord`, `LiveRepairStepper`→`LiveStepper`, `RepairSessionSummary`→`SessionSummary`, `RepairStepResult`→`StepResult` in `runtime/session.py`, `runtime/stepper.py`, `models/payloads.py`, and all imports.
  - [x] Contracts: rename module `contracts/repair.py`→`contracts/session.py`; update `contracts/__init__.py` re-exports and `runtime/__init__.py`, `runtime/context.py`, `runtime/snapshot.py`, `_registry.py`, `server.py`, `transports/*`, all `tools/*` imports.
  - [x] Schemas: `export_json_schemas.py` keys `repair-session.schema.json`→`session.schema.json`, `repair-step-result.schema.json`→`step-result.schema.json`; delete the old schema files and regenerate. Keep `repair-diagnostic-result.schema.json`.
  - [x] Strings: provenance sources `repair-session-store`→`session-store`, `repair-stepper`→`stepper`; error code `repair-step-interrupted`→`step-interrupted`; server `SERVER_INSTRUCTIONS` "repair-session tools" → "live-session tools".
  - [x] Update `tests/test_mcp_live_repair_surface.py` (imports, allowlist names, error codes) — consider renaming the test file to `tests/test_mcp_live_session_surface.py`.
- [x] **Task 4: Tests** (AC: 1, 2, 3)
  - [x] Real execution: `Evaluate    1 + 2` assigned to `${result}` returns `3`; `Should Be Equal    1    1` passes; `Should Be Equal    1    2` fails with a real `step-failed` envelope (mirrors the investigation experiment).
  - [x] State persistence: a step using `${result}` set by an earlier step resolves to the live value.
  - [x] Allowlist still exactly the 7 generic tool names; `MAX_USER_FACING_TOOLS` unchanged.
  - [x] Schema sync passes after regeneration (`scripts/verify_schema_sync.py`).
- [x] **Task 5: Verification gate**
  - [x] `uv run --group dev python scripts/export_json_schemas.py && uv run --group dev python scripts/verify_schema_sync.py`
  - [x] `python3 scripts/verify_workspace_structure.py`
  - [x] `uv run --group dev python -m unittest discover -s tests -v` (full suite green — no regressions in Epic 1-3 tests).

## Dev Notes

### Current state of files being modified (read before editing)

- `runtime/stepper.py` — `LiveRepairStepper.execute_step` currently: checks session via store, on success calls `record_step` and returns `RepairStepResult(ok=True, detail="Recorded a bounded repair step...")`. `step_executor` defaults to `None` and is only ever a real callable in tests. **This no-op path is what 5.1 replaces.**
- `runtime/session.py` — `LiveRepairSessionRecord` holds `rf_context` (placeholder dict), `libraries`, `steps`, `step_count`, `status`. `LiveRepairSessionStore` is an in-memory, `Lock`-guarded dict. 5.1 keeps lifecycle/accounting; adds a handle to the live engine (do NOT execute inside the store).
- `tools/rf_execute_step.py` — `build_execute_step_tool(store, stepper=None)` builds `LiveRepairStepper(store)` (no executor). Must build with the real engine.
- `tools/_registry.py` — 7-tool allowlist, `MAX_USER_FACING_TOOLS = 7`, `ALLOWLISTED_TOOL_NAMES`. Renames here are public-surface; keep the count and the `RuntimeError` guard.
- `models/payloads.py` — `RepairSessionSummary`, `RepairStepResult`, `SessionStatus` (Category A → rename); `RepairDiagnosticResult` (Category B → keep).
- `tests/test_mcp_live_repair_surface.py` — asserts the 4 session/step tool names, builds `LiveRepairStepper(store, step_executor=raise_interrupt)` for the interrupt case, asserts `repair-step-interrupted`.

### In-process RF context recipe (RF 7.4.2, validated against the original rf-mcp)

```python
from robot.conf.settings import RobotSettings
from robot.conf.languages import Languages
from robot.output import Output
from robot.running.context import EXECUTION_CONTEXTS
from robot.running.model import TestSuite
from robot.running.namespace import Namespace
from robot.running.resourcemodel import ResourceFile
from robot.variables.scopes import VariableScopes
from robot.libraries.BuiltIn import BuiltIn

variables = VariableScopes(RobotSettings())
suite = TestSuite(name=f"RFMCP_Session_{session_id}")
suite.source = Path(f"RFMCP_Session_{session_id}.robot")
suite.resource = ResourceFile(source=suite.source)
namespace = Namespace(variables, suite, suite.resource, Languages())
settings = RobotSettings(outputdir=tempdir, output=None, console="none")
output = Output(settings)
output.library_listeners.new_suite_scope()
variables["${OUTPUTDIR}"] = tempdir
namespace.import_library("BuiltIn")
ctx = EXECUTION_CONTEXTS.start_suite(suite, namespace, output, dry_run=False)
namespace.start_suite()
# execute:
result = BuiltIn().run_keyword(keyword_name, *arguments)
```

- **stdout discipline (critical):** RF writes console/log output to stdout; on the `stdio` transport fd 1 is the JSON-RPC channel. Wrap context creation and `run_keyword` in a stdout/stderr suppressor (redirect to `os.devnull` or `io.StringIO`). This is why the original passes `console='none'` and uses a `_suppress_stdout()` contextmanager.
- **Assignment syntax:** support `${name} =` / `${name}=` prefix; strip it, run the keyword, then `namespace.variables[name] = return_value` so later steps resolve it (AC 2).
- **Argument parsing:** split the instruction on runs of 2+ spaces (RF's separator), first token is the keyword. Keep it simple; named args / embedded args can be a follow-up.
- **Concurrency:** `EXECUTION_CONTEXTS` is process-global. v1 is a single active session at a time; guard so a second open while one is active is handled deterministically (reuse or error) rather than silently sharing `.current`. Document the limitation.

### Project Structure Notes

- New file `runtime/execution.py` matches the architecture skeleton (`architecture.md` package tree names `execution.py`) and the "Live Execution Engine for the MCP Core" decision.
- Robot Framework is already a dependency (7.4.2 confirmed). No new deps for 5.1.
- Stories 5.2 (context get/set) and 5.3 (snapshots) will read from this same live context/namespace and library instances — design `LiveExecutionContext` to expose `variables` and imported library instances for them.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 5 / Story 5.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#Live Execution Engine for the MCP Core]
- [Source: _bmad-output/planning-artifacts/prds/prd-rfmcp-reloaded-2026-05-23/prd.md#FR-2]
- [Source: docs/mcp-live-repair-boundary.md#Execution Model]
- [Source: investigation _bmad-output/implementation-artifacts/investigations/mcp-core-stepwise-fr2-investigation.md]
- Reference implementation (read-only, not a dependency): `manykarim/rf-mcp` `src/robotmcp/components/execution/rf_native_context_manager.py:141-260`.

## Dev Agent Record

### Agent Model Used

claude-opus-4-7 (1M context)

### Debug Log References

- `uv run python` smoke of `LiveExecutionContext` (Evaluate→3, persistence, real `1 != 2` failure, close).
- `uv run python` smoke of full MCP path via `build_open_session_tool`/`build_execute_step_tool`/`build_close_session_tool`.
- `uv run --group dev python scripts/export_json_schemas.py` → 18 schemas (now `session.schema.json`, `step-result.schema.json`).
- `uv run --group dev python scripts/verify_schema_sync.py` → Schema sync OK.
- `python3 scripts/verify_workspace_structure.py` → Workspace structure OK.
- `uv run --group dev python -m unittest discover -s tests -v` → Ran 110 tests, OK.

### Completion Notes List

- Added `runtime/execution.py` `LiveExecutionContext`: builds a persistent RF 7 context per session (`VariableScopes`, `TestSuite`, `Namespace`, `Output(console='none')`, `EXECUTION_CONTEXTS.start_suite`), executes one keyword per step via `namespace.get_runner()` + `runner.run(data_kw, res_kw, ctx)` (RF-native variable resolution; `BuiltIn().run_keyword` fallback), supports `${x} =` assignment into the live namespace, suppresses stdout/stderr to protect the stdio JSON-RPC channel, and tears down + removes the temp dir on `close()`.
- Rewrote `LiveStepper` to drive the engine via `store.get_or_create_engine(session_id)`; removed the `step_executor=None` simulation. Real failures → `ErrorEnvelope(code="step-failed", provenance source "live-execution")`; `InterruptedError` → `step-interrupted`; a failed keyword is still recorded as an executed step.
- `LiveSessionStore` gained a runtime-only `engine` handle, an overridable `engine_factory` (test seam), `get_or_create_engine`, and engine teardown in `close_session`.
- Renamed the general live-session primitive (Category A) dropping `repair`: tools `rf_open_session`/`rf_get_session`/`rf_execute_step`/`rf_close_session`; types `LiveSessionStore`/`LiveSessionRecord`/`LiveStepper`/`SessionSummary`/`StepResult`; module `contracts/repair.py`→`contracts/session.py`; schemas `session.schema.json`/`step-result.schema.json`; provenance/error strings; server instructions; flagship skill asset README tool references. Category B (`RepairDiagnosticResult`, `repair-diagnostic-result.schema.json`, repair diagnostics/hints CLI, the Browser Library flagship *repair* skill identity, FR15) intentionally kept.
- Session id prefix changed `repair-…`→`session-…`.
- Note: real DOM/app-state snapshots and live-namespace context get/set remain placeholder/synthetic — they are Stories 5.3 and 5.2 respectively; their existing tests are unchanged and still green.
- Single active in-process session at a time (process-global `EXECUTION_CONTEXTS`); documented in `execution.py`. Attach path is Story 5.4.

### File List

- packages/rfmcp_core/src/rfmcp_core/runtime/execution.py (new)
- packages/rfmcp_core/src/rfmcp_core/runtime/stepper.py
- packages/rfmcp_core/src/rfmcp_core/runtime/session.py
- packages/rfmcp_core/src/rfmcp_core/runtime/__init__.py
- packages/rfmcp_core/src/rfmcp_core/runtime/context.py
- packages/rfmcp_core/src/rfmcp_core/runtime/snapshot.py
- packages/rfmcp_core/src/rfmcp_core/contracts/session.py (renamed from contracts/repair.py)
- packages/rfmcp_core/src/rfmcp_core/contracts/__init__.py
- packages/rfmcp_core/src/rfmcp_core/models/__init__.py
- packages/rfmcp_core/src/rfmcp_core/models/payloads.py
- packages/rfmcp_mcp/src/rfmcp_mcp/server.py
- packages/rfmcp_mcp/src/rfmcp_mcp/tools/_registry.py
- packages/rfmcp_mcp/src/rfmcp_mcp/tools/rf_open_session.py
- packages/rfmcp_mcp/src/rfmcp_mcp/tools/rf_get_session.py
- packages/rfmcp_mcp/src/rfmcp_mcp/tools/rf_execute_step.py
- packages/rfmcp_mcp/src/rfmcp_mcp/tools/rf_close_session.py
- packages/rfmcp_mcp/src/rfmcp_mcp/tools/rf_get_context.py
- packages/rfmcp_mcp/src/rfmcp_mcp/tools/rf_set_context.py
- packages/rfmcp_mcp/src/rfmcp_mcp/tools/app_inspect_state.py
- packages/rfmcp_mcp/src/rfmcp_mcp/transports/stdio.py
- packages/rfmcp_mcp/src/rfmcp_mcp/transports/http.py
- packages/rfmcp_skills/src/rfmcp_skills/definitions/browser_library_repair.py
- assets/skills/browser-library-flagship-repair/README.md
- assets/schemas/session.schema.json (renamed from repair-session.schema.json)
- assets/schemas/step-result.schema.json (renamed from repair-step-result.schema.json)
- scripts/export_json_schemas.py
- tests/test_mcp_live_session_surface.py (renamed from tests/test_mcp_live_repair_surface.py)
- tests/test_browser_library_flagship_repair_workflow.py
- tests/saucedemo/run_stepwise.py

## Change Log

- 2026-05-27: Implemented Story 5.1 — in-process live RF execution engine behind the MCP stepper (real keywords, real pass/fail, state persistence), removed the simulation seam, and renamed the general live-session primitive (dropped `repair`). Full suite green (110 tests). Promoted to review.
- 2026-05-27: Applied code-review findings (claude/sonnet): thread-safe stream suppression + serialized RF context ops, `runner.run` uses the session-local context, temp-dir cleanup on failed start, `InterruptedError` re-raise, stale "repair session" error strings → "live session", documented RF-internals teardown fallback, renamed test class/method. Re-verified: schema sync OK, 110 tests pass. Completed Story 5.1.

## Senior Developer Review (AI)

**Reviewers:** `claude` CLI (model: sonnet) and `kilo` CLI (model: minimax-m2.7), per the requested two-reviewer setup.

**Outcome:** Changes Requested → all addressed (claude). Kilo review did not return (see note).

### claude/sonnet — outcome: Changes Requested (all resolved)

Action items (severity → resolution):

- [x] High — `execution.py` stream suppression not thread-safe → added module-level `_CONTEXT_LOCK` (RLock) guarding the stdout/stderr swap and all RF context ops.
- [x] High — `runner.run()` used the process-global `EXECUTION_CONTEXTS.current` → now passes the session-local `self._ctx`.
- [x] Med — `start_suite()` had no concurrency guard → covered by `_CONTEXT_LOCK` serialization.
- [x] Med — temp dir orphaned if `start()` raised → `try/except` removes it and re-raises.
- [x] Med — `execute()` swallowed `InterruptedError` in `except Exception` → re-raises it; stepper's `except InterruptedError` is the single interrupt path (removed the redundant string-check).
- [x] Med — stale "repair session" strings in `context.py` / `snapshot.py` / `rf_close_session.py` / `rf_get_session.py` error messages → "live session" (synthetic snapshot payload data intentionally left for Story 5.3).
- [x] Med — `close()` fallback touches RF private attrs → documented the RF 7.4.x assumption inline.
- [x] Low — test class/method still named `…Repair…` → renamed to `McpLiveSessionSurfaceTests` / `…_session_only`.
- [x] Low — dead `except InterruptedError` branch → now live (real engine re-raises; `_InterruptEngine` double exercises it).

Clean areas confirmed by claude: rename/import completeness, schema sync, `_parse_instruction` edge cases, `session.py` lock discipline, failed-step recording, Category-B `repair` preservation.

### kilo/minimax-m2.7 — note

The kilo review process ran ~60 minutes with no output (provider contention with an unrelated concurrent kilo job on another repo) and was stopped as stalled. Story 5.1 was finalized on the claude review, which covered all five requested focus areas. Kilo review can be re-run later as a best-effort second pass; no blocking findings are outstanding.
