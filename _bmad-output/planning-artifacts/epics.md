---
stepsCompleted:
  - 1
  - 2
  - 3
  - 4
inputDocuments:
  - "/home/many/workspace/rfmcp-reloaded/_bmad-output/planning-artifacts/architecture.md"
  - "/home/many/workspace/rfmcp-reloaded/_bmad-output/planning-artifacts/prds/prd-rfmcp-reloaded-2026-05-23/prd.md"
  - "/home/many/workspace/rfmcp-reloaded/_bmad-output/planning-artifacts/prds/prd-rfmcp-reloaded-2026-05-23/addendum.md"
workflowType: "epics-and-stories"
project_name: "rfmcp-reloaded"
user_name: "Many"
date: "2026-05-25"
lastStep: 4
status: "complete"
completedAt: "2026-05-25"
---

# rfmcp-reloaded - Epic Breakdown

## Overview

This document provides the corrected epic and story breakdown for `rfmcp-reloaded`, decomposing the requirements from the PRD and Architecture into implementable stories sized for a single development agent. The structure emphasizes user-visible workflow value first, while still preserving the architecture's strict boundaries around live-state MCP usage, deterministic CLI fallbacks, provenance-aware hinting, and supported-host portability.

## Requirements Inventory

### Functional Requirements

FR1: Expose only the minimum live-state Robot Framework operations through a narrow MCP Core.

FR2: Support interactive repair workflows that preserve runtime context and application inspection state across steps.

FR3: Make live-state usage clearly bounded and documented so operators know when to use MCP versus stateless workflows.

FR4: Provide deterministic CLI commands for stateless high-value tasks including grounding, scaffolding, validation, and executable run verification.

FR5: Return CLI outputs in structured, machine-usable forms that agents can consume without ambiguous parsing.

FR6: Provide a deterministic validation path that proves generated or repaired Robot Framework artifacts are runnable and behaviorally aligned.

FR7: Package a small set of repeatable Skill Workflows for high-value Robot Framework jobs, especially repair, generation, and refactoring.

FR8: Ensure every flagship Skill Workflow degrades gracefully to an equivalent deterministic CLI fallback path.

FR9: Document host-aware skill behavior and support differences without claiming false uniformity across hosts.

FR10: Provide structured hints for keyword, argument, ambiguity, and usage failures so agents and operators can recover deliberately.

FR11: Augment incomplete library documentation with attributable workflow guidance while distinguishing official docs, curated guidance, and inference.

FR12: Use hinting preventively to reduce repeated authoring errors while keeping v1 guidance advisory by default.

FR13: Publish explicit Compatibility Profiles for the supported v1 hosts and their fallback paths.

FR14: Minimize first-run friction so a solo operator can reach first value without a sprawling setup story.

FR15: Ship at least one flagship end-to-end Repair Workflow for a failing Robot Framework test in a supported host.

FR16: Ship at least one runnable-test generation workflow that ends with deterministic runnable validation.

### NonFunctional Requirements

NFR1: Default to local, user-controlled workflows and clearly bound privileged or attach-style behavior.

NFR2: Keep MCP, CLI, skill, and contract surfaces stable enough that reference workflows do not drift unpredictably.

NFR3: Report failures in structured, actionable forms that help the operator or agent continue instead of restarting.

NFR4: Prefer portability across the declared host set over expanding breadth prematurely.

NFR5: Reduce scope and maintenance burden relative to the legacy broad-surface design.

NFR6: Keep hinting attributable, explainable, and clearly separated from execution truth.

### Additional Requirements

- Use a Python `uv` workspace monorepo as the implementation baseline, replacing the current minimal single-package scaffold.
- Keep `rfmcp_core.models` as the contract source of truth, expose stable imports through `rfmcp_core.contracts`, and generate JSON Schema artifacts into `assets/schemas/`.
- Share one structured error envelope and hint payload schema across CLI and MCP outputs.
- Implement a file-first YAML hint system under `assets/hints/` with `pluggy` providers, deterministic precedence rules, deduplication, and provenance retention.
- Enforce local policy and capability gating with attach disabled by default, loopback-only HTTP exposure, explicit opt-in, and no secret persistence in assets or generated caches.
- Keep the FastMCP tool surface bounded to live-state execution, runtime context, and approved application-state inspection only.
- Implement stateless workflows through a Typer CLI with both human-readable and `--json` outputs.
- Treat canonical skill definitions as a first-class layer in `packages/rfmcp_skills/`, backed by `assets/skills/`, rendered by `rfmcp_bundles/`, and installed through CLI surfaces.
- Produce compatibility and onboarding outputs for the first-class v1 hosts: Claude Code, GitHub Copilot, Codex, OpenCode, and KiloCode.
- Validate the product through GitHub Actions, schema sync checks, version compatibility matrices, compatibility-profile assertions, and flagship end-to-end scenarios.
- Capture structured logs and benchmark evidence for repair, generation, and refactor scenarios without introducing a remote telemetry dependency.
- Keep provider packages optional, prohibit provider MCP tool registration, and require provider behavior to import shared types from the public contracts layer.

