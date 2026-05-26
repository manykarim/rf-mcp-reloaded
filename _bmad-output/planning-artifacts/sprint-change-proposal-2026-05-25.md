---
stepsCompleted:
  - 1
  - 2
  - 3
  - 4
  - 5
inputDocuments:
  - "/home/many/workspace/rfmcp-reloaded/_bmad-output/planning-artifacts/prds/prd-rfmcp-reloaded-2026-05-23/prd.md"
  - "/home/many/workspace/rfmcp-reloaded/_bmad-output/planning-artifacts/architecture.md"
  - "/home/many/workspace/rfmcp-reloaded/_bmad-output/planning-artifacts/epics.md"
  - "/home/many/workspace/rfmcp-reloaded/_bmad-output/planning-artifacts/implementation-readiness-report-2026-05-25.md"
mode: "batch-autonomous"
workflowType: "sprint-change-proposal"
project_name: "rfmcp-reloaded"
user_name: "Many"
date: "2026-05-25"
completedAt: "2026-05-25"
status: "complete"
---

# Sprint Change Proposal

## Issue Summary

### Trigger

The change trigger is the implementation-readiness gate captured in [implementation-readiness-report-2026-05-25.md](/home/many/workspace/rfmcp-reloaded/_bmad-output/planning-artifacts/implementation-readiness-report-2026-05-25.md:1). No implementation story exposed the issue yet; the problem was discovered before Phase 4 during planning validation.

### Core Problem Statement

The current epic/story plan is traceable to the PRD, but it is not shaped well enough for implementation under the BMad epic/story quality standard. The most important defects are:

- Epic 1 is framed as a technical-foundation milestone rather than a user-value epic.
- Several early stories are architecture or platform slices disguised as user stories.
- The first meaningful repair outcome is buried behind a long chain of technical precursor stories.
- Epic 4 mixes operator value with release-engineering plumbing, weakening epic independence and story clarity.

### Evidence

- The readiness report marked the plan **NEEDS WORK** and identified critical epic-quality violations.
- The current [epics.md](/home/many/workspace/rfmcp-reloaded/_bmad-output/planning-artifacts/epics.md:131) still opens with “Bootstrap a Trusted Contributor Foundation,” which is a technical milestone, not a standalone operator outcome.
- Story sequencing in Epic 2 explicitly makes the flagship repair workflow depend on Stories 2.1 through 2.5 plus Epic 1 foundations, which is a structural warning rather than a usable first thin slice.

## Impact Analysis

### Epic Impact

#### Epic 1

Current state:
- Too much pure platform bootstrapping is exposed as a top-level epic.
- User value exists only indirectly through Story 1.5.

Required change:
- Reframe the epic around the first operator-visible deterministic validation outcome.
- Keep starter-template setup, contracts, and policy work only insofar as they directly enable that first outcome.

#### Epic 2

Current state:
- The repair workflow is structurally correct but over-decomposed into technical layers before value is delivered.

Required change:
- Collapse registry, session, context, and inspection work into a thinner bounded repair-session capability.
- Pull the first successful repair path earlier.

#### Epic 3

Current state:
- Mostly sound, but story-level hinting and negative-path coverage are uneven.

Required change:
- Keep the epic, but tighten story acceptance criteria and explicitly carry preventive hinting into refactor/regenerate work.

#### Epic 4

Current state:
- The epic mixes host onboarding value with release/build/CI mechanics.

Required change:
- Reframe the epic around supported-host onboarding and reference-workflow completion.
- Treat renderer-family work and release gates as supporting stories rather than the epic’s core identity.

### Story Impact

- Stories 1.2, 1.3, 1.4, 2.1, and 2.2 need consolidation or reframing.
- Story 2.6 remains valid as a flagship target, but it should depend on fewer precursor stories.
- Story 4.1 is too broad because it spans five host outputs in one unit.
- Story 4.4 is valid but should be clearly downstream of stabilized workflow contracts and host outputs.

### Artifact Conflicts

#### PRD

No direct PRD conflict. The PRD’s goals, MVP shape, host set, and requirement inventory remain viable.

Required adjustment:
- None mandatory now.
- Optional future clarification: once the corrected epics land, add a short implementation-note update referencing story-level traceability expectations and behavioral-proof standards if those remain ambiguous.

#### Architecture

