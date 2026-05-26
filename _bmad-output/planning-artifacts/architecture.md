---
stepsCompleted:
  - 1
  - 2
  - 3
  - 4
  - 5
  - 6
  - 7
  - 8
inputDocuments:
  - "/home/many/workspace/rfmcp-reloaded/_bmad-output/planning-artifacts/prds/prd-rfmcp-reloaded-2026-05-23/prd.md"
  - "/home/many/workspace/rfmcp-reloaded/_bmad-output/planning-artifacts/prds/prd-rfmcp-reloaded-2026-05-23/addendum.md"
  - "/home/many/workspace/rfmcp-reloaded/_bmad-output/planning-artifacts/prfaq-rfmcp-reloaded.md"
  - "/home/many/workspace/rfmcp-reloaded/_bmad-output/planning-artifacts/prfaq-rfmcp-reloaded-distillate.md"
  - "/home/many/workspace/rfmcp-reloaded/docs/compass_artifact_wf-cfd59c3b-036d-4b2a-9ce2-522e9727a1c9_text_markdown.md"
  - "/home/many/workspace/rfmcp-reloaded/docs/deep-research-report (8).md"
workflowType: "architecture"
project_name: "rfmcp-reloaded"
user_name: "Many"
date: "2026-05-24"
lastStep: 8
status: "complete"
completedAt: "2026-05-24"
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Primary product contract:**
Users rely on this project to make AI-assisted Robot Framework work more inspectable, more deterministic, and more verifiable than ad hoc scripting, with clearly declared degradation when host capabilities vary.

**Who this serves first:**
The primary v1 audience is solo Automation Engineers using AI coding agents to create, repair, refactor, and validate Robot Framework artifacts. Secondary stakeholders are maintainers, contributor-developers, CI operators, and host/platform integrators.

**Problem being solved:**
Existing Robot Framework plus editor plus script workflows can produce runnable artifacts, but they do not reliably make AI-assisted changes inspectable, bounded, host-aware, and behaviorally trustworthy. The architecture must therefore reduce false confidence, not just reduce manual effort.

**Functional Requirements:**
The product is defined by 16 functional requirements across six requirement clusters. Architecturally, they form three runtime layers plus three control layers.

- **MCP Core requirements** define a narrow live-state execution surface for stepwise Robot Framework work, runtime/application-state inspection, and Robot Framework context access.
- **CLI Workflow requirements** define deterministic stateless commands for grounding, scaffolding, validation, executable run verification, and machine-usable failure output.
- **Skill Workflow requirements** define reusable host-facing orchestration for repair, generation, and refactoring tasks, always paired with deterministic fallback paths.
- **Hint and recovery requirements** define structured guidance for wrong keywords, unclear arguments, weak library docs, and recurring authoring mistakes.
- **Compatibility requirements** define explicit support tiers and first-run onboarding discipline for the v1 host set.
- **Flagship workflow requirements** require at least one repair workflow and one runnable-test generation workflow to prove the architecture against real scenarios.

Architecturally, this means the system is not a single application surface. It is a layered toolchain with a strict responsibility boundary between live-state services and stateless workflow services, plus a separate trust-and-guidance layer for error recovery and prevention.

**First-principles framing:**
At the most basic level, this product exists to solve five irreducible problems:

- A coding agent sometimes needs access to **live Robot Framework execution state** that cannot be reconstructed cheaply from files alone.
- A coding agent needs **deterministic ways to generate or transform Robot Framework artifacts** without relying on vague prompt-only reasoning.
- The system needs a **verification path** that proves output is not only syntactically valid but runnable and behaviorally aligned with the user’s requested steps, tasks, and assertions.
- The system needs a **hint and recovery path** that can guide the next correction step when library docs are insufficient or failures are predictable.
- The workflow needs to remain **usable across multiple agent hosts** without pretending every host offers the same capabilities.

From that foundation, the architectural logic becomes clearer:

- Privileged live-state access should be the exception path, not the default path.
- Stateless operations should be cheap, repeatable, and externally verifiable.
- Every generated artifact should move through a validation chain before it is treated as trustworthy.
- Hinting should improve trust and recovery without becoming an unbounded source of undocumented behavior.
- Portability should come from stable workflow contracts and fallback paths, not from host-specific magic.

### Architectural Asymmetry

This project is not a general AI platform. Its center of gravity is **Robot Framework execution truth**, **deterministic workflow outputs**, and **trustworthy recovery guidance**.

- The **MCP Core** exists to expose authoritative live state.
- **CLI Workflows** exist to impose deterministic artifact boundaries.
- **Skill Workflows** exist to orchestrate tasks against those boundaries.
- The **Hint System** exists to reduce false confidence and improve recovery when docs or errors alone are insufficient.
- **Compatibility Profiles** exist to describe declared degradation rules, not to imply universal parity.

Live-state access is authoritative. Generation, orchestration, and hinting are subordinate.

### Non-Functional Requirements

The NFR set strongly shapes the architecture:

- **Locality and safety** require local-first execution and explicit control over attach-style behavior and sensitive state capture.
- **Stable public surfaces** require durable interfaces for MCP, CLI, skills, and hint outputs so workflows do not drift unpredictably.
- **Structured failure reporting** requires machine-usable diagnostics, not just human-readable logs.
- **Portability over breadth** requires choosing a few hosts and supporting them well instead of generalizing too early.
- **Maintainer sustainability** requires surface-area reduction, scope discipline, and architecture that resists relapsing into a broad monolith.
- **Hint trust and clarity** require that additional guidance be attributable, explainable, and clearly distinguished from raw library docs or execution truth.

### Scale & Complexity

This is a medium-complexity developer-tooling architecture problem.

- Primary domain: developer tooling / AI-agent integration / Robot Framework automation
- Complexity level: medium
- Estimated architectural components: 7 to 9 major components or service areas

The complexity is driven less by traffic scale or data volume and more by:

- Stateful vs stateless workflow separation
- Multi-host compatibility behavior
- Agent reliability, recovery, and validation loops
- Public-surface discipline
- Security and clarity around attach-style behavior
- Version variance across Robot Framework and adjacent tooling
- Provenance and conflict handling for hint sources

### Technical Constraints & Dependencies

Known constraints and dependencies already implied by the requirements and source artifacts:

- The architecture must preserve a small set of live-state Robot Framework operations.
- Stateless helpers must stay out of the MCP Core unless evidence later proves otherwise.
- Runnable output must be verifiable through `robot` execution and structured validation paths.
- Hint output must be attributable and clearly separated from official docs and inferred guidance.
- The v1 host set is Claude Code, GitHub Copilot, Codex, OpenCode, and KiloCode.
- Hosts outside that set should be treated as experimental.
- Attach-style behavior must stay local-first, opt-in, and explicitly bounded.
- The architecture should compose with existing Robot Framework tooling such as RobotCode and the standard Robot CLI rather than replace them wholesale.
- Host environments will differ in capabilities, permissions, and available tools.
- LLM-facing workflows are probabilistic, so determinism must be imposed at artifact boundaries.
- Open-source maintenance capacity is limited, so every abstraction has carrying cost.
- Robot Framework version variance and ecosystem drift are normal operating conditions, not edge cases.

### Boundary Rules

The following boundary rules must remain true if the architecture is to stay coherent:

- The MCP Core must not absorb stateless convenience helpers merely because they are useful.
- CLI Workflows must not depend on hidden live-state assumptions.
- Skill Workflows must orchestrate contracts, not redefine them.
- The Hint System must not silently override user intent or disguise inferred guidance as execution truth.
- Compatibility Profiles must describe what is supported, what is degraded, and what is unsupported for each host.
- Flagship workflows are consumers of architectural contracts, not exceptions to them.
- There must not be two conflicting sources of truth for execution state, artifact meaning, or hint provenance.

### Proof Required For Claims

The architecture makes trust-sensitive claims. Those claims require proof obligations:

- **“Runnable”** requires `robot` execution without errors.
- **“Behaviorally aligned”** requires acceptance evidence that the generated or repaired test satisfies the requested steps, tasks, and assertions.
- **“Portable”** means equivalent intent can be completed across supported hosts within declared degradation rules.
- **“Deterministic”** means key workflow boundaries are stable despite environment noise such as timestamps, temp paths, locale, path separators, and tool-version skew.
- **“Helpful hinting”** means guidance improves recovery or prevention without obscuring source, confidence, or corrective intent.

At minimum, these claims imply the need for:

- Contract tests for interfaces and output schemas
- End-to-end workflow proofs for flagship scenarios
- Golden artifact or fixture-based checks where applicable
- Cross-host execution checks for supported hosts
- Version-compatibility coverage for key Robot Framework and tooling ranges
- Hint-source provenance checks and conflict-resolution tests

### Architectural Decision Pressure Already Visible

Even before solution design begins, the project context is already forcing a small set of Architecture Decision Record candidates:

- **ADR candidate: Live-state boundary.**
  The system must decide exactly which operations justify MCP residency and which must be forced into CLI or skill paths. This is the primary structural decision because it shapes maintainability, token cost, and implementation consistency.

- **ADR candidate: Runnable-test verification model.**
  The system must define how generated and repaired Robot Framework artifacts are grounded, validated, executed, and judged to satisfy user-requested steps and assertions.

- **ADR candidate: Hint system source and precedence model.**
  The system must define where hints come from, how they are ranked, how provenance is preserved, and how conflicting guidance is resolved.

- **ADR candidate: Host portability contract.**
  The system must define what first-class support means for each Agent Host, what fallback behavior is mandatory, and where host-specific divergence is acceptable.

- **ADR candidate: Attach safety model.**
  The system must define how local-only attach behavior is authorized, bounded, surfaced to the operator, and prevented from becoming an accidental remote control plane.

These decisions are more important than early technology choices because they determine whether the architecture stays narrow or relapses into a broad helper platform.

### Pre-mortem Risk Signals

If this architecture later fails, the most likely causes are already visible in the project context:

- **Boundary erosion failure:** convenience features gradually leak back into the live-state layer until the MCP Core becomes broad and hard to maintain again.
- **Verification weakness failure:** generated tests are counted as “successful” because they run, even when they do not faithfully implement the user’s requested steps, tasks, or assertions.
- **Hint trust failure:** users or agents cannot tell whether guidance came from official docs, curated rules, project knowledge, or inference.
- **Portability overclaim failure:** the product claims cross-host support before compatibility profiles and fallback behavior are stable enough to support that promise.
- **Attach expansion failure:** runtime inspection and observability features expand faster than the safety model, increasing privileged surface and operator confusion.
- **Surface drift failure:** MCP, CLI, skill, and hint contracts evolve independently and break the consistency needed for agent reliability.
- **Proof gap failure:** the architecture narrative sounds right, but the benchmark pack does not clearly prove reduced token cost, reduced tool-call failure, better runnable outcomes, or better recovery quality.
- **Authority confusion failure:** two sources of truth emerge for execution state, artifact meaning, or corrective guidance.
- **Observability gap failure:** host-specific fallbacks hide the real execution path, making failures hard to diagnose.
- **Framework lock-in failure:** host-aware abstractions silently encode assumptions from one environment.
- **Maintenance fragmentation failure:** compatibility profiles and hint rules expand faster than they can be validated.
- **Safety/performance coupling failure:** richer attach or live-state surfaces degrade responsiveness or increase operational risk.

These failure modes imply that later architectural decisions should explicitly optimize for containment, verification rigor, contract alignment, diagnosability, and measurable improvement rather than feature breadth.

### Cross-Cutting Concerns Identified

The following concerns will affect multiple architectural components and must be handled deliberately in later decisions:

- **State boundary discipline:** the seam between MCP-only behavior and CLI/skill behavior
- **Validation integrity:** preventing hallucinated or non-runnable generated tests
- **Hint provenance and conflict handling:** keeping guidance trustworthy and resolvable
- **Host portability:** designing for support tiers and fallback paths rather than false uniformity
- **Attach safety:** minimizing exposure of DOM, screenshots, API payloads, and runtime variables
- **Interface durability:** keeping MCP, CLI, skill, and hint surfaces stable enough for agent consistency
- **Observability for proof:** capturing benchmarkable workflow metrics without rebuilding a broad telemetry platform
- **Scope containment:** ensuring convenience features do not leak back into the live-state core
- **Adoption realism:** keeping setup burden and mental model small enough for solo open-source users
- **Confidence labeling:** distinguishing observed evidence, inferred constraints, and anticipated risks

### Non-Goals / Unsupported

This project context does not support the following interpretations:

- This is not general AI orchestration for every Robot Framework-adjacent use case.
- This is not universal host parity.
- This is not a guarantee of full correctness for AI-authored test changes.
- This is not a license for flagship workflows to bypass architectural contracts.
- This is not a broad execution-control platform beyond the narrow live-state needs being justified.
- This is not unbounded free-form hint generation without provenance or workflow constraints.

### Governing Decision Tests

Future architectural decisions should be judged against these tests:

- Does this preserve deterministic, inspectable behavior?
- Does this keep the MCP boundary minimal and live-state focused?
- Does this improve real usability across supported hosts, or only abstract differences on paper?
- Can the behavior be verified with runnable proof, not narrative assurance?
- Does this reduce false confidence for AI-authored Robot Framework changes?
- Does the hint system improve recovery without weakening trust?

