---
title: "rf-mcp Core and Robot Framework Agent Skills"
status: draft
created: "2026-05-23"
updated: "2026-05-24"
---

# PRD: rf-mcp Core and Robot Framework Agent Skills

*Working title — confirm.*

## 0. Document Purpose

This PRD defines the product requirements for a smaller, more focused Robot Framework AI tooling stack for a hobby/open-source project. It is written for the maintainer, contributors, and downstream workflow owners who may later produce UX, architecture, or epics from it. It builds on the completed PRFAQ and distillate at [`_bmad-output/planning-artifacts/prfaq-rfmcp-reloaded.md`](../../prfaq-rfmcp-reloaded.md) and [`_bmad-output/planning-artifacts/prfaq-rfmcp-reloaded-distillate.md`](../../prfaq-rfmcp-reloaded-distillate.md). Vocabulary is Glossary-anchored, features are grouped with globally numbered FRs, and inferred points are tagged inline as `[ASSUMPTION]`.

## 1. Vision

Build a Robot Framework agent-enablement stack that helps solo beginner and advanced Automation Engineers create, refactor, maintain, and heal Robot Framework tests with less orchestration friction. The product should make agent-assisted Robot Framework work feel practical instead of fragile: fewer overlapping tools, clearer workflows, deterministic fallbacks, and a smaller mental model for both humans and coding agents.

The core insight is that not every Robot Framework capability deserves to live behind MCP. The product should keep only the narrow set of behaviors that genuinely benefit from persistent live Robot Framework state and move the rest into portable, structured, stateless surfaces that modern coding agents can use reliably. This keeps the most differentiated capability while reducing maintenance and context cost.

For v1, success is not "support everything everywhere." Success is a small stack that nails a few high-value workflows for Robot Framework engineers and coding agents creating runnable Robot Framework tests for software they build.

## 2. Target User

### 2.1 Primary Persona

A solo Automation Engineer, ranging from beginner to advanced, who works with Robot Framework and uses AI coding agents to create, refactor, debug, and maintain test suites. They want less manual glue work, fewer brittle agent loops, and faster progress from failing test to repaired, runnable test.

### 2.2 Jobs To Be Done

- Help me diagnose and repair failing Robot Framework tests without forcing me to manually script every tool step.
- Help me create runnable Robot Framework tests for new software solutions my coding agent produced.
- Help me refactor or regenerate Robot Framework resources and suites without losing confidence in what still works.
- Help me move between agent hosts without relearning a completely different Robot Framework workflow every time.
- Help me fall back to deterministic local commands when an agent host or skill loader behaves inconsistently.

### 2.3 Non-Users (v1)

- Teams seeking a full enterprise test management platform.
- Users who want browser automation or API testing unrelated to Robot Framework.
- Users expecting fully autonomous unattended test healing in production pipelines on day one. `[ASSUMPTION: v1 focuses on supervised or semi-supervised agent workflows, not fully hands-off production autonomy.]`

### 2.4 Key User Journeys

- **UJ-1. An Automation Engineer repairs a failing Browser Library test with an agent.**
  - **Persona + context:** A solo engineer sees a failing Robot Framework Browser test after a product change.
  - **Entry state:** They have the project open locally and a coding agent available in a supported host.
  - **Path:** They ask the agent to inspect the failure, gather the relevant Robot Framework context, identify the probable breakage, and propose or apply a repair using the lightest viable tool path.
  - **Climax:** The engineer gets a repaired test or resource update plus a rerunnable verification path and understands why the fix was chosen.
  - **Resolution:** The suite is back to a runnable state and the engineer can continue working without manually stitching together a dozen tools.

- **UJ-2. A coding agent creates runnable Robot Framework coverage for a new software solution.**
  - **Persona + context:** A solo engineer asks a coding agent to build a software solution and also produce runnable Robot Framework tests for it.
  - **Entry state:** The software solution exists or is being created, and the agent needs Robot Framework-aware scaffolding and workflow guidance.
  - **Path:** The agent uses the documented workflow layer to discover the right test shape, scaffold files, fill in runnable structure, and validate the output through deterministic commands.
  - **Climax:** The engineer receives Robot Framework tests that run locally instead of pseudo-tests that only look plausible.
  - **Resolution:** The new solution ships with real Robot Framework coverage and the engineer can iterate from a working baseline.

