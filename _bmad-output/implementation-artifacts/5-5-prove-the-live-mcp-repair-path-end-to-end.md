# Story 5.5: Prove the Live MCP Repair Path End-to-End

Status: done

## Story

As a maintainer,
I want the repair loop proven end-to-end through the live MCP path,
so that FR15's proof exercises real keyword execution, not only the CLI subprocess fallback.

## Acceptance Criteria

1. **Given** the live execution engine from Stories 5.1-5.4
   **When** a repair scenario runs through the MCP tools (`rf_open_session` → `rf_execute_step` → `rf_get_context`/`app_inspect_state` → `rf_set_context` → `rf_execute_step` → `rf_close_session`)
   **Then** a real failure is observed live, a repair is applied, and a real re-run passes — all through the live in-process engine (no synthetic results, no CLI subprocess).

2. **Given** the end-to-end run
   **When** it completes
   **Then** benchmark evidence is recorded (surface = `mcp`, tool-call count, failed-tool-call count, runnable success) and written to a proof pack under `dist/benchmarks/`.

3. **Given** Epic 4's release gates
   **When** CI/benchmark stories (4.4, 4.5) are planned
   **Then** they reference the live MCP path as a release gate.

## Tasks / Subtasks

- [x] **Task 1: Live MCP repair proof** (AC: 1, 2)
  - [x] Add `packages/rfmcp_mcp/src/rfmcp_mcp/benchmarks.py` with `run_live_mcp_repair_proof() -> LiveMcpProof` that drives the real MCP tools against a fresh `LiveSessionStore` (in-process engine): open → execute a step that fails live (`Should Be Equal    ${STATUS}    PASS` with `${STATUS}` unset) → inspect (`rf_get_context` + `app_inspect_state app_context`) → repair (`rf_set_context ${STATUS} PASS`) → re-execute the same step (now passes) → close. Capture per-call surface/ok and a metrics summary.
  - [x] `write_live_mcp_proof_pack(output_path) -> LiveMcpProof` writes the proof JSON (default `dist/benchmarks/epic5-live-mcp-proof.json`).
- [x] **Task 2: Proof script** (AC: 2)
  - [x] Add `scripts/run_epic5_live_mcp_proof.py` (mirrors `run_epic3_benchmark_pack.py`).
- [x] **Task 3: Epic 4 release-gate reference** (AC: 3)
  - [x] In `epics.md`, note in Stories 4.4 and 4.5 that the live MCP repair path (Epic 5) is a release gate / part of the benchmark evidence.
- [x] **Task 4: Tests** (AC: 1, 2)
  - [x] `tests/test_live_mcp_repair_proof.py`: assert the live loop — first execute fails (`step-failed`, real RF `${STATUS}` error), repair succeeds, re-execute passes; metrics show `surface == "mcp"`, `failed_tool_calls >= 1`, `runnable_success is True`; proof pack writes and round-trips.
- [x] **Task 5: Verification gate**
  - [x] `verify_schema_sync.py`; full `unittest` suite green; run the proof script and confirm it writes the pack.

## Dev Notes