### UX Design Requirements

No standalone UX design document was present in the planning artifacts. UX-specific work is therefore limited to CLI and host onboarding clarity, structured output readability, and documentation usability already captured by FR5, FR14, and the architecture requirements.

### FR Coverage Map

FR1: Epic 2 - Bounded live repair-session capability and approved live-state inspection.

FR2: Epic 2 (bounded surface/contracts) and Epic 5 (real live execution, runtime context, and application-state inspection) - persistent repair sessions, runtime context access, and flagship repair flow.

FR3: Epic 2 - Explicit MCP-versus-CLI boundary, policy enforcement, and repair workflow guidance.

FR4: Epic 1 and Epic 3 - Deterministic validation, grounding, scaffolding, and run-verification commands.

FR5: Epic 1 and Epic 3 - Shared contract-backed machine-usable outputs for validation and authoring workflows.

FR6: Epic 2 and Epic 3 - Runnable validation paths for repaired, generated, and refactored artifacts.

FR7: Epic 2 and Epic 3 - Canonical repair, generation, and refactor skill workflows.

FR8: Epic 2 and Epic 4 - Deterministic CLI fallback paths preserved for flagship workflows and host onboarding.

FR9: Epic 4 - Host-aware packaging, install behavior, and compatibility communication.

FR10: Epic 2 - Repair diagnostics and structured hinting for keyword and argument failures.

FR11: Epic 2 - Provenance-aware hint augmentation beyond raw library documentation.

FR12: Epic 2 and Epic 3 - Preventive and corrective advisory hinting for repair and authoring workflows.

FR13: Epic 4 - Explicit compatibility profiles, supported-host validation, and release evidence.

FR14: Epic 4 - First-run onboarding and supported-host guidance that gets an operator to a reference workflow quickly.

FR15: Epic 2 - Flagship Browser Library repair workflow with deterministic proof.

FR16: Epic 3 - Flagship runnable-test generation workflow with executable verification.

## Epic List

### Epic 1: Deliver the First Deterministic Validation Workflow
Automation Engineers and contributors can bootstrap the toolchain, run a deterministic validation command, and receive structured failure output from a clean local setup.
**FRs covered:** FR4, FR5

### Epic 2: Repair Failing Robot Tests with Live Context
Automation Engineers can open a bounded live repair session, inspect approved runtime context, receive provenance-aware repair diagnostics, and complete a Browser Library repair workflow without losing deterministic fallback paths.
**FRs covered:** FR1, FR2, FR3, FR10, FR11, FR12, FR15

### Epic 3: Generate and Refactor Runnable Robot Coverage
Automation Engineers can ground keywords, scaffold suites, generate runnable tests, and refactor existing Robot Framework artifacts with deterministic validation, guarded failure handling, and reusable skills.
**FRs covered:** FR6, FR7, FR12, FR16

### Epic 4: Onboard Supported Hosts to Reference Workflows
Operators can install and use the workflows across the supported hosts with clear compatibility guidance, deterministic fallback mapping, validated bundles, and benchmark-backed release proof.
**FRs covered:** FR8, FR9, FR13, FR14

### Epic 5: Wire a Live Robot Framework Execution Engine Behind the MCP Core
Automation Engineers get real stepwise keyword execution against persistent live Robot Framework state — real variables, imports, pass/fail, application-state inspection, and an opt-in attach path — replacing the bounded simulation that Epic 2 scaffolded.
**FRs covered:** FR1, FR2, FR10, FR15 (realization upgrade)

## Story Traceability Table