## Starter Template Evaluation

### Primary Technology Domain

Python developer-tooling monorepo with multiple distribution surfaces:

- MCP runtime
- CLI tooling
- install/setup scripts
- core agent skills
- file-based hint packs
- optional VS Code extension package
- optional plugin-bundle artifacts for marketplace-style distribution

### Starter Options Considered

1. Plain single-package `uv` application

- Too flat for the required repo shape.

2. `uv` workspace monorepo

- Best fit for one repo with multiple packages and one lockfile.

3. Open Plugins-style repository basis

- Valuable as a plugin/distribution artifact structure, but insufficient as the primary Python repo foundation.

### Selected Starter: `uv` workspace monorepo

**Rationale for Selection:**
This provides the cleanest one-repo foundation for a Python-centered system that still needs separation between MCP runtime, CLI, skills/install surfaces, hint packs, and optional IDE extension packaging. It also allows Open Plugins-compatible bundles to live inside the repo or be generated from it for marketplace integration.

**Initialization Command:**

```bash
uv init --package rfmcp-reloaded
```

**Architectural Decisions Provided by Starter:**

**Language & Runtime:**

- Python-centered runtime and packaging
- optional TypeScript only for a VS Code extension package if needed later

**Dependency & Environment Management:**

- `uv` workspace
- shared `uv.lock`
- per-package `pyproject.toml`

**CLI Solution:**

- `typer` as the preferred CLI framework
- `click` ecosystem underneath

**Code Organization:**

- monorepo with multiple workspace members
- separation between runtime, CLI, installers, bundles, and optional extension package

**Plugin / Hint Extensibility:**

- file-based curated hints by default
- Python plugin/provider interface for additional libraries
- Open Plugins-compatible bundle layout for shareable skill/rules/MCP packaging

**Robot Framework Integration Bias:**

- `robot`, `rebot`, `libdoc`, and `robot.api` first
- RobotCode optional, not required

**Library & Syntax Boundary:**

- Browser, Selenium, Requests, Appium, Database, DataDriver support should begin as plugin/hint providers plus skills
- keyword-driven, BDD, and data-driven styles should be handled by generation/validation layers and skills, not by core MCP semantics

**Extension / Marketplace Path:**

- if VS Code Marketplace support is pursued, use a dedicated extension package and VSIX publishing flow
- do not rely on Open Plugins format alone for VS Code Marketplace distribution

## Core Architectural Decisions

### Data Architecture

- No database in the core MVP.
- Hint and recovery guidance should use a file-first architecture with curated YAML packs as the primary source of truth.
- YAML packs must remain mostly declarative data, suitable for patterns, metadata, severity, tags, recovery text, match criteria, and pack manifests.
- YAML packs should not become a container for complex branching logic, inheritance graphs, cross-pack behavioral coupling, or dynamic transforms.
- Hint and rule files should be validated with strict typed schemas.
- Every pack manifest must carry an explicit schema version.
- The extension model should use `pluggy` hook specifications and implementations.
- The `pluggy` hook surface must remain narrow and business-oriented, focused on discovery, rule contribution, normalization, enrichment, recovery strategy contribution, and tightly scoped conflict resolution.
- Plugins must not silently mutate arbitrary internal state or rewrite authoritative pack data without explicit, bounded rules.
- Installed providers should be discovered through Python package entry points via `importlib.metadata`.
- Provider discovery and loading must use deterministic ordering by stable key, not filesystem order or raw entry-point iteration order.
- A generated local cache or index is allowed for performance, but it must be explicitly rebuildable, local-only, non-authoritative, and never user-edited.
- The cache must be treated like a disposable derived artifact similar to `__pycache__`.
- The cache must carry its own format version.
- Cache validity must be determined by fingerprinted inputs, including at minimum pack file paths, content hashes, plugin package versions, Python version, and tool version.
- Cache rebuild must trigger automatically on fingerprint mismatch.
- Core runtime behavior must remain correct with cache disabled.
- The canonical load pipeline is:
  `discover -> parse -> schema-validate -> normalize -> merge -> build derived index -> serve`
- Source of truth remains the curated YAML packs plus installed providers, never the cache artifact.
- Loaded guidance must preserve provenance sufficient to identify pack id, pack version, source path, and plugin/provider id.
- Pack IDs must be globally unique.
- Override precedence between core packs, built-ins, installed plugins, local project packs, and inferred recovery guidance must be explicit and documented.
- Failure handling must be defined for malformed packs, broken plugins, stale caches, and partially installed environments.

**Rationale:**
This preserves inspectability and contributor friendliness while still allowing ecosystem-specific guidance to scale through plugins. The added invariants prevent stale-cache behavior, nondeterministic merges, and hidden authority drift.

### Authentication & Security

- The core MVP should not implement an application-level authentication system.
- Security should be enforced through local policy files plus explicit capability flags, not user accounts or RBAC.
- Sensitive operations must be classified by capability and checked before execution.
- Attach and live-state capabilities must be disabled by default.
- Enabling attach or comparable privileged runtime inspection must require explicit local policy or explicit session-level opt-in.
- Secret material must not be stored in hint packs, cache artifacts, plugin manifests, or generated guidance files.
- Secret persistence is optional and should prefer OS-native secure storage when needed.
- The architecture should support optional OS keyring integration for credential storage.
- Plugin/provider execution should be treated as trusted installed code, but failure isolation, provenance labeling, and privilege boundaries must still be enforced by core contracts.
- Core MVP should not support remote plugin execution, silent background downloads, or implicit privilege expansion.

**Rationale:**
This matches the local-first nature of the product and keeps the security model legible for solo developers and CI-driven agent workflows. It also keeps privileged operations explicit, which is necessary for attach-style safety and trust.

### API & Communication Patterns

- The core MCP surface should support both `stdio` and HTTP transports in v1.
- FastMCP should be the preferred Python server framework for implementing the MCP surface in v1.
- The protocol contract must remain aligned to the official MCP specification and schema, regardless of framework choice.
- The exposed MCP tool surface must remain narrow and bounded to live-state execution, stepwise operations, and explicitly approved runtime/context inspection.
- Stateless helper workflows should not be reintroduced into MCP merely because the server framework makes additional exposure easy.
- MCP payloads should be typed and schema-backed.
- The CLI should remain the default stateless automation path.
- CLI commands should support both human-readable output and stable machine-usable `--json` output.
- CLI JSON contracts and MCP tool payload contracts should be documented together and versioned explicitly.
- Error handling should use a shared structured error envelope across CLI and MCP-facing tool results.
- The shared error envelope should include at minimum an error code, human-readable message, source, severity, provenance/context, retryability, and a suggested next step.
- Hint and recovery guidance should use a dedicated hint payload schema carried within or alongside the shared error envelope.
- Structured hint payloads must preserve provenance and distinguish curated guidance, provider guidance, and inferred recovery suggestions.
- Contract schemas should be exportable as JSON Schema for validation, testing, and cross-host consistency checks.