- This is the capstone proving Stories 5.1-5.4 compose into a real repair loop over the MCP surface. It uses BuiltIn keywords only (`Should Be Equal`) so it runs deterministically without a browser/Playwright — the flagship Browser repair additionally needs a live browser (the existing CLI/subprocess flagship proof in `tests/test_browser_library_flagship_repair_workflow.py` covers the file-edit + rerun; this story proves the *live MCP execution* half).
- Reuse the MCP tool builders (`build_open_session_tool`, `build_execute_step_tool`, `build_get_context_tool`, `build_set_context_tool`, `build_app_inspect_state_tool`, `build_close_session_tool`) and a fresh `LiveSessionStore` — exactly the surface an agent host drives.
- Benchmark/observability shapes to mirror: `rfmcp_cli.benchmarks.BenchmarkScenarioResult`/`BenchmarkSummary`, `rfmcp_core.observability.events.WorkflowEvent(surface, benchmark, ...)`. Keep the new proof in `rfmcp_mcp` (it drives the MCP surface); define its own small pydantic result model rather than importing the CLI's.
- Output goes under `dist/benchmarks/` next to the existing `epic3-proof-pack.json`.
- Layering: `rfmcp_mcp` may import `rfmcp_core`; do not import `rfmcp_cli`.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Epic 5 / Story 5.5]
- [Source: _bmad-output/planning-artifacts/prds/prd-rfmcp-reloaded-2026-05-23/prd.md#FR-15]
- [Source: packages/rfmcp_cli/src/rfmcp_cli/benchmarks.py] (benchmark pack pattern)
- [Source: packages/rfmcp_core/src/rfmcp_core/observability/events.py] (WorkflowEvent)
- [Source: tests/test_browser_library_flagship_repair_workflow.py] (existing CLI flagship proof)

## Dev Agent Record

### Agent Model Used

claude-opus-4-7 (1M context)

### Debug Log References

- `uv run --group dev python scripts/run_epic5_live_mcp_proof.py` → runnable_success=True, tool_calls=7, failed_tool_calls=1; wrote `dist/benchmarks/epic5-live-mcp-proof.json`.
- `uv run --group dev python scripts/verify_schema_sync.py` → Schema sync OK.
- `python3 scripts/verify_workspace_structure.py` → OK.
- `uv run --group dev python -m unittest discover -s tests` → Ran 117 tests, OK.

### Completion Notes List

- Added `rfmcp_mcp/benchmarks.py` `run_live_mcp_repair_proof()` / `write_live_mcp_proof_pack()`: drives the real MCP tools against a fresh in-process `LiveSessionStore` through the full live repair loop — open → `Should Be Equal ${STATUS} PASS` fails live (real RF, `${STATUS}` unset) → `rf_get_context` + `app_inspect_state app_context` (real) → `rf_set_context ${STATUS} PASS` → identical step re-runs and passes → close. Emits a `LiveMcpProof` with surface=`mcp`, tool/failed-call counts, and per-call trace; writes JSON to `dist/benchmarks/epic5-live-mcp-proof.json`.
- Proof outcome: `runnable_success=True`, `tool_calls=7`, `failed_tool_calls=1` (the reproduced failure) — the live MCP path executes real keywords end-to-end, not a CLI subprocess or synthetic results.
- Added `scripts/run_epic5_live_mcp_proof.py` and `tests/test_live_mcp_repair_proof.py` (loop assertions + proof-pack round-trip).
- `epics.md` Stories 4.4 (CI release gate) and 4.5 (benchmark evidence) now reference the Epic 5 live MCP proof so the live-execution path is gated/measured alongside the CLI flagship proof.
- Layering preserved: `rfmcp_mcp.benchmarks` imports only `rfmcp_core` + sibling MCP tools; no `rfmcp_cli` dependency.
- Scope note: this proves the *live MCP execution* half of the flagship; the browser file-edit + rerun half remains covered by the existing CLI/subprocess flagship proof (a real browser/Playwright is not available here).

### File List

- packages/rfmcp_mcp/src/rfmcp_mcp/benchmarks.py (new)
- scripts/run_epic5_live_mcp_proof.py (new)
- tests/test_live_mcp_repair_proof.py (new)
- _bmad-output/planning-artifacts/epics.md (4.4 / 4.5 release-gate references)
- dist/benchmarks/epic5-live-mcp-proof.json (generated proof pack)

## Change Log

- 2026-05-27: Implemented Story 5.5 — end-to-end live MCP repair proof (`rfmcp_mcp.benchmarks`) driving the real tools through fail→repair→pass over the in-process engine, with a benchmark proof pack and Epic 4 release-gate references. Full suite green (117 tests). Promoted to review.
- 2026-05-27: Applied code-review findings (claude/sonnet): wrapped the proof in `try/finally` so the live RF context is always closed (no `EXECUTION_CONTEXTS` leak); guard a non-ok `rf_open_session` before dereferencing the session; `reproduced_failure` now requires a real `step-failed` (not a session/lifecycle error); added a policy preflight so a disabled capability raises instead of masquerading as a failed proof; the script exits non-zero when `runnable_success` is false (CI gate); tightened tests to assert concrete `tool_calls == 7` / `failed_tool_calls == 1` and de-tautologized the proof-pack test. Full suite green (117 tests); proof script exits 0. Completed Story 5.5.

## Senior Developer Review (AI)

**Reviewers:** `claude` CLI (sonnet) — completed; verdict: **"The proof IS genuine"** (real RF `${STATUS}` failure → live repair → real pass; honest `runnable_success`; clean layering). `kilo` CLI (minimax-m2.7) — timed out with no output (provider contention with an unrelated concurrent kilo job). Finalized on the claude review.

### claude/sonnet — outcome: Changes Requested (all resolved)

- [x] High — no `try/finally` → `EXECUTION_CONTEXTS` leak on exception → proof body wrapped in `try/finally`; `rf_close_session` always runs.
- [x] High — `rf_open_session` error not guarded before `["session"]` → early `runnable_success=False` proof if open is not ok.
- [x] High — proof script always exited 0 → exits 1 when `runnable_success` is false.
- [x] Med — `reproduced_failure` accepted any `ok=False` → now requires `error.code == "step-failed"` (real RF execution boundary crossed).
- [x] Med — hidden policy dependency could silently fail the proof → `_require_proof_policy()` raises a clear error when `CONTEXT_WRITE`/`INSPECTION_SNAPSHOT` are unavailable.
- [x] Med — test `failed_tool_calls >= 1` too permissive → asserts `== 1` and `tool_calls == 7`.
- [x] Med — round-trip test was tautological → asserts concrete values (`tool_calls == 7`, `failed_tool_calls == 1`, `runnable_success` true, 7 calls).
- [ ] Low (noted) — `failed_tool_calls` includes a close failure; documented as intentional (close succeeds in the happy path, so the count is 1).
- [ ] Low (pre-existing, not this story) — `close()` runs `shutil.rmtree` outside `_suppress_streams`; latent multi-thread concern, left as-is.

Clean areas confirmed by claude: `record()` captures `ok` faithfully; `close_session` nulls the engine under lock then closes outside; deterministic JSON (`sort_keys`, `extra="forbid"`); `app_inspect_state("app_context")` is a substantive live read; no `rfmcp_cli` imports.