| Story ID | Primary FRs | Secondary FRs | Allowed Prerequisites | Forbidden Forward Dependencies |
| -------- | ----------- | ------------- | --------------------- | ------------------------------ |
| 1.1 | FR4 | FR5 | None | 1.2+, 2.x, 3.x, 4.x |
| 1.2 | FR4 | FR5 | 1.1 | 1.3+, 2.x, 3.x, 4.x |
| 1.3 | FR4, FR5 | N/A | 1.1, 1.2 | 1.4, 2.x, 3.x, 4.x |
| 1.4 | FR4, FR5 | N/A | 1.1, 1.2, 1.3 | 1.5, 2.x, 3.x, 4.x |
| 1.5 | FR5 | FR6, FR13 | 1.1, 1.2, 1.3, 1.4 | 2.x, 3.x, 4.x |
| 2.1 | FR1, FR2, FR3 | N/A | 1.1, 1.3 | 2.2+, 3.x, 4.x |
| 2.2 | FR1, FR2 | FR3 | 2.1 | 2.3+, 3.x, 4.x |
| 2.3 | FR3, FR6, FR10, FR11, FR12 | FR5 | 1.3, 1.4, 2.1, 2.2 | 2.4, 3.x, 4.x |
| 2.4 | FR2, FR7, FR8, FR15 | FR6 | 2.1, 2.2, 2.3 | 3.x, 4.x |
| 3.1 | FR4, FR5, FR12 | FR6 | 1.3, 1.4 | 3.2+, 4.x |
| 3.2 | FR6, FR12, FR16 | FR5 | 3.1 | 3.3+, 4.x |
| 3.3 | FR6, FR12 | FR7 | 3.1, 3.2 | 3.4+, 4.x |
| 3.4 | FR7, FR8, FR9 | N/A | 3.1, 3.2, 3.3 | 3.5, 4.x |
| 3.5 | FR6, FR16 | FR12 | 3.1, 3.2, 3.3, 3.4 | 4.x |
| 4.1 | FR9 | FR13 | 3.4 | 4.2+ |
| 4.2 | FR8, FR9 | FR13 | 4.1 | 4.3+ |
| 4.3 | FR13, FR14 | FR9 | 4.1, 4.2 | 4.4, 4.5 |
| 4.4 | FR13 | FR8, FR9 | 4.1, 4.2, 4.3 | 4.5 |
| 4.5 | FR13 | FR15, FR16 | 2.4, 3.5, 4.4 | None |

## Epic 1: Deliver the First Deterministic Validation Workflow

Convert the current placeholder repository into a usable validation baseline so contributors can bootstrap the toolchain and Automation Engineers can get structured validation feedback immediately.

### Story 1.1: Initialize the Project From the Selected Starter Template

As a maintainer,
I want to initialize the repository from the selected `uv` starter and baseline toolchain,
So that the project begins from the approved workspace shape instead of an ad hoc scaffold.

**Requirements:** FR4, NFR2, NFR5

**Acceptance Criteria:**

**Given** the current repository only contains a root `pyproject.toml`, `main.py`, and planning artifacts
**When** the workspace bootstrap story is implemented
**Then** the repository is initialized from the architecture-selected starter command `uv init --package rfmcp-reloaded`
**And** the root workspace configuration, shared `uv.lock`, and baseline tool versions match the architecture decision record
**And** the resulting layout is ready for follow-on package and contract work without inventing an alternate starter structure.

**Given** the local environment does not satisfy the baseline Python or `uv` expectations
**When** the bootstrap path is attempted
**Then** the failure is explicit about the mismatch
**And** the maintainer is given a deterministic next step rather than a silent partial setup.

### Story 1.2: Publish Contributor Bootstrap Rules and Workspace Package Scaffolds

As a contributor,
I want the workspace package scaffolds and contributor bootstrap rules to be explicit,
So that I can extend the project without guessing package ownership, provider boundaries, or verification commands.

**Requirements:** FR4, FR5, NFR2, NFR3

**Acceptance Criteria:**

**Given** the starter workspace exists
**When** the contributor scaffolding story is implemented
**Then** the project includes the intended package skeletons for `rfmcp_core`, `rfmcp_mcp`, `rfmcp_cli`, `rfmcp_skills`, `rfmcp_bundles`, and the first provider packages
**And** the bootstrap documentation explains package boundaries, provider scaffolding expectations, and the baseline verification commands contributors must run.

**Given** a contributor adds or modifies a package scaffold incorrectly
**When** they follow the documented bootstrap rules
**Then** the project structure rules make the inconsistency visible
**And** the contributor can correct the mistake without relying on hidden maintainer knowledge.