- **UJ-3. An Automation Engineer refactors an existing suite without losing portability.**
  - **Persona + context:** A solo engineer wants to regenerate or restructure Robot Framework resources and tests while still using different coding agents over time.
  - **Entry state:** The suite already exists and the engineer wants maintainable, agent-friendly support instead of a one-host-specific workflow.
  - **Path:** They use the same documented commands and skills through one supported host, then later through another host with a compatibility-appropriate fallback.
  - **Climax:** The engineer can accomplish the same core workflow without being trapped in one oversized MCP integration.
  - **Resolution:** The suite evolves while the engineer retains control over portability.

## 3. Glossary

- **Human Operator** — The Automation Engineer directing the workflow and reviewing agent output.
- **Agent Host** — The environment where a coding agent runs, such as Codex, Copilot, Goose, or another MCP-capable IDE/CLI agent.
- **Live RF Context** — A persistent Robot Framework runtime context that preserves variables, imports, library state, and execution continuity across calls.
- **MCP Core** — The intentionally small Model Context Protocol surface reserved for workflows that need Live RF Context.
- **CLI Workflow** — A deterministic, stateless command path that performs one-shot Robot Framework tasks with structured outputs.
- **Skill Workflow** — A reusable instruction-and-script bundle that teaches an Agent Host how to perform a Robot Framework task consistently.
- **Compatibility Profile** — A documented support tier explaining what works in a given Agent Host, how it works, and what fallback path applies.
- **Runnable Test** — A Robot Framework test or suite that executes locally with the documented validation path instead of being only syntactically plausible.
- **Repair Workflow** — The end-to-end path from failure signal to validated change for an existing Robot Framework test or resource.

## 4. Features

### 4.1 Minimal Live-State MCP Core

**Description:** The product provides a deliberately narrow MCP Core for workflows that require Live RF Context. It is not a general dumping ground for every useful Robot Framework helper. It exists to preserve the differentiated live-state behaviors that stateless commands and skills do not replace well. Realizes UJ-1, UJ-3.

**Functional Requirements:**

#### FR-1: Live-state operations are exposed through a narrow MCP Core

The product exposes only the minimum set of live-state Robot Framework operations needed for interactive repair and runtime inspection. `[ASSUMPTION: v1 should keep the MCP Core to no more than five user-facing tools.]` Realizes UJ-1, UJ-3.

**Consequences (testable):**
- The documented MCP Core surface is smaller than the legacy broad-surface MCP design.
- Every MCP Core operation is explicitly justified by a live-state need in product documentation.
- Stateless helpers are not added to the MCP Core unless the maintainer can show they depend on Live RF Context.

#### FR-2: The MCP Core supports interactive repair workflows

The Human Operator can direct an Agent Host to inspect runtime state and step through a repair workflow when a Robot Framework failure requires persistent context. Realizes UJ-1.

**Consequences (testable):**
- A failing test repair workflow can inspect relevant runtime state without forcing the user to restart the context on every step.
- The repair flow can return enough structured information for the Human Operator to understand and validate the proposed fix.
- The MCP Core executes stepwise repair actions as real Robot Framework keywords against a persistent live execution context; a step that would fail under `robot` (e.g. a false assertion) returns a real failure, never a recorded no-op.
- Live execution state — variables, imports, and library instances — persists across steps within a session so later steps observe the effects of earlier ones.
- The MCP Core retrieves real application state (DOM, accessibility snapshots, screenshots, last API response, current open app context) captured from the actual loaded library instances where applicable, not synthetic placeholders.
- The MCP Core gets and sets real Robot Framework runtime context (variables, libraries, keyword-relevant state) in the live namespace used for repair workflows.

#### FR-3: Live-state usage is clearly bounded and documented

The product tells the Human Operator when a workflow should use the MCP Core and when it should not. Realizes UJ-1, UJ-3.