**Rationale:**
This keeps MCP useful across more hosts and deployment contexts without reopening the core boundary question. It also ensures that recovery guidance, machine automation, and human debugging all rely on one consistent contract model instead of separate ad hoc output paths.

### Infrastructure & Deployment

- Primary distribution should be through PyPI.
- Installation and execution paths should be optimized for `uvx`, `uv tool install`, and `pipx`.
- Release outputs should include generated plugin/skill bundles in addition to the Python package.
- A separate VS Code extension track may be added later, but it is not required for the core MVP release path.
- CI/CD should use GitHub Actions.
- CI should validate supported Python and Robot Framework version ranges through a compatibility matrix.
- CI should exercise runnable-test verification paths and at least the flagship workflow proofs.
- Configuration should separate application settings, local policy, hint packs, cache/index artifacts, and generated release assets.
- Logging should use structured logging from day one.
- Structured logs should be sufficient for local debugging, CI diagnosis, and benchmark/evidence collection without requiring a remote telemetry backend in MVP.
- HTTP transport support is allowed in v1, but default exposure must be loopback-only.
- Broader network exposure should require explicit configuration or policy changes, not implicit defaults.

**Rationale:**
This gives the project a realistic open-source release path, strong enough CI proof discipline, and enough observability for debugging and benchmark claims without dragging the MVP into unnecessary platform operations.

### Resolved Blocking ADR Decisions

#### ADR: Contract Source of Truth

- `rfmcp_core.models` is the authoritative source of canonical typed contract shapes.
- `rfmcp_core.contracts` is the stable public import surface and serialization layer built on top of those models; it may re-export and compose models but must not introduce competing field definitions.
- `assets/schemas/` contains generated JSON Schema exports derived from `rfmcp_core.models` for cross-host validation, documentation, and fixture verification.
- Direct manual edits to generated files in `assets/schemas/` are prohibited. Contract evolution flows in one direction:
  `rfmcp_core.models` → `rfmcp_core.contracts` → generated `assets/schemas/`.
- `scripts/export_json_schemas.py` exports JSON Schema from the authoritative models.
- `scripts/verify_schema_sync.py` regenerates schema artifacts and fails CI if the committed JSON Schema no longer matches the authoritative model layer.
- Contract-shape changes must be implemented by changing models first, then updating the public contract façade and regenerated schemas in the same change.

#### ADR: Provider Extension Shape

- `pluggy` hookspecs live in `rfmcp_core.hints.hookspecs`.
- Provider discovery and registration orchestration lives in `rfmcp_core.hints.plugin_manager`.
- Provider packages expose hook implementations through the Python entry-point group `rfmcp.providers`.
- The entry-point name is the stable `provider_id`, using dotted lowercase format such as `robotframework.browser`.
- Each provider package should expose `plugin.py` as the entry-point target and may include `metadata.py` plus narrowly scoped helper modules.
- The stable provider ordering key is `provider_id`; providers must be sorted by that key before execution.
- Static authoritative hint packs live under `assets/hints/libraries/`; provider packages contribute code and dynamic recovery behavior, not competing authoritative static truth.
- Allowed hook categories are:
  - provider metadata declaration
  - failure/context normalization
  - contextual hint contribution
  - recovery-candidate contribution
- The hookspec contract for those categories is:
  - `get_provider_metadata() -> ProviderMetadata`
  - `normalize_failure_context(context: FailureContext) -> FailureNormalization | None`
  - `contribute_contextual_hints(context: FailureContext) -> list[HintCandidate]`
  - `contribute_recovery_candidates(context: FailureContext) -> list[RecoveryCandidate]`
- Providers must import shared payload and candidate types from `rfmcp_core.contracts`, not from `rfmcp_core.models`.
- Merge semantics are:
  - core-derived context fields are authoritative
  - provider normalization may fill missing context fields but may not overwrite authoritative core fields
  - conflicting provider normalizations resolve by first-wins in sorted `provider_id` order, while conflicts are retained in diagnostics/provenance output
  - contextual hints and recovery candidates are unioned, deduplicated by stable candidate key, then ordered by confidence and stable provenance key
- Forbidden provider behaviors include:
  - mutating authoritative YAML packs in place
  - registering MCP tools directly
  - overriding local policy decisions
  - performing network I/O at import time
  - relying on package-global side effects for registration

#### ADR: Skill Workflow Structural Home

- Skill Workflows are a distinct structural layer and are not implied only through install scripts or bundle builders.
- Canonical host-agnostic skill workflow definitions live in `packages/rfmcp_skills/`.
- Authoritative skill instruction assets and templates live in `assets/skills/`.
- Skill discovery is manifest-based: each canonical workflow definition exports a stable `skill_id`, input contract, fallback command reference, and asset binding.
- Asset binding is by `skill_id`, with each workflow definition mapping to `assets/skills/<skill_id>/`.
- `rfmcp_bundles` renders host-specific skill/bundle outputs from:
  - `packages/rfmcp_skills/`
  - `assets/skills/`
  - `assets/bundles/`
- `rfmcp_cli.install.skills` installs and references rendered skill artifacts but does not define canonical skill workflow content.
- The structural mapping for PRD FR-7, FR-8, and FR-9 is:
  - canonical skill jobs and expected inputs → `packages/rfmcp_skills/`
  - host-agnostic instructional assets → `assets/skills/`
  - deterministic fallback command mapping → `packages/rfmcp_skills/fallbacks.py`
  - host-aware rendering and packaging → `packages/rfmcp_bundles/`
  - host-specific installation entry points → `packages/rfmcp_cli/install/skills.py`

#### ADR: Implementation Baseline Versions

The implementation baseline for v1 is:

- Python: `>=3.11,<3.14`
- `uv`: `0.11.16`
- FastMCP: `3.3.1`
- MCP Python SDK compatibility target: `mcp 1.27.1`
- `pluggy`: `1.6.0`
- `pydantic`: `2.13.4`
- `pydantic-settings`: `2.14.1`
- `typer`: `0.25.1`
- Robot Framework primary support range: `7.4.x`
- Robot Framework primary tested baseline: `7.4.2`

This version table is the implementation baseline for workspace initialization, dependency locking, and CI matrix construction. Changes to these baselines should be treated as explicit architectural updates, not incidental dependency drift.

### Performance & Scalability Considerations

