# Sprint Change Proposal — Live Robot Framework Execution Engine (FR-2 realization)

- **Date:** 2026-05-27
- **Author:** Many (with Developer agent)
- **Trigger source:** Investigation `mcp-core-stepwise-fr2` (`_bmad-output/implementation-artifacts/investigations/mcp-core-stepwise-fr2-investigation.md`)
- **Change scope classification:** **Major** (new epic + architecture decision + requirement clarification)
- **Review mode:** Incremental (all five edits approved)

## Section 1 — Issue Summary

The MCP Core's stepwise repair surface does not execute Robot Framework keywords. The `LiveRepairStepper` accepts an injectable `step_executor` that defaults to `None` and is never wired in production (`packages/rfmcp_core/src/rfmcp_core/runtime/stepper.py:32,79`); a successful step merely records the instruction string (`:101`). Runtime context is a seeded placeholder dict (`runtime/session.py:24`) and `app_inspect_state` returns synthetic fixtures (`runtime/snapshot.py:64`, `"synthetic": true`).

**Evidence (reproduced):** Running `rf_execute_repair_step("Should Be Equal    1    2")` returns `ok: true` ("Recorded a bounded repair step") — an assertion that must fail under `robot`. The same input on the original `manykarim/rf-mcp` returns a genuine `robot.errors.HandlerExecutionFailed: 1 != 2`. The original executes keywords against a real RF runtime (`EXECUTION_CONTEXTS`, namespace, `BuiltIn`) and supports attach to a live process.

This conflicts with **PRD FR-2**, which already requires "stepwise execution plus retrieval of application state … and getting and setting Robot Framework runtime context including variables, libraries, and keyword-relevant state." Epic 2 shipped the bounded **contract surface** (7-tool allowlist, schemas, policy gating, error envelope) as a **simulation scaffold**; the live behavior FR-2 describes was never implemented.

## Section 2 — Impact Analysis

- **Epic Impact:**
  - **Epic 2 (done):** stays done. Its delivered scope — bounded allowlist, schemas, policy/transport gating, structured errors — is genuinely complete and becomes Epic 5's foundation. The gap is a *new capability layer*, not a defect in stories 2.1–2.4.
  - **Epic 3 (done):** unaffected (stateless CLI/skill generation + refactor; real `robot` subprocess execution already lives here).
  - **Epic 4 (backlog):** stories **4.4** (CI flagship proof) and **4.5** (benchmark evidence) must exercise the live MCP path. Epic 5 should land before Epic 4's proof/benchmark stories.
  - **Epic 5 (new):** the live execution engine.
- **Story Impact:** five new stories (5.1–5.5). No existing story rewritten.
- **Artifact Conflicts:**
  - **PRD** — FR-2 testable consequences tightened so a scaffold can no longer pass (intent unchanged).
  - **Architecture** — new "Live Execution Engine for the MCP Core" subsection + implementation-sequence step.
  - **Epics** — Epic List, FR coverage map, and full Epic 5 section added.
  - **sprint-status.yaml** — Epic 5 + 5 stories registered as `backlog`.
  - **docs/mcp-live-repair-boundary.md** — execution model documented.
- **Technical Impact:** new `runtime/execution.py` (in-process RF context); `stepper.py`, `session.py`, `context.py`, `snapshot.py` re-pointed from simulation to live state; opt-in attach bridge under existing `security/attach_policy.py`; library-dependent app-state capture (Browser/Selenium/Requests). Perf concern already noted at `architecture.md:500` ("stepwise execution overhead").

## Section 3 — Recommended Approach

**Hybrid = Direct Adjustment + minor requirement clarification.** Add a new Epic 5 within the existing structure and tighten FR-2's testable wording.

- **Option 1 — Direct Adjustment (new Epic 5):** Viable. **Effort: High. Risk: Medium.** Chosen.
- **Option 2 — Rollback:** Not viable. There is nothing to roll back; the scaffold is a useful, correct foundation (contracts/surface/policy).
- **Option 3 — MVP review/reduce:** Not needed. FR-2 was always MVP scope; this realizes it. Timeline extends but scope does not shrink.

**Rationale:** Keeps Epic 2's history honest and intact, composes with Robot Framework's own runtime instead of reimplementing it, preserves the bounded allowlist and local-first safety model, and gives Epic 5 a crisp definition of done.

**User decisions captured:**
- Execution engine: **in-process + opt-in attach** (both).
- Plan shape: **new Epic 5** (Epic 2 stays done).
- App-state scope: **full** (real execution AND real app-state inspection in this change).

## Section 4 — Detailed Change Proposals (all applied)