**Consequences (testable):**
- Reference docs distinguish live-state workflows from stateless workflows.
- At least one flagship workflow shows the decision boundary between MCP Core and CLI Workflow usage.
- Stateless helper functions such as library docs lookup, keyword search, suite scaffolding, and general test generation are explicitly excluded from the MCP Core unless later evidence proves they require Live RF Context.

### 4.2 Structured CLI Workflow Layer

**Description:** The product provides deterministic CLI Workflows for Robot Framework tasks that do not require Live RF Context. The CLI is the portable fallback and the default execution path for many one-shot operations. Realizes UJ-1, UJ-2, UJ-3.

**Functional Requirements:**

#### FR-4: The product provides deterministic commands for stateless high-value tasks

The Human Operator or Agent Host can run documented CLI Workflows for common stateless tasks such as validation, discovery, and scaffolding. `[ASSUMPTION: the smallest useful v1 CLI set is keyword/docs grounding, scaffolding, validation, and executable run verification.]` Realizes UJ-1, UJ-2, UJ-3.

**Consequences (testable):**
- The v1 CLI command set is documented with stable names, expected inputs, and outputs.
- A Human Operator can run the same commands manually when an Agent Host fails to load or use a Skill Workflow.
- The recommended minimum v1 CLI set covers:
  - keyword or library docs grounding to reduce hallucinated test steps
  - suite or resource scaffolding
  - static or dry-run style validation
  - executable run verification with structured result output

#### FR-5: CLI outputs are structured for agent consumption

CLI Workflows return output shapes that an Agent Host can consume without excessive parsing ambiguity. Realizes UJ-1, UJ-2.

**Consequences (testable):**
- CLI Workflows provide machine-readable output for success, failure, and next-step guidance.
- Error output is specific enough to drive a Repair Workflow instead of forcing the user to inspect raw logs first.
- Validation and run verification outputs identify likely hallucinations, missing keywords, missing libraries, and execution failures in a structured form the Agent Host can act on.

#### FR-6: CLI Workflows validate runnable output

The product gives the Human Operator a deterministic way to confirm whether created or repaired Robot Framework artifacts are runnable. Realizes UJ-1, UJ-2.

**Consequences (testable):**
- A generated or repaired artifact can be validated through a documented command path.
- Validation failures produce actionable output instead of generic pass/fail only.
- A Runnable Test is defined as a Robot Framework artifact that executes via `robot` without errors and fulfills the steps, tasks, and assertions requested by the Human Operator.

### 4.3 Skill Workflow Layer

**Description:** The product provides Skill Workflows that teach supported Agent Hosts how to perform Robot Framework jobs consistently. Skills should improve the happy path, not become the only path. Realizes UJ-1, UJ-2, UJ-3.

**Functional Requirements:**

#### FR-7: Skill Workflows package repeatable Robot Framework tasks

The product offers Skill Workflows for a small set of high-value jobs, especially repair, runnable-test generation, and refactoring support. Realizes UJ-1, UJ-2, UJ-3.

**Consequences (testable):**
- Each shipped Skill Workflow targets a named Robot Framework job and documents its expected inputs.
- The v1 skills catalog is intentionally small and focused on the flagship workflows instead of broad catalog coverage.

#### FR-8: Skill Workflows degrade gracefully to CLI Workflows

If an Agent Host does not load or execute a Skill Workflow reliably, the Human Operator can fall back to the equivalent CLI Workflow without losing the task path. Realizes UJ-1, UJ-2, UJ-3.

**Consequences (testable):**
- Each flagship Skill Workflow references its deterministic fallback command path.
- Product docs do not require native skill auto-loading behavior to make the core workflow possible.

#### FR-9: Skill guidance is host-aware without claiming false uniformity

The product documents host-specific behavior where it matters instead of promising identical skill handling everywhere. Realizes UJ-3.

**Consequences (testable):**
- Skill setup docs call out host-specific differences when they affect success.
- Unsupported or partially supported behaviors are documented as such.

### 4.4 Hint and Recovery Guidance System

