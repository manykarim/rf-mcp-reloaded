# Investigation: How the MCP Core implements stepwise execution against FR2 (+ comparison to manykarim/rf-mcp)

## Hand-off Brief

1. **What happened.** Exploration: traced how rfmcp-reloaded's MCP Core implements stepwise keyword execution against FR2, then compared it feature-for-feature with the original `manykarim/rf-mcp` (RobotMCP).
2. **Where the case stands.** **Concluded, High confidence.** rfmcp-reloaded ships the FR2 *contract/state-machine surface* (session lifecycle, step bookkeeping, context store, snapshot contracts, policy gating) but does **not execute Robot Framework keywords** — the executor is an injectable seam that defaults to `None`. The original `rf-mcp` executes keywords for real against a live RF runtime. Both behaviors confirmed by running experiments.
3. **What's needed next.** Decision for the user: treat the empty `step_executor` seam as intended v1 scope or as a gap to close. No code change made.

## Case Info

| Field            | Value                                                                      |
| ---------------- | -------------------------------------------------------------------------- |
| Ticket           | N/A (slug: mcp-core-stepwise-fr2)                                          |
| Date opened      | 2026-05-27                                                                 |
| Status           | Concluded                                                                  |
| System           | rfmcp-reloaded (uv workspace, FastMCP) vs. manykarim/rf-mcp @ /tmp/rf-mcp-original |
| Evidence sources | source code both repos; Story 2.1/2.2 + Epic-2 retro; two executed experiments |

## Problem Statement

How does the MCP Core implement stepwise keyword execution against FR2 ("Support interactive repair workflows that preserve runtime context and application inspection state across steps")? Then (follow-up): compare feature-wise to the stepwise execution in https://github.com/manykarim/rf-mcp, cloning and running experiments.

## Evidence Inventory

| Source   | Status    | Notes     |
| -------- | --------- | --------- |
| reloaded `runtime/stepper.py`, `session.py`, `context.py`, `snapshot.py` | Available (read) | Core engine — simulated |
| reloaded `rfmcp_mcp` tools + `_registry.py` + `server.py` | Available (read) | 7-tool bounded surface |
| reloaded `models/payloads.py` | Available (read) | FR2 contract types |
| original `manykarim/rf-mcp` @ /tmp/rf-mcp-original | Available (cloned, depth 50) | Real RF execution engine |
| original `execution_coordinator.py`, `keyword_executor.py`, `library_manager.py`, `mcp_attach.py`, `server.py` | Available (read/grep) | Real execution path |
| Experiment A (reloaded) `/tmp/exp_reloaded.py` | Executed | Output captured below |
| Experiment B (original) `/tmp/exp_original.py` | Executed | Output captured below |

## Confirmed Findings

### Finding 1: rfmcp-reloaded's stepwise execution never runs a keyword — the executor is an empty seam

**Evidence:** `packages/rfmcp_core/src/rfmcp_core/runtime/stepper.py:28-35,78-108`.

`LiveRepairStepper.__init__` takes `step_executor: Callable[[str, str], None] | None = None`. `execute_step` only calls it `if self._step_executor is not None` (line 79). On success it just calls `self._store.record_step(...)` and returns `detail="Recorded a bounded repair step against the active live session."` The MCP tool factory `build_execute_step_tool(store)` (`rf_execute_step.py:12`) constructs `LiveRepairStepper(store)` with **no** executor, and `server.py:18` wires tools via `definition.factory(session_store)` — so the production server's executor is always `None`. A repo-wide grep shows `step_executor` is supplied a real callable **only in tests** (`tests/test_mcp_live_repair_surface.py:116,210`, and only to raise `InterruptedError`).

### Finding 2: "Runtime context" and "application inspection state" are in-memory placeholders / synthetic fixtures

**Evidence:** `session.py:24-27` seeds `rf_context = {"${CURRENT_TEST}": "Repair Session"}` and a static `libraries=["BuiltIn","Collections"]`. `rf_get_context`/`rf_set_context` (`context.py:61-129`) read/write that dict. `snapshot.py:56-159` returns `{"synthetic": True, "source": "repair-session-fixture", ...}` with hardcoded DOM/accessibility/screenshot/API/app payloads. No DOM, browser, or live app is ever touched.