No core architecture conflict. The architecture already describes the bounded MCP surface, shared contract model, hint provenance, and first-class host set that the corrected epic plan should preserve.

Required adjustment:
- None mandatory now.
- Optional future clarification: add a short note in the implementation-sequence or validation section explaining that technical foundation work is intentionally grouped beneath user-value epics rather than surfaced as standalone milestone epics.

#### UX

No UX artifact exists and no standalone UI surface currently forces a UX rewrite.

Required adjustment:
- None for this correction.

### Technical Impact

- No code rollback is required because implementation has not started.
- The primary impact is backlog reorganization and story reshaping.
- Sprint planning should not begin until the corrected epic/story structure is accepted.

## Path Forward Evaluation

### Option 1: Direct Adjustment

Assessment:
- Modify the current epics and stories in place.
- Keep the PRD and architecture intact.
- Replace the weakest epic framing and consolidate technical precursor stories.

Effort estimate: Medium
Risk level: Low to Medium
Status: Viable

Why:
- The planning artifacts are already rich and traceable.
- The problem is structural, not conceptual.
- The fastest path is to repair the story decomposition rather than re-open product scope.

### Option 2: Potential Rollback

Assessment:
- Reverting completed implementation is not relevant because implementation work has not started.

Effort estimate: Low
Risk level: Low
Status: Not viable

Why:
- There is no implemented backlog or code slice to roll back.
- The real need is plan restructuring, not rollback.

### Option 3: PRD MVP Review

Assessment:
- Reduce or redefine MVP scope if the current plan is exposing a deeper product mismatch.

Effort estimate: Medium to High
Risk level: Medium
Status: Not currently viable as the primary response

Why:
- The readiness findings do not show a broken MVP.
- They show a poor translation from PRD/architecture into epics and stories.
- Reopening MVP scope now would create churn without resolving the planning-shape problem.

### Recommended Path

Selected approach: Option 1, Direct Adjustment

Rationale:
- It addresses the actual defect: poor epic/story decomposition.
- It preserves validated upstream artifacts.
- It minimizes churn and keeps momentum.
- It is the lowest-risk path that restores implementation readiness without pretending the current epic structure is acceptable.

Timeline impact:
- Short delay to revise `epics.md`
- No reason to delay architecture or PRD unless new conflicts appear during rewrite

## Detailed Change Proposals

### Artifact Type: Epics and Stories

#### Proposal 1: Reframe Epic 1 Around the First Operator Outcome

Epic: 1
Section: Epic title, goal, and Story 1 cluster

OLD:
- **Epic 1: Bootstrap a Trusted Contributor Foundation**
- Goal focuses on workspace, contract, policy, and observability baseline.

NEW:
- **Epic 1: Deliver the First Deterministic Validation Workflow**
- Goal: An Automation Engineer can bootstrap the toolchain, run a deterministic validation command, and receive structured failure output from a clean project setup.

Rationale:
- This preserves the required starter-template story while anchoring the epic in operator-visible value instead of pure platform setup.

#### Proposal 2: Replace the Current Epic 1 Story Sequence With a Thinner Value Path

Epic: 1
Section: Stories

OLD:
- 1.1 Set Up Initial Project From Starter Template
- 1.2 Define the Authoritative Contract and Schema Pipeline
- 1.3 Establish Local Policy and Attach-Safety Defaults
- 1.4 Add Structured Logging and Benchmark Event Foundations
- 1.5 Ship a Minimal Validate CLI Slice on the Shared Contracts

NEW:
- 1.1 Initialize the project from the selected starter template and baseline toolchain
- 1.2 Publish bootstrap documentation and provider/package scaffold rules for contributors
- 1.3 Define shared validation contracts and schema sync
- 1.4 Ship deterministic `validate` workflow with structured failure output
- 1.5 Add validation diagnostics, policy defaults, structured logging, and benchmark event foundations

Rationale:
- This preserves the mandatory starter-template story while removing the oversized “do everything in 1.1” shape.
- Observability and benchmark-event work remain explicit instead of disappearing.
- FR14 remains owned by Epic 4 rather than being reintroduced ambiguously into Epic 1.

#### Proposal 3: Reshape Epic 2 Into a Thin Repair Capability Without Creating a Mega-Story

Epic: 2
Section: Story structure