**Description:** The product provides a hint system that helps Agent Hosts and Human Operators recover from wrong keywords, unclear keyword arguments, weak library documentation, and recurring Robot Framework authoring mistakes. The purpose is not only to report failure, but to guide the next correction step and reduce preventable hallucinations. Realizes UJ-1, UJ-2, UJ-3.

**Functional Requirements:**

#### FR-10: The product provides structured hints for keyword and argument failures

When a Robot Framework workflow fails because of an incorrect keyword, missing keyword, ambiguous keyword, or incorrect argument usage, the system provides structured guidance that helps the Agent Host or Human Operator recover. Realizes UJ-1, UJ-2.

**Consequences (testable):**
- Error output distinguishes between missing keyword, wrong keyword choice, wrong argument shape, and unclear library usage where possible.
- The system returns actionable next-step guidance instead of only raw execution or parser error text.
- Hints are formatted so an Agent Host can consume them programmatically. `[ASSUMPTION: hint outputs should be machine-readable alongside human-readable explanations.]`

#### FR-11: The product augments incomplete library documentation with workflow guidance

The product can supply additional context when standard Robot Framework keyword documentation is not sufficient to guide correct usage. Realizes UJ-1, UJ-2, UJ-3.

**Consequences (testable):**
- Guidance can include usage notes, expected patterns, common mistakes, or disambiguation context beyond raw keyword docs.
- The system clearly distinguishes between official library documentation, derived hints, and project-specific guidance. `[ASSUMPTION: hint provenance should be visible so users can judge trust.]`
- Guidance can be applied in both generation workflows and repair workflows.

#### FR-12: The product uses hinting to prevent repeated authoring errors

The system can add contextual guidance before or during execution to reduce predictable Robot Framework authoring errors, not just react after failure. Realizes UJ-1, UJ-2, UJ-3.

**Consequences (testable):**
- The system can surface preventive guidance when a workflow pattern is known to be error-prone.
- Recurring error categories can map to stable hinting rules or knowledge entries.
- The hint system does not silently override user intent; it guides and explains. `[ASSUMPTION: v1 hinting remains advisory rather than automatically corrective unless explicitly invoked.]`

### 4.5 Compatibility Profiles and Onboarding

**Description:** The product treats host portability as a product concern, not a marketing slogan. Compatibility Profiles and onboarding docs help the Human Operator get to first value quickly and understand what support level they are actually getting. Realizes UJ-1, UJ-2, UJ-3.

**Functional Requirements:**

#### FR-13: The product publishes explicit Compatibility Profiles

The Human Operator can see which Agent Hosts are supported in v1, what workflows are supported in each, and what fallbacks apply. Realizes UJ-1, UJ-2, UJ-3.

**Consequences (testable):**
- Each supported host has a documented support tier and setup path.
- Hosts with weaker or partial support are labeled clearly rather than implied to be equivalent.
- The first-class v1 host set is Claude Code, GitHub Copilot, Codex, OpenCode, and KiloCode.
- Agent Hosts outside the first-class set are documented as experimental until they meet the same workflow and fallback bar.

#### FR-14: The product minimizes first-run friction

The Human Operator can reach first value without navigating a sprawling multi-surface setup story. Realizes UJ-1, UJ-2.

**Consequences (testable):**
- The primary onboarding path is concise and role-appropriate for a solo maintainer project.
- At least one reference workflow can be completed from the onboarding docs without hidden prerequisite knowledge.

### 4.6 Flagship Workflow Proof

**Description:** The product proves its shape through one or two reference workflows instead of abstract architectural claims. Realizes UJ-1, UJ-2.

**Functional Requirements:**

#### FR-15: The product ships at least one flagship Repair Workflow

The Human Operator can follow a documented end-to-end Repair Workflow for a failing Robot Framework test in a supported host. `[ASSUMPTION: Browser Library failure repair is the best first flagship workflow.]` Realizes UJ-1.

**Consequences (testable):**
- A reference workflow documents inputs, expected agent behavior, fallback commands, and validation.
- The workflow demonstrates where MCP Core is used and where CLI Workflow or Skill Workflow is used.