- v1 performance goals are local responsiveness, deterministic startup behavior, bounded hint-resolution work, and predictable cache reuse rather than large-scale multi-user throughput.
- The generated hint cache/index exists to keep pack/provider loading bounded without creating a second source of truth.
- Provider discovery should be lazy enough to avoid unnecessary startup work outside commands or tools that actually need provider behavior.
- CLI and MCP serialization should reuse the same contract layer to avoid duplicate transformation overhead and divergent hot paths.
- HTTP support remains loopback-only by default to keep transport overhead and exposure bounded in MVP.
- Performance validation should focus on:
  - cache rebuild behavior
  - startup/load path stability
  - hint resolution cost across representative reference scenarios
  - stepwise execution overhead introduced by the MCP layer
- These concerns are validated through benchmark/reference scenarios rather than generalized scale claims.

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**

- Python-centered `uv` workspace monorepo as the project foundation
- File-first YAML hint architecture with `pluggy` extensibility and a non-authoritative rebuildable cache
- Local policy plus capability-flag security model with attach disabled by default
- Shared MCP/CLI contract model with schema-backed payloads and a structured error envelope plus hint payload schema
- Narrow MCP boundary implemented with FastMCP across `stdio` and HTTP transports

**Important Decisions (Shape Architecture):**

- Robot Framework public APIs first, RobotCode optional
- Browser, Selenium, Requests, Appium, Database, and DataDriver support starting as providers/skills rather than core MCP
- PyPI distribution plus generated plugin/skill bundles
- Structured logging from day one
- HTTP loopback-only default posture

**Deferred Decisions (Post-MVP):**

- Separate VS Code extension release track
- Broader network exposure for HTTP transport
- Any database-backed index or persistence layer beyond the disposable local cache
- Expanded plugin/runtime governance beyond local-first trust boundaries

### Decision Impact Analysis

**Implementation Sequence:**

1. Initialize the Python `uv` workspace and package boundaries.
2. Establish shared schemas, contract types, and the structured error/hint envelope.
3. Implement the YAML pack loader, schema validation, provider discovery, precedence rules, and disposable cache.
4. Implement local policy parsing, capability gating, and attach safety checks.
5. Build the bounded FastMCP surface over `stdio` and HTTP.
6. Build CLI workflows with human and `--json` outputs against the same core contracts.
7. Add structured logging, benchmark capture, and CI matrix validation.
8. Generate install/setup artifacts and plugin/skill bundles.

**Cross-Component Dependencies:**

- Hint-system provenance and precedence rules affect CLI validation, MCP recovery payloads, and benchmarkability.
- Security capability checks affect both MCP live-state operations and CLI commands that expose privileged behavior.
- Shared schemas affect FastMCP tools, CLI `--json` output, hint payloads, and compatibility tests.
- HTTP transport support depends on the same bounded MCP surface and policy model as `stdio`; it must not become a second contract family.
- CI proof discipline depends on structured logs, runnable-test verification, and deterministic pack/provider loading behavior.

## Implementation Patterns & Consistency Rules

### Pattern Categories Defined

**Critical Conflict Points Identified:**
The highest-risk conflict areas are naming, contract shape, project structure, provenance fields, validation timing, and failure-handling behavior across MCP, CLI, hint providers, and generated bundles.

### Naming Patterns

**Code Naming Conventions:**

- Python modules, functions, variables, and internal schema field names should use `snake_case`.
- Python classes, typed models, and exception types should use `PascalCase`.
- Constant names should use `UPPER_SNAKE_CASE`.
- CLI commands and long options should use `kebab-case`.

**MCP Naming Conventions:**

- MCP tool names should use dotted namespaces such as `rf.execute_step` or `hint.resolve_keyword`.
- Tool names should be verb-oriented and stable.
- Tool names should not mirror filesystem paths or package internals.

**Hint / Provider Naming Conventions:**

- Pack IDs and provider IDs should use dotted lowercase identifiers such as `robotframework.browser.core`.
- IDs must be globally unique.
- YAML keys and JSON contract fields should use `snake_case`.

### Structure Patterns

**Project Organization:**

- The repository should be organized by runtime surface first, not by user workflow first.
- Top-level architectural areas should clearly separate MCP runtime, CLI runtime, shared core logic, hint/policy assets, generated bundles, and tests.
- Workflow-specific behavior such as repair or generation should compose those surfaces rather than redefine them.

**Rationale:**
These rules minimize naming drift across Python code, YAML packs, JSON contracts, and MCP tools while reinforcing the core boundary between live-state services and stateless workflows.

### Format Patterns

**Shared Error Envelope:**

- Structured errors should use explicit field names:
  - `error_code`
  - `message`
  - `source`
  - `severity`
  - `retryable`
  - `suggested_next_step`
  - `provenance`
  - `details`
  - optional `hint`
- Agents must not invent alternate short-form field names such as `code`, `msg`, or `next_step` for the canonical contract.
- The same envelope shape should be used across CLI JSON output and MCP-facing tool results.

**Hint Payload Shape:**

- Structured hints should use explicit fields:
  - `hint_code`
  - `category`
  - `summary`
  - `guidance`
  - `confidence`
  - `provenance`
  - `applies_to`
  - `suggested_fix`
- Hint payloads must remain attributable and must distinguish curated, provider-contributed, and inferred guidance.

### Structure Patterns

**Test Organization:**

- Tests should live under a central top-level `tests/` tree.
- The test tree should be organized by runtime surface and verification purpose, not ad hoc by contributor preference.
- Shared fixtures should live under `tests/fixtures/`.
- Flagship workflow proofs should live in clearly named integration or end-to-end test areas.
- Generated cache artifacts must not be used as canonical test fixtures unless the test is explicitly about cache behavior.

**Artifact and Asset Organization:**

- Authoritative shared assets such as schemas, policies, and curated hint packs should live in clear top-level directories.
- Package-local asset directories are allowed only for code-adjacent internals that are not the primary shared source of truth.
- Generated caches must live in a dedicated cache area and be excluded from source control.
- Generated plugin/skill bundles should live in a dedicated build or distribution artifact area.
- Agents must not invent new authoritative asset locations without updating the documented structure.

**Rationale:**
These rules keep contracts legible, make test discovery predictable, and stop authoritative assets from fragmenting across the repo.

### Communication Patterns

**Structured Logging Conventions:**

- Structured logs should use mandatory canonical field names, including:
  - `event`
  - `component`
  - `operation`
  - `run_id`
  - `tool_name`
  - `pack_id`
  - `provider_id`
  - `error_code`
  - `severity`
- Agents must not introduce ad hoc alternative field names for the same concepts across packages.

**Provenance Conventions:**

- Surfaced hints, rules, and recovery guidance should preserve canonical provenance fields:
  - `source_type`
  - `source_id`
  - `source_version`
  - `source_path`
  - optional `provider_id`