### Finding 3: The only real RF in reloaded is static libdoc + subprocess proof in the CLI/skill path — not the MCP surface

**Evidence:** The single real RF import in `packages/` is `from robot.libdocpkg import LibraryDocumentation` in CLI grounding (`rfmcp_cli/.../workflows/grounding.py:8`) — static documentation parsing. Real *execution* happens only as a subprocess `robot` run in the stateless flagship path: `rfmcp_cli/.../workflows/generation.py:76-115` (`_run_robot_execution` → `subprocess.run([... "robot" ...])` → `ExecutionProof` with real return codes) and `rfmcp_skills/.../definitions/browser_library_repair.py:216-236`. This is what the Epic-2 retro means by "real Robot execution" (`epic-2-retro-2026-05-26.md:58,110`) — the CLI/skill proof, **not** the MCP live stepper.

### Finding 4: rfmcp-reloaded MCP surface is deliberately bounded to 7 tools

**Evidence:** `rfmcp_mcp/.../tools/_registry.py:15,26-74`. `MAX_USER_FACING_TOOLS = 7`; allowlist = `rf_open_repair_session`, `rf_get_repair_session`, `rf_execute_repair_step`, `rf_close_repair_session`, `rf_get_context`, `rf_set_context`, `app_inspect_state`. A hard `RuntimeError` guards against exceeding 7. Each tool carries a `live_state_justification` string.

### Finding 5: manykarim/rf-mcp executes keywords against a real, live Robot Framework runtime

**Evidence:** `/tmp/rf-mcp-original/src/robotmcp/components/execution/execution_coordinator.py:73-135` (`execute_step` → `keyword_executor.execute_keyword`); `keyword_executor.py` (165 KB real executor); `core/library_manager.py:192-194` instantiates real `BuiltIn()`, `:418-430` uses `from robot.running.context import EXECUTION_CONTEXTS` and `current_context.namespace.get_library_instance(...)`. Attach mode runs keywords in an external live RF process: `attach/mcp_attach.py:347-349,428-433` (`bi.run_keyword(name, *args)`). ~45 MCP tools incl. `execute_step`, `execute_flow`, `execute_batch`, `execute_if`, `execute_for_each`, `execute_try_except`, `build_test_suite`, `run_test_suite`, `manage_attach`, `get_application_state`, `get_page_source`, `set_variables`, `evaluate_expression`.

### Finding 6 (experiments): identical inputs, opposite behavior

**Experiment A — reloaded** (`/tmp/exp_reloaded.py`, run via `uv run`):
- `execute_step("Should Be Equal    1    2")` → `ok: true`, `detail: "Recorded a bounded repair step…"`, `step_count` incremented. **No failure, no execution.**
- `app_inspect_state(dom)` → `payload.synthetic == true`, `html: "<body data-rfmcp='repair-session'></body>"`.

**Experiment B — original** (`/tmp/exp_original.py`, isolated venv editable install):
- `execute_step("Evaluate", ["1 + 2"], assign_to="result")` → `success: true`, `output: "3"`, `assigned_variables: {"${result}": 3}` (real value in a live namespace).
- `execute_step("Should Be Equal", ["1","1"])` → `pass`, `output: "OK"`.
- `execute_step("Should Be Equal", ["1","2"])` → `success: false`, `status: "fail"`, `error: "Keyword execution failed: 1 != 2"`; stderr shows real `robot.errors.HandlerExecutionFailed: 1 != 2` from `robot/running/librarykeywordrunner.py`.
- `execute_step("Log", ["Result is ${result}"])` → `pass` (resolved the live variable set two steps earlier).

The same failing assertion (`1 != 2`) is a no-op "recorded step" in reloaded and a genuine RF failure in the original — direct proof of simulated vs. real execution.

## Feature Comparison: stepwise execution