#### FR-16: The product ships at least one runnable-test generation workflow

The Human Operator can direct an Agent Host to create runnable Robot Framework tests for a new software solution with a deterministic validation path. Realizes UJ-2.

**Consequences (testable):**
- A reference workflow covers test generation for a new or changed software solution.
- The workflow ends with runnable validation rather than stopping at generated files.

## 5. Cross-Cutting NFRs

- **NFR-1: Locality and safety.** The product must default to local, user-controlled workflows and clearly document any privileged or attach-style behavior. Sensitive runtime data exposure must be minimized.
- **NFR-2: Stable public surfaces.** User-facing MCP Core operations, CLI Workflows, and Skill Workflows must avoid churn that breaks reference workflows unnecessarily.
- **NFR-3: Structured failure reporting.** Failures must be reported in a way that helps a Human Operator or Agent Host continue the task instead of restarting from scratch.
- **NFR-4: Portability over breadth.** Adding another host is lower priority than making the supported hosts reliable.
- **NFR-5: Maintainer sustainability.** The product should reduce scope and maintenance burden relative to the broad legacy surface, not recreate it under different packaging.
- **NFR-6: Hint trust and clarity.** Hinting and added guidance must be attributable, explainable, and clearly differentiated from raw library docs or execution truth.

## 6. Constraints and Guardrails

### 6.1 Attach-Style Safety

- Attach-style behavior is opt-in and off by default.
- Attach-style behavior is documented as local-development-only for v1, not as a remote shared control plane.
- Sessions use ephemeral credentials or tokens instead of fixed defaults. `[ASSUMPTION: v1 should generate per-session credentials automatically.]`
- Attach sessions are clearly visible to the Human Operator and can be stopped explicitly.
- Documentation warns users not to expose attach endpoints beyond localhost in hobby/open-source setups.
- Sensitive state capture such as screenshots, DOM, accessibility snapshots, or API responses is documented as potentially containing secrets or private data and must be handled intentionally.

### 6.2 Scope Discipline

- The MCP Core is not the place for convenience helpers that are stateless.
- Skills improve orchestration but do not replace deterministic fallback paths.
- Host portability is defined as "documented support with fallback paths," not "identical behavior everywhere."

## 7. API Contracts / Public Surface

- The MCP Core is a small public surface reserved for live-state workflows only.
- CLI Workflows are public user-facing commands and must be documented as stable interfaces once released.
- Skill Workflows are public workflow surfaces and must declare their expected inputs, fallback commands, and host assumptions.
- Compatibility Profiles are part of the product surface because they define what "supported" means for each Agent Host.

## 8. Versioning and Deprecation Policy

- The product uses explicit versioning for public surfaces so contributors and users can understand when workflows may need updates.
- Breaking changes to the MCP Core, CLI Workflows, or shipped Skill Workflows must be called out in release notes and migration guidance.
- Deprecated surfaces should remain documented until a replacement path exists.
- Host-specific support reductions or changes must be treated as compatibility changes, not buried in general notes.

## 9. Non-Goals (Explicit)

- Building a broad enterprise test management platform.
- Reproducing every legacy helper inside the new MCP Core.
- Claiming equal support quality across every coding agent host in v1.
- Shipping fully autonomous production-grade test healing with no human review loop in v1.
- Reviving broad dashboard, memory/RAG, or generalized workflow-generation scope in the initial release.

## 10. MVP Scope

### 10.1 In Scope

- A narrow MCP Core for live-state Robot Framework workflows.
- A small CLI Workflow layer for stateless validation, discovery, and scaffolding tasks.
- A small Skill Workflow layer for the highest-value Robot Framework jobs.
- A hint and recovery guidance mechanism for keyword, argument, and usage failures.
- Compatibility Profiles for the first-class v1 host set: Claude Code, GitHub Copilot, Codex, OpenCode, and KiloCode.
- At least one flagship Repair Workflow and one runnable-test generation workflow.

### 10.2 Out of Scope for MVP