### Story 1.3: Define Shared Validation Contracts and Schema Sync

As a contributor,
I want one authoritative contract and schema-sync path for validation surfaces,
So that CLI, MCP, providers, and later host bundles consume stable payload shapes instead of drifting independently.

**Requirements:** FR4, FR5, NFR2, NFR3

**Acceptance Criteria:**

**Given** the workspace packages exist
**When** the contract story is implemented
**Then** `rfmcp_core.models` defines the canonical contract shapes and `rfmcp_core.contracts` exposes the supported public façade
**And** the shared error envelope, hint payload schema, hint pack schema, and skill-manifest schema are explicitly defined for downstream surfaces
**And** generated JSON Schema artifacts are written to `assets/schemas/` from the model layer rather than maintained separately.

**Given** a contributor changes a contract model
**When** they run the schema export and verification scripts
**Then** schema artifacts regenerate deterministically and verification fails on drift
**And** the one-way contract evolution path is documented clearly enough that later stories do not redefine payloads locally.

### Story 1.4: Ship Deterministic Validate Workflow With Structured Failure Output

As an Automation Engineer,
I want a deterministic validation command with structured failure output,
So that I can verify Robot Framework artifacts early instead of waiting for later workflow layers to exist.

**Requirements:** FR4, FR5, NFR2, NFR3

**Acceptance Criteria:**

**Given** the contract and schema pipeline exists
**When** the validation story is implemented
**Then** the project exposes a minimal `validate` command with human-readable output and a stable `--json` shape backed by the shared contracts
**And** the command gives a real operator-visible CLI workflow before the broader repair and generation epics complete.

**Given** validation fails on a malformed Robot Framework artifact or baseline mismatch
**When** the command returns the result
**Then** the output uses the shared structured error envelope with error code, severity, provenance, retryability, and suggested next step
**And** the failure does not require raw-log inspection to understand what to do next.

### Story 1.5: Add Validation Diagnostics, Local Policy Defaults, and Benchmark Event Foundations

As a maintainer,
I want validation diagnostics, local policy defaults, and structured benchmark events to be explicit,
So that later workflows have trusted evidence, bounded defaults, and reusable diagnostics rather than ad hoc instrumentation.

**Requirements:** FR5, NFR1, NFR2, NFR3, NFR5

**Acceptance Criteria:**

**Given** later epics must prove runnable outcomes, tool-call reductions, and benchmark results
**When** diagnostics and observability foundations are implemented
**Then** shared structured event shapes and logging utilities exist for CLI and MCP code paths
**And** benchmark capture remains local-first and does not require a remote telemetry backend.

**Given** privileged or attach-style behavior expands later
**When** policy defaults and diagnostics are reviewed
**Then** local policy assets keep loopback-only and explicit opt-in posture visible
**And** emitted diagnostics remain machine-readable and clearly distinguish observed facts from inferred guidance.

## Epic 2: Repair Failing Robot Tests with Live Context

Deliver a bounded live repair capability that lets Automation Engineers inspect approved runtime context, recover with deterministic diagnostics, and complete a Browser Library repair workflow without waiting on a full helper platform.

### Story 2.1: Expose a Bounded Live Repair Session Surface

As an Automation Engineer,
I want a bounded live repair session surface,
So that I can step through a repair investigation without recreating runtime state on every action.

**Requirements:** FR1, FR2, FR3, NFR2, NFR5

**Acceptance Criteria:**

**Given** the architecture reserves MCP for live-state needs only
**When** the live repair session story is implemented
**Then** the MCP package exposes only the allowlisted session and stepwise-repair tools over `stdio` and loopback-only HTTP
**And** session lifecycle, policy gating, and interrupted-step failures all use the shared structured error path
**And** stateless helpers such as grounding, scaffolding, and general generation are not registered as MCP tools.

**Given** a maintainer attempts to expand the repair surface later
**When** the boundary is reviewed
**Then** every added tool must be justified by a live-state need
**And** the docs make the MCP-versus-CLI decision boundary explicit.

### Story 2.2: Add Robot Framework Context Access and Approved Inspection Snapshots

As an Automation Engineer,
I want explicit Robot Framework context access and approved inspection snapshots,
So that a repair session can retrieve the evidence needed for diagnosis without broadening the MCP surface arbitrarily.

**Requirements:** FR1, FR2, FR3, NFR1, NFR3

**Acceptance Criteria:**