- Inferred guidance must always be labeled as inferred and must not be blended into curated or provider-authored truth.

### Process Patterns

**Validation Timing and Failure Behavior:**

- Authoritative assets such as schemas, policies, and curated hint packs should fail closed on validation errors.
- Optional providers may fail in isolation, but must emit structured reporting and must not silently disappear.
- Generated caches may be discarded and rebuilt automatically on validation or fingerprint mismatch.
- MCP and CLI boundary payloads should be validated explicitly at contract boundaries rather than trusted implicitly.

### Enforcement Guidelines

**All AI Agents MUST:**

- Reuse shared schema, error, hint, and provenance types instead of redefining near-duplicates.
- Emit canonical contract shapes for all new MCP tools and CLI `--json` outputs.
- Validate new hint packs, pack IDs, and provider metadata against shared rules before merge.
- Preserve the runtime-surface-first project organization unless the documented structure is updated deliberately.

**Pattern Enforcement:**

- CI should enforce schema validity, pack ID uniqueness, contract-shape checks, and selected logging/provenance invariants where practical.
- Conventions should become automated checks wherever feasible instead of remaining reviewer-only guidance.
- Pattern violations should be treated as architecture drift, not stylistic preference.

**Rationale:**
These rules keep failures visible, preserve trust in hint provenance, and stop agents from quietly inventing incompatible local conventions.

## Project Structure & Boundaries

### Complete Project Directory Structure

```text
rfmcp-reloaded/
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── CHANGELOG.md
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .python-version
├── .editorconfig
├── .github/
│   └── workflows/
│       ├── ci.yml
│       ├── release.yml
│       ├── compat_matrix.yml
│       └── verify_schema_sync.yml
├── docs/
│   ├── architecture.md
│   ├── compatibility_profiles.md
│   ├── contracts.md
│   ├── contract_evolution.md
│   ├── hint_packs.md
│   └── mcp_tools.md
├── scripts/
│   ├── build_bundles.py
│   ├── rebuild_cache.py
│   ├── export_json_schemas.py
│   └── verify_schema_sync.py
├── packages/
│   ├── rfmcp_core/
│   │   ├── pyproject.toml
│   │   └── src/rfmcp_core/
│   │       ├── __init__.py
│   │       ├── contracts/
│   │       │   ├── __init__.py
│   │       │   ├── errors.py
│   │       │   ├── hints.py
│   │       │   ├── provenance.py
│   │       │   ├── results.py
│   │       │   └── serialize.py
│   │       ├── models/
│   │       │   ├── __init__.py
│   │       │   ├── hint_pack.py
│   │       │   ├── policy.py
│   │       │   └── payloads.py
│   │       ├── policy/
│   │       │   ├── __init__.py
│   │       │   ├── capabilities.py
│   │       │   ├── loader.py
│   │       │   └── enforcement.py
│   │       ├── hints/
│   │       │   ├── __init__.py
│   │       │   ├── hookspecs.py
│   │       │   ├── loader.py
│   │       │   ├── merger.py
│   │       │   ├── cache.py
│   │       │   ├── plugin_manager.py
│   │       │   └── precedence.py
│   │       ├── runtime/
│   │       │   ├── __init__.py
│   │       │   ├── session.py
│   │       │   ├── stepper.py
│   │       │   ├── context.py
│   │       │   └── snapshot.py
│   │       ├── robot/
│   │       │   ├── __init__.py
│   │       │   ├── parser.py
│   │       │   ├── libdoc.py
│   │       │   ├── execution.py
│   │       │   └── validation.py
│   │       ├── observability/
│   │       │   ├── __init__.py
│   │       │   └── events.py
│   │       └── utils/
│   │           ├── __init__.py
│   │           ├── hashing.py
│   │           └── paths.py
│   ├── rfmcp_mcp/
│   │   ├── pyproject.toml
│   │   └── src/rfmcp_mcp/
│   │       ├── __init__.py
│   │       ├── server.py
│   │       ├── transports/
│   │       │   ├── __init__.py
│   │       │   ├── stdio.py
│   │       │   └── http.py
│   │       ├── tools/
│   │       │   ├── __init__.py
│   │       │   ├── _registry.py
│   │       │   ├── rf_execute_step.py
│   │       │   ├── rf_get_context.py
│   │       │   ├── rf_set_context.py
│   │       │   └── app_inspect_state.py
│   │       ├── security/
│   │       │   ├── __init__.py
│   │       │   ├── attach_policy.py
│   │       │   └── session_guard.py
│   │       └── logging.py
│   ├── rfmcp_cli/
│   │   ├── pyproject.toml
│   │   └── src/rfmcp_cli/
│   │       ├── __init__.py
│   │       ├── main.py
│   │       ├── commands/
│   │       │   ├── __init__.py
│   │       │   ├── validate.py
│   │       │   ├── generate.py
│   │       │   ├── repair.py
│   │       │   ├── refactor.py
│   │       │   ├── hints.py
│   │       │   └── cache.py
│   │       ├── workflows/
│   │       │   ├── __init__.py
│   │       │   ├── grounding.py
│   │       │   ├── generation.py
│   │       │   ├── repair.py
│   │       │   └── refactor.py
│   │       ├── presenters/
│   │       │   ├── __init__.py
│   │       │   ├── human.py
│   │       │   └── structured.py
│   │       ├── install/
│   │       │   ├── __init__.py
│   │       │   ├── agents.py
│   │       │   └── skills.py
│   │       └── logging.py
│   ├── rfmcp_skills/
│   │   ├── pyproject.toml
│   │   └── src/rfmcp_skills/
│   │       ├── __init__.py
│   │       ├── catalog.py
│   │       ├── inputs.py
│   │       ├── fallbacks.py
│   │       └── definitions/
│   │           ├── __init__.py
│   │           ├── repair.py
│   │           ├── generation.py
│   │           ├── refactor.py
│   │           └── keyword_recovery.py
│   ├── rfmcp_bundles/
│   │   ├── pyproject.toml
│   │   └── src/rfmcp_bundles/
│   │       ├── __init__.py
│   │       ├── builders/
│   │       │   ├── __init__.py
│   │       │   ├── open_plugins.py
│   │       │   ├── codex.py
│   │       │   ├── claude_code.py
│   │       │   ├── copilot.py
│   │       │   └── kilocode.py
│   │       └── manifests/
│   │           ├── __init__.py
│   │           ├── templates.py
│   │           └── registry.py
│   ├── rfmcp_provider_browser/
│   │   ├── pyproject.toml
│   │   └── src/rfmcp_provider_browser/
│   │       ├── __init__.py
│   │       ├── metadata.py
│   │       └── plugin.py
│   ├── rfmcp_provider_selenium/
│   │   ├── pyproject.toml
│   │   └── src/rfmcp_provider_selenium/
│   │       ├── __init__.py
│   │       ├── metadata.py
│   │       └── plugin.py
│   ├── rfmcp_provider_requests/
│   │   ├── pyproject.toml
│   │   └── src/rfmcp_provider_requests/
│   │       ├── __init__.py
│   │       ├── metadata.py
│   │       └── plugin.py
│   ├── rfmcp_provider_appium/
│   │   ├── pyproject.toml
│   │   └── src/rfmcp_provider_appium/
│   │       ├── __init__.py
│   │       ├── metadata.py
│   │       └── plugin.py
│   ├── rfmcp_provider_database/
│   │   ├── pyproject.toml
│   │   └── src/rfmcp_provider_database/
│   │       ├── __init__.py
│   │       ├── metadata.py
│   │       └── plugin.py
│   └── rfmcp_provider_datadriver/
│       ├── pyproject.toml
│       └── src/rfmcp_provider_datadriver/
│           ├── __init__.py
│           ├── metadata.py
│           └── plugin.py
├── assets/
│   ├── schemas/
│   │   ├── hint_pack.schema.json
│   │   ├── policy.schema.json
│   │   ├── error_envelope.schema.json
│   │   └── hint_payload.schema.json
│   ├── policies/
│   │   ├── default.policy.yaml
│   │   └── local_http.policy.yaml
│   ├── hints/
│   │   ├── core/
│   │   ├── robotframework/
│   │   └── libraries/
│   ├── skills/
│   │   ├── repair/
│   │   ├── generation/
│   │   ├── refactor/
│   │   └── keyword_recovery/
│   ├── bundles/
│   │   ├── open_plugins/
│   │   ├── codex/
│   │   ├── claude_code/
│   │   ├── copilot/
│   │   └── kilocode/
│   └── examples/
│       ├── agent_setups/
│       └── rf_projects/
├── tests/
│   ├── unit/
│   │   ├── core/
│   │   ├── mcp/
│   │   ├── cli/
│   │   ├── bundles/
│   │   └── providers/
│   ├── integration/
│   │   ├── mcp_stdio/
│   │   ├── mcp_http/
│   │   ├── cli_contracts/
│   │   ├── hint_resolution/
│   │   ├── policy_enforcement/
│   │   └── providers/
│   ├── e2e/
│   │   ├── flagship_generation/
│   │   └── flagship_repair/
│   ├── compatibility/
│   │   ├── robotframework/
│   │   ├── python/
│   │   └── hosts/
│   │       ├── bundle_validation/
│   │       └── profile_assertions/
│   └── fixtures/
│       ├── expected_contracts/
│       ├── generated_from_assets/
│       └── libdoc_outputs/
└── dist/                     # generated, gitignored
    └── bundles/
```

