---
title: "PRFAQ Distillate: rfmcp-reloaded"
type: llm-distillate
source: "prfaq-rfmcp-reloaded.md"
created: "2026-05-23T13:30:40+02:00"
purpose: "Token-efficient context for downstream PRD creation"
---

# Product Framing

- Reject the solution-led framing "rework the MCP server"; the customer problem is that AI-assisted Robot Framework work is currently too heavy, too fragile, and too client-specific.
- Treat this as an open-source developer tooling initiative, not a broad SaaS launch.
- Primary value proposition: keep live Robot Framework control where it is uniquely valuable, and demote everything else to simpler primitives.

# Core Thesis

- The defensible architecture is hybrid: minimal MCP for live-state workflows plus CLI plus Agent Skills for stateless workflows.
- The unique retained capability is live in-process Robot Framework `ExecutionContext` style control, especially attach/debug loops.
- The rework only wins if it defines a ruthless boundary for what remains in MCP.

# Rejected Framings

- Rejected: "Deprecate rf-mcp." Reason: it discards the one differentiated capability that still appears real.
- Rejected: "Skills replace MCP." Reason: skills do not preserve persistent live state.
- Rejected: "Universal support across every target client." Reason: official ecosystem support is uneven and must be treated as a rollout variable.
- Rejected: "Tool bloat alone proves the case." Reason: a truly small MCP surface may avoid the worst token-cost failure modes.

# External Validation Signals

- Anthropic documented that large MCP tool libraries can consume major context budget and recommends deferred loading or search for bigger tool surfaces.
- Microsoft's Playwright MCP README explicitly says coding agents may benefit more from CLI+SKILLS, while reserving MCP for persistent-context loops.
- GitHub Copilot officially supports Agent Skills across cloud agent, CLI, and VS Code agent mode, including `.agents/skills`.
- OpenAI documents skills for Codex and says skills can be used across app, CLI, and IDE extension.
- Goose officially documents both skills and the need to limit unnecessary tools for context reasons.
- RobotCode already offers REPL and `repl-server`, so the project should compose with RobotCode rather than pretend it is absent.
- JetBrains officially documents MCP well; this review did not find equivalently strong official evidence for native `SKILL.md` support there.

# Requirements Signals

- Must preserve a tiny live-state MCP core for interactive execution, attach control, and runtime context inspection.
- Must ship a deterministic CLI fallback so the system still works when skills are not loaded or hosts behave differently.
- Must provide structured JSON output from CLI commands for agent consumption.
- Must include host-by-host compatibility documentation instead of one generic support table.
- Must document attach-mode security posture as a first-class concern.

# Candidate MVP Scope

- MCP core capped at roughly 3-5 tools.
- CLI commands: `dry-run`, `keyword-search`, `libdoc`, and one scaffolding command.
- Skills limited to a few high-value workflows such as Browser failure repair, API test diagnosis, resource generation, and docs lookup.
- One flagship reference workflow should anchor the release; "fix a failing Browser Library test" is the strongest candidate from the current analysis.

# Explicit Non-Goals for First Release

- No dashboard revival.
- No memory/RAG resurrection.
- No generalized workflow generation layer.
- No broad promise that all IDE agents will auto-load and use skills the same way.
- No migration of every current convenience tool before usage evidence supports it.

# Technical Context and Constraints

- Boundary definition is the hardest technical task; the project needs evidence about which current tools truly depend on live state.
- Skills improve orchestration but remain host- and model-mediated; they are not fully deterministic.
- CLI cold starts and shell orchestration are acceptable for one-shot tasks but not for stateful interactive loops.
- Security concerns remain concentrated around attach mode and any exposed variables, DOM, or runtime state.

# Competitive and Positioning Context

- The project should frame itself against "fat MCP server" and "ad hoc script pile," not against RobotCode itself.
- Skills are not a moat; the moat is the Robot Framework-specific live-state bridge and the quality of the packaged workflows.
- The strongest strategic move is scope reduction plus interoperability, not surface-area parity.

# Open Questions

- Which current rf-mcp tools are actually used most in real sessions?
- Which workflows measurably improve when moved from MCP to CLI plus skills?
- Which hosts reliably support the intended skill loading and execution behavior in practice, not just in theory?
- What is the minimum viable skills catalog that makes the hybrid story compelling on day one?
- How much maintainer capacity exists for parallel packaging, compatibility docs, and workflow hardening?

# Suggested Discovery Work

- Instrument current usage or collect representative task traces before major extraction work.
- Benchmark current vs hybrid on a small set of tasks across at least two hosts.
- Track setup time, tool-call count, success rate, correction rate, and context overhead where visible.
- Validate security expectations for attach mode and define safe defaults before wider rollout.

# Resource and Timeline Signals

- A solo-maintainer path is feasible only as staged extraction, not a simultaneous rewrite.
- Reasonable sequence: freeze scope, instrument usage, ship CLI prototypes, ship 1-2 skills, shrink MCP, then expand selectively.
- If the project attempts all hosts and all migrated features at once, the plan stops being credible.

# Verdict Actions

- Forged in steel: keep the hybrid direction, protect the live-state core, and lean on CLI plus skills for the rest.
- Needs more heat: tighten the customer definition, benchmark one flagship workflow, and rewrite compatibility claims into tested tiers.
- Cracks in the foundation: missing usage evidence, asymmetric host support, and high scope-creep risk.
- Downstream PRD should treat portability as a design objective with explicit confidence levels, not a binary promise.