**Given** the bounded repair session surface exists
**When** context and inspection support is implemented
**Then** the runtime layer supports Robot Framework context get/set operations plus approved application inspection snapshots such as DOM, accessibility, screenshots, or last API response where policy allows
**And** those capabilities remain explicitly bounded to the allowlisted MCP tools.

**Given** a requested snapshot or context action exceeds local policy or session capabilities
**When** the request is evaluated
**Then** the call is denied through the shared structured error path
**And** the denial preserves provenance and the next safe action for the operator or skill.

### Story 2.3: Deliver Repair Diagnostics, Validation Fallback, and Provenance-Aware Hinting

As an Automation Engineer,
I want deterministic repair diagnostics, validation fallback, and provenance-aware hinting,
So that I can continue a repair even when live-state tools are unavailable or the failure mode is unclear.

**Requirements:** FR3, FR5, FR6, FR10, FR11, FR12, NFR3, NFR6

**Acceptance Criteria:**

**Given** a failing suite or resource change must be inspected outside MCP
**When** repair diagnostics and validation fallback are implemented
**Then** the CLI exposes stable commands with both readable output and `--json` payloads backed by the shared contracts
**And** validation and run-verification results identify likely keyword, library, and execution problems in structured form.

**Given** curated YAML packs, provider contributions, and inferred recovery suggestions may all contribute guidance
**When** the repair hint workflow runs
**Then** the system validates and loads file-based hint packs, discovers providers through `pluggy`, merges results deterministically, and emits provenance-rich hint payloads
**And** conflicts and deduplication behavior follow the architecture's precedence rules.

**Given** a repair scenario includes missing keywords, wrong arguments, ambiguous usage, or unavailable live-state access
**When** the operator or skill consumes the diagnostic payload
**Then** the operator receives actionable next-step guidance that distinguishes official docs, curated hints, provider guidance, and inferred suggestions
**And** fallback validation and hinting remain sufficient to continue without manually parsing raw logs first.

### Story 2.4: Complete the Browser Library Flagship Repair Workflow

As an Automation Engineer,
I want a documented Browser Library repair workflow with deterministic fallbacks,
So that I can repair a real failing test end to end and verify the fix with confidence.

**Requirements:** FR2, FR6, FR7, FR8, FR15, NFR4

**Acceptance Criteria:**

**Given** the bounded repair session, approved inspection, and repair-diagnostic stories are complete
**When** Browser Library repair is implemented as the chosen flagship repair scenario
**Then** the project ships the canonical repair skill definition, its host-agnostic assets, and the mapped fallback CLI commands
**And** the documentation shows where MCP is used and where deterministic CLI paths take over.

**Given** the flagship repair scenario runs in local verification
**When** end-to-end tests and benchmark capture execute
**Then** the workflow proves a failing test can be diagnosed, repaired, and rerun successfully
**And** the project records evidence for runnable success, failure shaping quality, and repair-path determinism.

## Epic 3: Generate and Refactor Runnable Robot Coverage

Provide a deterministic authoring path for new and existing Robot Framework artifacts so agents can ground themselves, scaffold real files, validate behavior, and recover safely when generation or refactor work goes wrong.

### Story 3.1: Implement Keyword Grounding and Suite Scaffolding Workflows

As an Automation Engineer,
I want deterministic grounding and scaffolding commands,
So that new Robot Framework work starts from real library context and runnable file structures instead of plausible-looking guesses.

**Requirements:** FR4, FR5, FR12, NFR2, NFR3

**Acceptance Criteria:**

**Given** a new suite or resource must be created
**When** the grounding and scaffolding workflows are implemented
**Then** the CLI can retrieve keyword or library grounding information and scaffold suite/resource files with stable command contracts
**And** the outputs are available in both readable and machine-usable forms.

**Given** an agent needs evidence before generating test steps
**When** it consumes the grounding results
**Then** the payload identifies the relevant libraries, keywords, and usage context clearly enough to reduce hallucinated test steps
**And** scaffolding produces deterministic starting files instead of ad hoc placeholders
**And** preventive hint guidance can be surfaced before generation when a known authoring pattern is error-prone.

### Story 3.2: Implement Runnable Test Generation With Verification

As an Automation Engineer,
I want a generation workflow that ends in executable proof,
So that newly created Robot Framework tests are treated as trustworthy only after validation and `robot` execution.

**Requirements:** FR6, FR12, FR16, NFR3, NFR5