- Wide host coverage with equal behavior guarantees.
- Large skills catalogs before flagship workflows are proven.
- Deep enterprise governance features, SLAs, or regulated-industry packaging.
- Full parity with every current broad-surface helper.
- Fully unattended autonomous healing in CI without a Human Operator review loop.
- Unbounded free-form hint generation without provenance or workflow constraints.

## 11. Success Metrics

**Primary**
- **SM-1**: A supported Human Operator can complete the flagship Repair Workflow end-to-end using a supported Agent Host and documented fallback path. Validates FR-2, FR-8, FR-15.
- **SM-2**: A supported Human Operator can produce Runnable Tests for a new software solution using the documented generation workflow. Validates FR-6, FR-7, FR-16.
- **SM-3**: The released MCP Core surface is materially smaller and more focused than the broad legacy surface. Validates FR-1, FR-3.
- **SM-4**: The hint system reduces unresolved keyword and argument errors in reference scenarios by providing actionable guidance. Validates FR-10, FR-11, FR-12.

**Secondary**
- **SM-5**: First-run onboarding is short enough that a solo open-source user can reach the first reference workflow without bespoke maintainer intervention. Validates FR-14.
- **SM-6**: Supported hosts have explicit Compatibility Profiles with no ambiguous "works everywhere" claims. Validates FR-9, FR-13.
- **SM-7**: The hybrid workflow reduces input context used per reference scenario relative to the broad legacy workflow. Validates FR-3, FR-8.
- **SM-8**: The hybrid workflow reduces failed tool-call rate and total tool-call count per reference scenario. Validates FR-4, FR-5, FR-15, FR-16.
- **SM-9**: The hybrid workflow reduces combined input and output token usage for reference scenarios where the Agent Host exposes that telemetry. Validates FR-4, FR-8.
- **SM-10**: First-pass runnable rate improves for generated and repaired Robot Framework artifacts. Validates FR-6, FR-16.
- **SM-11**: Human correction burden decreases across benchmark scenarios, measured by number of manual interventions or time-to-fix. Validates FR-14, FR-15, FR-16.
- **SM-12**: Hint outputs are trusted and reused because they are clear about source, confidence, and corrective intent. Validates FR-11, NFR-6.

**Counter-metrics (do not optimize)**
- **SM-C1**: Number of supported hosts. Do not maximize host count at the expense of reliability. Counterbalances SM-5.
- **SM-C2**: Number of shipped commands or skills. Do not grow surface area before the flagship workflows are stable. Counterbalances SM-1, SM-2, SM-3.
- **SM-C3**: Amount of state captured during attach workflows. Do not maximize observability by default at the expense of safety or clarity. Counterbalances NFR-1.

## 12. Open Questions

1. What exact command names and output schemas should the minimum CLI Workflow set use?
2. Which first-class hosts can satisfy the same flagship workflows without hidden host-specific handholding?
3. What explicit acceptance scenarios will prove a generated or repaired test "fulfills the steps, tasks, and assertions requested by the Human Operator" beyond merely executing cleanly?
4. Which benchmark scenarios should be mandatory in every release comparison pack?
5. What are the first trusted sources for hint content: curated rules, project guidance, library-specific notes, failure history, or all of them?
6. How should the system rank or filter multiple hints when documentation, inferred guidance, and project-specific context disagree?

## 13. Assumptions Index

- §2.3 — v1 focuses on supervised or semi-supervised agent workflows, not fully hands-off production autonomy.
- §4.1 / FR-1 — v1 should keep the MCP Core to no more than five user-facing tools.
- §4.2 / FR-4 — the smallest useful v1 CLI set is keyword/docs grounding, scaffolding, validation, and executable run verification.
- §4.4 / FR-10 — hint outputs should be machine-readable alongside human-readable explanations.
- §4.4 / FR-11 — hint provenance should be visible so users can judge trust.
- §4.4 / FR-12 — v1 hinting remains advisory rather than automatically corrective unless explicitly invoked.
- §4.6 / FR-15 — Browser Library failure repair is the best first flagship workflow.
- §6.1 — v1 should generate per-session attach credentials automatically.