### Epics (`_bmad-output/planning-artifacts/epics.md`)
- FR coverage map FR2 → now "Epic 2 (bounded surface/contracts) and Epic 5 (real live execution, runtime context, and application-state inspection)".
- Epic List → added Epic 5 entry (FR1, FR2, FR10, FR15 realization upgrade).
- Added full **Epic 5** section with Stories 5.1–5.5 and Given/When/Then acceptance criteria:
  - 5.1 Execute Real Keywords in an In-Process Live RF Context (also owns the `repair` → generic-session rename)
  - 5.2 Back Runtime Context Get/Set With the Live Namespace
  - 5.3 Back Approved Inspection Snapshots With Real Library State
  - 5.4 Add the Opt-In Attach Bridge to a Running RF Process
  - 5.5 Prove the Live MCP Repair Path End-to-End

### Naming cleanup (folded into Epic 5, Story 5.1)
The general live-session primitive carried a misleading `repair` qualifier. Story 5.1 drops it because the capability (run a real keyword in live context, hold variables, inspect state, attach) serves repair, authoring, and exploration — matching the original `manykarim/rf-mcp` (`manage_session` / `execute_step` / `get_session_state`) and the PRD glossary ("Live RF Context" is distinct from "Repair Workflow", `prd.md:71,77`). Pre-v1, so the rename is cheapest now, before Epic 5 builds more code on these names.

| Before | After |
| --- | --- |
| `rf_open_repair_session` | `rf_open_session` |
| `rf_get_repair_session` | `rf_get_session` |
| `rf_execute_repair_step` | `rf_execute_step` |
| `rf_close_repair_session` | `rf_close_session` |
| `LiveRepairSessionStore` / `LiveRepairStepper` | `LiveSessionStore` / `LiveStepper` |
| `RepairSessionSummary` / `RepairStepResult` | `SessionSummary` / `StepResult` |
| `repair-session.schema.json` / `repair-step-result.schema.json` | `session.schema.json` / `step-result.schema.json` |

**Retained `repair`** (genuinely repair-specific): `repair_diagnostics`, `repair_hints`, `RepairDiagnosticResult`, `repair-diagnostic-result.schema.json`, the Browser Library flagship repair skill, and FR-15. `rf_get_context` / `rf_set_context` / `app_inspect_state` already carried no `repair` qualifier and are unchanged.

### PRD (`prds/prd-rfmcp-reloaded-2026-05-23/prd.md` + `.decision-log.md`)
- FR-2 consequences rewritten: real keyword execution, real pass/fail ("never a recorded no-op"), state persistence across steps, real app-state from loaded library instances, real get/set of runtime context.
- Decision-log entry dated 2026-05-27 recording the clarification and its trigger.

### Architecture (`architecture.md`)
- New subsection **"Live Execution Engine for the MCP Core"** (in-process engine via RF public APIs; stepper/session/context/snapshot re-pointed; real failure propagation; opt-in attach bridge; library-sourced app-state).
- Implementation Sequence: new step 6 ("Wire the live Robot Framework execution engine …"), subsequent steps renumbered.

### Sprint status (`implementation-artifacts/sprint-status.yaml`)
- `epic-5: backlog` + 5 story keys `backlog` + `epic-5-retrospective: optional`; `last_updated` bumped to 2026-05-27.

### Boundary doc (`docs/mcp-live-repair-boundary.md`)
- `rf_execute_repair_step` and `app_inspect_state` rows reworded for real execution; new "Execution Model" section.

## Section 5 — Implementation Handoff

- **Scope class: Major** → PM/Architect own Epic 5 shaping (done here), then standard story cycle.
- **Next workflow steps:**
  1. `bmad-create-story` → draft **Story 5.1** (in a fresh context window).
  2. `bmad-create-story` (validate) → `bmad-dev-story` → `bmad-code-review`, repeating per story.
  3. Sequence Epic 5 **before** Epic 4 stories 4.4 / 4.5 so the live path is a release gate.
- **Success criteria:** `rf_execute_repair_step` runs real keywords with real pass/fail; variables persist across steps; `rf_get_context`/`rf_set_context` and `app_inspect_state` reflect live state; attach is opt-in/off-by-default/loopback-only; the flagship Browser repair is proven end-to-end through MCP and recorded in benchmark evidence.

## Section 6 — Checklist Record

- §1 Trigger & Context — Done. §2 Epic Impact — Done (4.4/4.5 dependency flagged). §3 Artifact Conflicts — Done (PRD/Arch/Epics/sprint-status/boundary-doc; UX N/A). §4 Path Forward — Done (Hybrid/Option 1). §5 Proposal Components — Done. §6 Final Review — pending user approval below.