**Acceptance Criteria:**

**Given** grounded inputs and scaffolded files exist
**When** the generation workflow is implemented
**Then** the CLI can generate runnable test artifacts, validate them structurally, and execute them through the documented run-verification path
**And** the workflow produces structured evidence showing whether the requested steps, tasks, and assertions were fulfilled.

**Given** the generated output fails validation or execution
**When** the workflow reports the result
**Then** the operator receives actionable failure details through the shared contract surface
**And** the workflow exposes the next deterministic correction path instead of stopping at a generic failure
**And** preventive or corrective hint guidance is included when recurring authoring mistakes are detected.

### Story 3.3: Implement Refactor and Regenerate Workflows for Existing Suites

As an Automation Engineer,
I want deterministic refactor and regenerate workflows for existing Robot Framework assets,
So that I can evolve suites and resources without losing clarity about what changed or whether the result still runs.

**Requirements:** FR6, FR7, FR12, NFR2, NFR3

**Acceptance Criteria:**

**Given** an existing suite or resource needs structural changes
**When** the refactor workflow is implemented
**Then** the CLI exposes a stable path for refactor or regeneration tasks that reuses shared contracts, validation, and failure shaping
**And** the workflow reports the affected artifacts clearly enough for human review.

**Given** a refactor operation alters existing Robot Framework files
**When** validation and run verification complete
**Then** the workflow reports whether the change remains runnable and where manual follow-up is required
**And** the resulting contract shape is consistent with the generation and repair surfaces.

**Given** a refactor or regeneration attempt fails partially or introduces a risky change
**When** the workflow reports the result
**Then** the operator receives preventive or corrective hint guidance for the known failure pattern
**And** the output distinguishes between automatically recoverable issues and manual follow-up that must not be skipped.

### Story 3.4: Publish Canonical Generation and Refactor Skills

As an Automation Engineer,
I want reusable skill workflows for generation and refactoring jobs,
So that supported hosts can follow the same task recipe while still preserving deterministic CLI fallback paths.

**Requirements:** FR7, FR8, FR9, NFR4

**Acceptance Criteria:**

**Given** the generation and refactor CLI workflows exist
**When** the skill layer story is implemented
**Then** canonical workflow definitions, input contracts, fallback mappings, and asset bindings exist for generation and refactor jobs
**And** host-specific rendering consumes those canonical definitions instead of redefining the workflow logic per host.

**Given** a supported host cannot load or execute a skill reliably
**When** an operator follows the documented fallback
**Then** they can complete the same job through deterministic CLI commands
**And** the host-specific documentation does not pretend the skill path is mandatory or universally identical.

### Story 3.5: Prove Generation and Refactor Workflows With End-to-End Scenarios

As a maintainer,
I want end-to-end proof for the generation and refactor workflows,
So that the product demonstrates runnable outcomes instead of relying on architecture narrative alone.

**Requirements:** FR6, FR16, NFR3, NFR5

**Acceptance Criteria:**

**Given** the flagship generation and refactor workflows are implemented
**When** end-to-end and benchmark scenarios execute
**Then** the project measures runnable success, correction burden, and workflow determinism for representative scenarios
**And** the resulting evidence is suitable for release comparison and regression detection.

**Given** a future change regresses output quality or validation behavior
**When** the proof suite runs in CI
**Then** the regression is caught through explicit workflow checks rather than only unit-level assertions
**And** the benchmark pack remains focused on repair, generation, and refactor reference scenarios.

## Epic 4: Onboard Supported Hosts to Reference Workflows

Render canonical workflows into supported-host outputs, install them predictably, and prove the host claims with compatibility guidance, CI validation, and benchmark-backed release evidence.

### Story 4.1: Render Supported-Host Outputs by Renderer Family

As an operator,
I want host outputs rendered by shared packaging family,
So that supported hosts receive consistent artifacts without duplicating workflow logic five different ways.

**Requirements:** FR9, FR13, NFR4

**Acceptance Criteria:**

**Given** canonical skills and bundle assets exist
**When** the renderer-family story is implemented
**Then** the project can generate host-targeted outputs for the first-class v1 host set from shared canonical workflow definitions and assets
**And** the generated artifacts live under `dist/` or other generated locations rather than becoming a second source of truth.