OLD:
- 2.1 Implement the Bounded FastMCP Surface and Tool Registry
- 2.2 Build Runtime Session and Stepwise Execution Services
- 2.3 Add Robot Context and Approved Inspection Snapshot Services
- 2.4 Build Repair and Validation CLI Workflows on the Shared Contracts
- 2.5 Implement Provenance-Aware Hint Resolution for Repair Workflows
- 2.6 Deliver the Browser Library Flagship Repair Workflow

NEW:
- 2.1 Expose a bounded live repair session surface
- 2.2 Add Robot Framework context access and approved inspection snapshots
- 2.3 Deliver repair diagnostics, validation fallback, and provenance-aware hinting
- 2.4 Complete the Browser Library flagship repair workflow

Rationale:
- The current sequence is correct in engineering terms but too decomposed to function as a healthy story chain.
- The new structure preserves an intermediate value-bearing slice between bounded session infrastructure and the flagship repair outcome.
- It avoids replacing a long chain with one oversized precursor story.

#### Proposal 4: Tighten Epic 3 by Explicitly Covering Refactor Hinting and Negative Paths

Epic: 3
Section: Story 3.3 and related acceptance criteria

OLD:
- Refactor/regenerate flow focuses on stable path, validation, and reporting.

NEW:
- Add explicit acceptance criteria that refactor/regenerate workflows surface preventive or corrective hint guidance for known failure patterns.
- Add negative-path acceptance criteria for partial refactor failure, validation regression, and required manual follow-up.

Rationale:
- Epic 3 already carries the right value shape.
- It needs stronger implementation readiness and consistency with FR12 and NFR3.

#### Proposal 5: Reframe Epic 4 Around Host Onboarding Without Re-Creating Oversized Stories

Epic: 4
Section: Epic title, goal, and story grouping

OLD:
- **Epic 4: Deliver Portable Host Workflows and Release Proof**
- Stories split host bundles, install mapping, compatibility docs, CI gates, and benchmark evidence.

NEW:
- **Epic 4: Onboard Supported Hosts to Reference Workflows**
- Story grouping:
  - 4.1 Render supported-host outputs by renderer family
  - 4.2 Add install surfaces and fallback mapping
  - 4.3 Publish compatibility profiles and first-run onboarding
  - 4.4 Add CI compatibility, bundle validation, and release gates
  - 4.5 Produce benchmark-backed release evidence

Rationale:
- This makes the epic’s value legible to an operator.
- It keeps onboarding/compatibility separate from CI/release mechanics, which avoids widening the same stories already flagged as oversized.

#### Proposal 6: Add Explicit Story-Level Traceability and Dependency Notes

Artifact: `epics.md`
Section: Story metadata or appendix

OLD:
- FR traceability exists at epic level only, with broad story references embedded in prose.

NEW:
- Add a concrete story-level traceability table in `epics.md` with columns:
  - Story ID
  - Primary FRs
  - Secondary FRs
  - Allowed prerequisites
  - Forbidden forward dependencies
- Re-map FR ownership after the restructure so FR14 remains primarily owned by Epic 4 and no story inherits duplicate onboarding ownership accidentally.

Rationale:
- This reduces ambiguity during sprint planning and implementation.
- It also gives later reviewers a precise way to test whether the restructured stories remain aligned.

#### Proposal 7: Add Explicit Negative-Path Acceptance-Criteria Corrections

Artifact: `epics.md`
Section: Revised Story 1.1 successor, Story 3.3, Story 4.3, and Story 4.5

OLD:
- Negative-path acceptance criteria are inconsistent and often absent.

NEW:
- Add failure-path criteria for:
  - starter-template mismatch or incomplete baseline setup
  - unsafe or partially failing refactor/regenerate operations
  - onboarding flows that still require hidden prerequisites
  - benchmark/release evidence gaps or missing host-validation coverage

Rationale:
- The readiness gate did not only object to epic structure.
- It also objected to happy-path-only acceptance criteria, and the correction proposal should close that defect explicitly.

### Artifact Type: PRD

No mandatory PRD text change is recommended in this proposal.

Rationale:
- The readiness findings indicate that the PRD is structurally sound.
- The fault lies in decomposition, not in product scope or requirement intent.

### Artifact Type: Architecture

No mandatory architecture text change is recommended in this proposal.