### Architectural Boundaries

**API Boundaries:**

- `rfmcp_mcp` exposes only live-state MCP tools and transport wiring.
- `rfmcp_cli` exposes stateless workflows, install/setup commands, and presentation.
- `rfmcp_core.models` defines authoritative typed payload shapes.
- `rfmcp_core.contracts` is the stable public contract façade and serialization layer for CLI and MCP payloads.

**Component Boundaries:**

- `rfmcp_core.runtime` is MCP-safe live-state logic.
- `rfmcp_cli.workflows` owns generation, repair, refactor, and grounding orchestration.
- `rfmcp_skills` owns canonical host-agnostic skill workflow definitions plus fallback command mapping.
- `rfmcp_bundles` owns artifact generation only.
- Provider packages contribute optional hook implementations and never become core dependencies.

**Data Boundaries:**

- `assets/` contains authoritative committed inputs.
- `dist/` and runtime cache paths are generated and not authoritative.
- JSON Schema authority is top-level under `assets/schemas/`; Python typed models live under `rfmcp_core.models`.

### Requirements to Structure Mapping

- Minimal Live-State MCP Core → `rfmcp_mcp/` + `rfmcp_core/runtime/`
- Structured CLI Workflows → `rfmcp_cli/commands/` + `rfmcp_cli/workflows/`
- Skill Workflows → `rfmcp_skills/` + `assets/skills/` + `rfmcp_bundles/` + `rfmcp_cli/install/skills.py`
- Hint and Recovery → `rfmcp_core/hints/` + provider packages + `assets/hints/`
- Compatibility and Onboarding → `rfmcp_cli/install/`, `rfmcp_bundles/`, `tests/compatibility/`
- Flagship workflow proof → `tests/e2e/flagship_generation/`, `tests/e2e/flagship_repair/`

### Integration Points

**Internal Communication:**

- MCP and CLI both call into `rfmcp_core` services.
- Providers register through plugin entry points and are loaded by `rfmcp_core/hints/plugin_manager.py` against `rfmcp_core/hints/hookspecs.py`.
- Skill workflow definitions feed host-specific rendering through `rfmcp_bundles`.
- MCP tool registration is centralized in `rfmcp_mcp/tools/_registry.py`, which owns the allowlisted tool set, tool ids, and required capabilities.
- `_registry.py` is core-only; provider packages never participate in MCP tool registration.
- Bundle builders consume canonical assets and contract metadata, not package-private behavior.

**External Integrations:**

- Robot Framework public APIs via `rfmcp_core/robot/`
- FastMCP for MCP server exposure
- Skill workflow assets via `rfmcp_skills/` and `assets/skills/`
- Agent-host bundle/install outputs through `rfmcp_bundles/`
- Optional OS keyring integration for credential storage

**Data Flow:**

- Assets and providers are discovered → validated → merged in `rfmcp_core` → surfaced through CLI/MCP contracts → verified by integration/e2e tests.

### File Organization Patterns

**Configuration Files:**

- Root toolchain and CI config stays at repo root.
- Authoritative policy files live under `assets/policies/`.
- Package-local config is allowed only when not a shared source of truth.

**Source Organization:**

- Runtime-surface-first organization under `packages/`.
- Shared contracts and logic live in `rfmcp_core`, not duplicated in MCP or CLI packages.

**Test Organization:**

- Central `tests/` tree by runtime surface and verification level.
- Compatibility and flagship proofs remain explicit and discoverable.
- `tests/compatibility/hosts/` validates compatibility-profile claims and generated host bundle outputs; it is not a full host automation harness.

**Asset Organization:**

- Shared authoritative assets live under `assets/`.
- Generated artifacts live under `dist/` and runtime cache paths, with only authoritative inputs committed as source.

### Development Workflow Integration

**Development Server Structure:**