**Given** host packaging differs
**When** bundles are rendered
**Then** each output captures only the host-specific manifest or packaging concerns
**And** workflow logic, fallback commands, and canonical assets stay owned by the shared skill and asset layers
**And** renderer implementations are grouped by shared host packaging patterns rather than five unrelated bespoke code paths in one story.

### Story 4.2: Add Install Surfaces and Fallback Mapping for Supported Hosts

As an operator,
I want installation commands and fallback mappings that are explicit per host,
So that I can recover quickly when a host's skill-loading behavior is incomplete or inconsistent.

**Requirements:** FR8, FR9, FR13, NFR4

**Acceptance Criteria:**

**Given** the supported hosts do not all load skills or bundles the same way
**When** installation and host-mapping surfaces are implemented
**Then** the CLI can install or reference the rendered skill artifacts for each supported host
**And** each host path includes the deterministic fallback commands for the flagship workflows.

**Given** an operator follows a host-specific install path
**When** setup completes
**Then** the instructions identify the supported support tier, known deviations, and fallback behavior clearly
**And** unsupported hosts remain labeled experimental instead of implied to have parity.

### Story 4.3: Publish Compatibility Profiles and First-Run Onboarding

As a solo Automation Engineer,
I want compatibility profiles and concise onboarding docs,
So that I can reach a reference workflow quickly and understand exactly what support level I am getting in my chosen host.

**Requirements:** FR13, FR14, NFR2, NFR4

**Acceptance Criteria:**

**Given** the v1 host set is explicitly defined
**When** compatibility profiles are published
**Then** each supported host has a documented profile covering support tier, setup path, supported workflows, and required fallback behavior
**And** the docs avoid vague "works everywhere" language.

**Given** a new operator is evaluating the project
**When** they follow the onboarding documentation
**Then** they can reach at least one reference workflow without hidden prerequisites
**And** the onboarding path stays concise enough to satisfy FR14.

**Given** a host still requires a hidden setup dependency or undocumented workaround
**When** the onboarding flow is validated
**Then** that host cannot be presented as first-run complete
**And** the documentation must either expose the prerequisite explicitly or downgrade the support claim.

### Story 4.4: Add CI Compatibility, Bundle Validation, and Release Gates

As a maintainer,
I want CI to validate compatibility and release-critical surfaces,
So that portability, schema stability, and flagship workflow claims are checked continuously rather than manually.

**Requirements:** FR13, NFR2, NFR4, NFR5

**Acceptance Criteria:**

**Given** bundles, schemas, contracts, and flagship workflows are part of the product surface
**When** CI workflows are implemented
**Then** GitHub Actions validates schema sync, supported Python and Robot Framework ranges, host compatibility assertions, bundle validity, and flagship proof scenarios
**And** the Epic 5 live MCP repair proof (`scripts/run_epic5_live_mcp_proof.py`) is run as a release gate alongside the CLI/subprocess flagship proof
**And** failures block release when public-surface guarantees drift.

**Given** contributors evolve package structure or host outputs
**When** CI runs on a change
**Then** the validation suite catches contract drift, compatibility-profile breakage, and release-asset inconsistencies
**And** the CI surface remains focused on the declared support matrix rather than unbounded host coverage.

### Story 4.5: Produce Benchmark-Backed Release Evidence

As a maintainer,
I want release evidence tied to the flagship scenarios,
So that scope decisions and portability claims can be defended with measured outcomes instead of intuition.

**Requirements:** FR13, FR15, FR16, NFR3, NFR5

**Acceptance Criteria:**

**Given** the flagship repair, generation, and refactor scenarios are implemented
**When** the benchmark and release-evidence story is completed
**Then** the project records comparable measures for setup friction, tool-call count, failed tool-call rate, runnable success, correction burden, and token or context usage where available
**And** the evidence includes the Epic 5 live MCP repair proof pack (`dist/benchmarks/epic5-live-mcp-proof.json`) so the live-execution path is measured, not only the CLI/subprocess path
**And** the benchmark pack remains small enough to sustain as an open-source proof set.

**Given** a release is prepared
**When** the evidence package is reviewed
**Then** maintainers can show how the hybrid design improved or regressed against the target scenarios
**And** the release narrative does not claim benefits that the benchmark pack fails to prove.

**Given** host validation coverage or benchmark evidence is incomplete
**When** release readiness is reviewed
**Then** the gap is called out explicitly instead of being implied away
**And** unsupported benefit claims are blocked from the release narrative.

## Epic 5: Wire a Live Robot Framework Execution Engine Behind the MCP Core