| Capability | rfmcp-reloaded (MCP Core) | manykarim/rf-mcp (RobotMCP) |
| --- | --- | --- |
| Runs a real RF keyword | **No** — records instruction string (`stepper.py:101`) | **Yes** — `keyword_executor.execute_keyword` via live RF |
| Keyword failure surfaces | No (always `ok:true` unless session bad / InterruptedError) | Yes (real `status:fail`, RF error) |
| Return values / variable assignment | No (`set_context` writes a placeholder dict) | Yes (`assign_to`, live namespace) |
| Variable resolution across steps | Stored verbatim, never evaluated | Yes (`${result}` resolved by RF) |
| Live app/browser state | Synthetic fixtures (`snapshot.py:64`) | Real DOM/page source/screenshots |
| Attach to running RF process | No (`attach_requested` flag recorded, unused) | Yes (`mcp_attach.py`, external bridge) |
| Control flow (if/for/try) | No | Yes (`execute_if/for_each/try_except`) |
| Build/run a suite from steps | No (CLI subprocess path only) | Yes (`build_test_suite`, `run_test_suite`) |
| Tool count | 7 (hard cap) | ~45 |
| Output contract / schema | Strong (pydantic, JSON Schema export) | Lighter, dict-based |
| Policy/capability gating, provenance | Yes (first-class) | Limited |

**Net:** the two are at different layers. The original is a working live RF execution engine with a broad tool surface. rfmcp-reloaded re-architects the *surface and contracts* of the narrow live-state slice (FR1–FR3) — bounded tools, schemas, policy, provenance — but the actual keyword-execution engine behind `rf_execute_repair_step` is an unimplemented injection seam (`step_executor=None`).

## Conclusion

**Confidence:** High (Confirmed in code + reproduced by two executed experiments).

rfmcp-reloaded satisfies FR2 **as a bounded contract/state-machine surface**: session lifecycle, step accounting, runtime-context get/set, approved-inspection snapshot kinds, transport/policy gating, and shared structured errors — all delivered and tested. It does **not** yet preserve or act on *real* runtime context: keyword execution is a deliberate seam (`step_executor`) that production never wires, context is a placeholder dict, and snapshots are synthetic fixtures. The original `manykarim/rf-mcp` is the opposite — a real, broad live-execution engine. The "real Robot execution" cited in the Epic-2 retro is the stateless CLI/skill subprocess proof, not the MCP stepwise path.

This matches the PRFAQ's own framing that "the hard part is proving which operations truly require a live execution context" (`prfaq:133`) — reloaded has nailed the *seam definition* and contracts but has not (yet) reconnected a live RF engine to it.

## Recommended Next Steps

### Fix direction (only if live execution is in-scope for v1)
Wire a real executor into the seam: implement a `step_executor` (or replace `LiveRepairStepper`) backed by RF's `EXECUTION_CONTEXTS`/`BuiltIn` (as the original does in `library_manager.py:418-430`) or by the attach bridge pattern (`mcp_attach.py`). Snapshots in `snapshot.py` and context in `session.py` would then read live state instead of fixtures. Scope is non-trivial (this is the original's largest module).

### If the seam is intended v1 scope
Document explicitly (in `docs/mcp-live-repair-boundary.md`) that the MCP stepwise surface is a contract scaffold and that real execution is provided via the CLI/skill subprocess proof, so the synthetic nature is not mistaken for live behavior.

### Suggested skills
- `bmad-correct-course` — if this changes Epic 2/4 scope or the FR2 acceptance interpretation.
- `bmad-quick-dev` — if wiring a minimal real `step_executor` is desired as a contained task.

## Reproduction Plan

- Reloaded: `cd /home/many/workspace/rfmcp-reloaded && uv run python /tmp/exp_reloaded.py`
- Original: `cd /tmp/rf-mcp-original && .venv-exp/bin/python /tmp/exp_original.py`

## Side Findings

- Reloaded allowlist is 7 tools but `_registry.py` comment lineage and Story 2.1 dev notes reference a "4-tool" v1; tools 5-7 (context/inspection) were added in Stories 2.2-2.4. (`_registry.py:15`)
- `session.py:114-129 configure_capabilities` and `attach_requested` are recorded but have no execution effect in the current simulated engine — latent hooks for a future real executor.