- Local development should target individual workspace packages through `uv` while preserving shared contract and asset ownership in `rfmcp_core` and `assets/`.

**Build Process Structure:**

- Build and verification scripts should export schemas, verify schema/model sync, build bundles, and validate contract stability before release publication.

**Deployment Structure:**

- PyPI packages are the primary shipped artifacts.
- Generated host bundles are built into `dist/bundles/` from `assets/bundles/` plus `rfmcp_bundles`.

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
The architecture is now coherent enough to support implementation startup. The Python `uv` workspace, FastMCP-based MCP layer, Typer CLI layer, file-first YAML hint system, `pluggy` providers, shared contract model, explicit skill layer, and local-policy security model now fit together without an unresolved architecture blocker. The formerly blocking seams around contract authority, provider extension shape, skill workflow structure, and baseline dependency versions are now explicitly decided.

**Pattern Consistency:**
The documented patterns support the architecture and now line up with the resolved ADR decisions. Naming, provenance, validation, serialization, provider loading, and runtime-surface-first organization are aligned strongly enough to guide multiple implementation agents without forcing them to invent their own structure.

**Structure Alignment:**
The revised project structure now reflects the important boundaries directly: contract authority, provider hookspec location, skill workflow ownership, generated-vs-authoritative asset separation, and core-only MCP tool registration are all structurally represented rather than left as informal intent.

### Requirements Coverage Validation ✅

**Feature Coverage:**
All major requirement clusters are structurally represented:

- Minimal Live-State MCP Core → `rfmcp_mcp` + `rfmcp_core.runtime`
- Structured CLI Workflows → `rfmcp_cli.commands` + `rfmcp_cli.workflows`
- Skill Workflows → `rfmcp_skills` + `assets/skills` + `rfmcp_bundles` + `rfmcp_cli.install.skills`
- Hint and Recovery → `rfmcp_core.hints` + provider packages + `assets.hints`
- Compatibility and Onboarding → install surfaces, bundle builders, compatibility tests
- Flagship Workflow Proof → explicit e2e areas for generation and repair

**Functional Requirements Coverage:**
The architecture supports the major functional requirement categories, including deterministic workflows, shared error/hint contracts, hint provenance, explicit fallback command paths, host-aware skill rendering, and bounded live-state MCP operations.

**Non-Functional Requirements Coverage:**
The architecture addresses locality and safety, stable public surfaces, structured failure reporting, portability over breadth, maintainability, hint trust, and performance/scalability concerns at an appropriate MVP level.

### Implementation Readiness Validation

**Decision Completeness:**
The architecture is complete enough to begin implementation. The decisions that directly affect workspace initialization and early cross-package implementation are now explicit: source-of-truth direction, provider extension layout, skill workflow structural ownership, and baseline versions are all documented.

**Structure Completeness:**
The structure is concrete and deterministic enough for implementation start. It defines package boundaries, canonical asset ownership, provider package shape, skill workflow ownership, tool registration boundaries, and generated artifact placement with enough specificity to prevent the earlier ambiguity.

**Pattern Completeness:**
The architecture covers the major conflict categories and closes the previously blocking ambiguity around contract authority, provider extension shape, skill workflow placement, and dependency baselines. A few policy-level details remain for later hardening, but they no longer block architecture-guided implementation.

### Gap Analysis Results

**Critical Gaps:**

- None currently open

**Important Gaps:**

- Public contract versioning and deprecation policy should be documented before public surface evolution begins.
- Provider runtime failure handling and provider/core compatibility declarations should be specified before the provider catalog grows.
- Quantitative benchmark thresholds can be added later to strengthen performance evidence, even though the architecture now defines the validation scope.

**Nice-to-Have Gaps:**

- Additional provider package examples
- More explicit mapping between compatibility test folders and CI workflow names
- OS support matrix and dev-tooling version pins
- Dedicated doc stubs for contract evolution and bundle generation

### Validation Issues Addressed

- Invalid Python module naming for MCP tools was corrected conceptually by separating MCP tool ids from Python filenames.
- Structural drift between MCP-safe runtime logic and CLI-owned workflows was corrected by moving stateless workflows out of core and introducing a dedicated runtime area.
- Provider optionality was corrected by shifting from a monolithic providers package to per-provider packages.
- Bundle ownership was clarified by separating authoritative bundle inputs from generated release output.
- Schema authority is now resolved with explicit one-way flow from authoritative models to public contracts to generated JSON Schema.
- Provider extension shape is now resolved with explicit hookspec location, package layout, ordering key, and merge semantics.
- Skill Workflow structural ownership is now resolved through an explicit `rfmcp_skills` layer plus authoritative skill assets and host renderers.
- Implementation baseline versions are now embedded for workspace initialization and CI construction.
- Performance considerations are now explicit enough to support MVP architecture validation.

### Architecture Completeness Checklist

**Requirements Analysis**

- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**Architectural Decisions**

- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed

**Implementation Patterns**

- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [ ] Process patterns documented

**Project Structure**

- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** READY WITH MINOR GAPS

**Confidence Level:** medium

**Readiness Basis:**
The previously blocking ADR items are now explicitly decided and structurally represented. Implementation can start without leaving architecture-shaping choices to individual agents. The remaining gaps are policy and hardening follow-ups rather than blockers.

**Key Strengths:**

- Clearer MCP vs CLI separation after the structure revision
- Strong shared-contract direction with explicit authority flow
- Hint/provenance model is structurally represented
- Optional-provider direction now matches the product intent
- Skill Workflows now have a distinct structural home and fallback mapping
- Centralized tests and authoritative asset ownership reduce future drift

**Areas for Future Enhancement:**

- Add explicit public contract versioning and deprecation policy
- Clarify provider runtime failure handling and compatibility declarations
- Add a short runbook for the `models` → `contracts` → `assets/schemas/` sync flow and CI drift detection
- Document the provider plugin lifecycle end-to-end with a worked example
- Pin the CI matrix directly to the declared Python and Robot Framework baselines
- Expand provider package examples and contract-evolution docs
- Add quantitative benchmark targets and measurement harness references once the benchmark pack is implemented

### Implementation Handoff

**AI Agent Guidelines:**

- Begin implementation against the documented baseline versions and explicit package boundaries.
- Treat `rfmcp_core.models` as the authoritative contract-shape layer, `rfmcp_core.contracts` as the public façade, and generated JSON Schema as derived output.
- Implement provider plugins only through the documented hookspec contract and stable ordering rules.
- Respect runtime, CLI, provider, and bundle boundaries exactly as documented.

**First Implementation Priority:**
Initialize the `uv` workspace and package boundaries using the documented baseline versions, then implement the contract model layer, schema export/sync pipeline, and hookspec skeleton before building MCP or CLI features.