Optional update if the team wants stronger traceability:
- Add a short note under implementation sequencing or validation explaining that foundation work is intentionally embedded in value-delivering epics and not treated as standalone milestone epics.

Rationale:
- The architecture is not what failed the readiness gate.
- The epic/story translation is what failed it.

### Artifact Type: UX

No UX change proposal.

Rationale:
- No UX artifact exists.
- The current course correction is not blocked on a standalone UX specification.

## PRD MVP Impact and High-Level Action Plan

### MVP Impact

The MVP does not need to change.

What changes:
- The way implementation work is packaged into epics and stories
- The sequence and granularity of the first implementation slices

What does not change:
- MVP host set
- Narrow MCP boundary
- Shared contract requirement
- Hint provenance requirement
- Flagship repair and generation workflows

### High-Level Action Plan

1. Update `epics.md` using the change proposals above.
2. Re-run a critical review of the revised epics file.
3. Re-run implementation readiness against the revised artifact.
4. Only after the plan is clean, proceed to sprint planning.

### Dependencies and Sequencing

- `epics.md` correction must happen before sprint planning.
- Story-level traceability notes should land in the same revision as the epic restructure.
- No PRD or architecture rewrite is needed unless the corrected epics uncover a deeper mismatch.

## Implementation Handoff

### Scope Classification

Moderate

Why:
- No full replan is needed.
- No code rollback is needed.
- Backlog reorganization and story restructuring are required before implementation begins.

### Handoff Responsibilities

- Product Owner / Developer workflow:
  - Rewrite `epics.md` to adopt the corrected epic framing, thinner story chains, explicit story-level traceability table, and negative-path acceptance criteria.
  - Preserve FR coverage while reducing technical-story fragmentation.

- Reviewer / critical pass:
  - Re-check the revised epic/story artifact against readiness criteria and adversarial review criteria.

- Sprint planning workflow:
  - Generate implementation order only after the corrected epic/story set is accepted.

### Success Criteria

- Epic 1 is visibly about a user-completable validation outcome, not a foundation milestone.
- Epic 2 reaches a meaningful repair workflow in fewer precursor stories.
- Epic 4 reads as supported-host onboarding value rather than release plumbing.
- Story-level traceability and dependency notes are explicit enough for implementation handoff.
- A fresh readiness check no longer fails on epic quality as its primary blocker.

## Checklist Execution Record

### Section 1: Understand the Trigger and Context

- [x] 1.1 Trigger identified: readiness gate after planning validation, not an implementation story
- [x] 1.2 Core problem defined: poor epic/story decomposition
- [x] 1.3 Evidence gathered from readiness findings and current `epics.md`

### Section 2: Epic Impact Assessment

- [x] 2.1 Current epic containing trigger evaluated
- [x] 2.2 Epic-level changes defined
- [x] 2.3 Remaining epics reviewed for impact
- [x] 2.4 No new epics required; existing epics need reshaping
- [x] 2.5 Epic order should remain broadly sequential, but story grouping should change

### Section 3: Artifact Conflict and Impact Analysis

- [x] 3.1 PRD checked for conflict
- [x] 3.2 Architecture checked for conflict
- [N/A] 3.3 UX artifact conflict not applicable because no UX spec exists
- [x] 3.4 Secondary artifact impact documented for readiness and future sprint-planning flow

### Section 4: Path Forward Evaluation

- [x] 4.1 Direct adjustment evaluated as viable
- [x] 4.2 Rollback evaluated as not viable
- [x] 4.3 PRD MVP review evaluated as not primary path
- [x] 4.4 Recommended path selected: Option 1 Direct Adjustment

### Section 5: Sprint Change Proposal Components

- [x] 5.1 Issue summary created
- [x] 5.2 Epic and artifact impacts documented
- [x] 5.3 Recommended path and rationale documented
- [x] 5.4 MVP impact and high-level action plan defined
- [x] 5.5 Agent handoff plan established

### Section 6: Final Review and Handoff

- [x] 6.1 Checklist completion reviewed
- [x] 6.2 Proposal reviewed for consistency and specificity
- [x] 6.3 Current user request treated as approval to generate and finalize the proposal for implementation planning review
- [N/A] 6.4 `sprint-status.yaml` update not applicable because sprint planning has not yet created it
- [x] 6.5 Next steps and handoff plan confirmed within this proposal