Replace the simulated live-session stepper with a real Robot Framework execution engine that preserves live context across steps, executes keywords for real, exposes real application state, and supports an opt-in attach path — without widening the bounded MCP tool allowlist. This epic also drops the misleading `repair` qualifier from the general live-session primitive (the session and step tools serve repair, authoring, and exploration alike), keeping `repair` only where behavior is genuinely repair-specific.

### Story 5.1: Execute Real Keywords in an In-Process Live RF Context

As an Automation Engineer,
I want each repair step to run as a real Robot Framework keyword in a persistent in-process context,
So that variables, imports, and library state carry across steps and real failures surface honestly.

**Requirements:** FR2, NFR1, NFR3

**Acceptance Criteria:**

**Given** an open live session
**When** `rf_execute_step` runs a keyword (e.g. `Should Be Equal    1    2`)
**Then** the keyword executes through a real Robot Framework execution context (`EXECUTION_CONTEXTS` / namespace / `BuiltIn`)
**And** a genuine pass/fail is returned through the existing `StepResult` + `ErrorEnvelope` contracts
**And** the in-memory `step_executor=None` simulation path is removed.

**Given** a multi-step session
**When** a later step references a variable assigned by an earlier step
**Then** the live namespace resolves it so state persists across steps without restarting the context.

**Given** the live-session primitive is general (used for repair, authoring, and exploration alike)
**When** the engine lands
**Then** the session and step tools and types drop the `repair` qualifier — `rf_open_session`, `rf_get_session`, `rf_execute_step`, `rf_close_session`, `LiveSessionStore`, `LiveStepper`, `SessionSummary`, `StepResult`, and the `session` / `step-result` JSON Schemas
**And** the `repair` name is retained only where behavior is genuinely repair-specific (repair diagnostics, repair hints, the Browser Library flagship repair skill, FR15).

### Story 5.2: Back Runtime Context Get/Set With the Live Namespace

As an Automation Engineer,
I want `rf_get_context` / `rf_set_context` to read and write the real Robot Framework runtime namespace,
So that the context I inspect and mutate is execution truth, not a placeholder.

**Requirements:** FR2, NFR1

**Acceptance Criteria:**

**Given** a live session with executed steps
**When** `rf_get_context` is called
**Then** it returns real Robot Framework variables and actually-loaded libraries instead of the seeded placeholder dict
**And** `rf_set_context` writes into the live namespace under the existing policy and capability gating.

### Story 5.3: Back Approved Inspection Snapshots With Real Library State

As an Automation Engineer,
I want `app_inspect_state` to capture real DOM, accessibility, screenshot, last API response, and app context,
So that repair decisions use the live application instead of synthetic fixtures.

**Requirements:** FR2, NFR1

**Acceptance Criteria:**

**Given** a live session whose loaded libraries support a snapshot kind (Browser, Selenium, or Requests)
**When** `app_inspect_state` is requested for an approved kind
**Then** the snapshot is captured from the real library instance with provenance `OBSERVED`
**And** the synthetic `repair-session-fixture` payloads are removed
**And** snapshot kinds unsupported by the active libraries return a structured, capability-gated error.

### Story 5.4: Add the Opt-In Attach Bridge to a Running RF Process

As an Automation Engineer,
I want to attach the repair session to an already-running Robot Framework process,
So that I can inspect and step against a live application I already have open.

**Requirements:** FR1, FR2, NFR1

**Acceptance Criteria:**

**Given** attach is enabled by explicit local policy and the session is opened with `attach_requested=true`
**When** the execute, context, and inspect tools run
**Then** they route to the attached external process over a loopback-only, ephemeral-credential bridge
**And** attach stays disabled by default, is visible to the operator, and can be stopped explicitly
**And** no new MCP tools are added beyond the existing allowlist.

### Story 5.5: Prove the Live MCP Repair Path End-to-End

As a maintainer,
I want the flagship Browser Library repair proven through the live MCP path,
So that FR15's proof exercises real execution, not only the CLI subprocess fallback.

**Requirements:** FR2, FR15, NFR2, NFR5

**Acceptance Criteria:**

**Given** the live execution engine from Stories 5.1-5.4
**When** the flagship repair scenario runs through the MCP tools
**Then** an end-to-end live repair is demonstrated and recorded in benchmark evidence
**And** the Epic 4 CI and benchmark stories (4.4, 4.5) reference the live path as a release gate.
