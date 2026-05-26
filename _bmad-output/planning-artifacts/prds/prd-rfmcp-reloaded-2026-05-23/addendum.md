# Addendum: rf-mcp Core and Robot Framework Agent Skills

## Purpose

This addendum preserves technical context and product-shaping detail that informed the PRD but does not belong in the PRD's main narrative. It is intended as downstream context for architecture, implementation planning, and future workflow expansion.

## Source Artifacts

- `docs/compass_artifact_wf-cfd59c3b-036d-4b2a-9ce2-522e9727a1c9_text_markdown.md`
- `docs/deep-research-report (8).md`
- `_bmad-output/planning-artifacts/prfaq-rfmcp-reloaded.md`
- `_bmad-output/planning-artifacts/prfaq-rfmcp-reloaded-distillate.md`

## Technical Direction Preserved From Discovery

- The rework should follow a hybrid shape: a tiny MCP Core for live-state Robot Framework operations, plus CLI Workflows and Skill Workflows for stateless tasks.
- The main technical risk is choosing the seam incorrectly: leaving too much in MCP or removing workflows that actually need state.
- The most plausible retained live-state value is attach/debug style context reuse and runtime inspection during repair loops.
- The product now also requires a hint and recovery guidance mechanism for wrong keywords, wrong arguments, unclear library docs, and recurring authoring mistakes.

## Candidate v1 Public Surface Hypothesis

These are not locked product requirements yet, but they are strong starting points for architecture and implementation planning:

- **Candidate MCP Core behaviors**
  - interactive keyword execution in live context
  - stepwise execution across a repair session
  - runtime context inspection
  - application state retrieval such as DOM, accessibility snapshots, screenshots, last API response, and current open app context where relevant
  - getting and setting Robot Framework runtime context including variables, libraries, and keyword-relevant state
  - attach/session status and control

- **Candidate CLI Workflows**
  - keyword or docs grounding
  - suite or resource scaffolding
  - static or dry-run validation
  - executable run verification with structured failure output
  - hint retrieval or hint shaping against known failure categories

- **Candidate Skill Workflows**
  - Browser Library repair
  - API test diagnosis or regeneration
  - runnable-test generation for new software solutions
  - refactor/regenerate resource workflow
  - keyword and argument recovery workflow using curated hints plus contextual guidance

## Compatibility Notes

- First-class v1 hosts confirmed by user direction: Claude Code, GitHub Copilot, Codex, OpenCode, and KiloCode.
- Any host outside that set should be documented as experimental until it satisfies the same reference workflows and fallback expectations.
- Earlier research suggested strong evidence for Codex, GitHub Copilot, and Goose skills plus broad MCP support across multiple hosts; the explicit v1 host set is a product decision and may exceed the set with the strongest prior external evidence.

## Benchmarking Direction

The PRFAQ surfaced a need for evidence before scope expansion. A practical benchmark pack would include:

- repairing a failing Browser Library test
- generating runnable Robot Framework tests for a new software solution
- refactoring or regenerating an existing Robot Framework resource

Suggested measures:

- setup friction
- tool-call count
- failed tool-call rate
- validation success rate
- first-pass runnable rate
- human correction rate
- time-to-first-runnable-suite
- time-to-repair
- input context size
- input/output token usage where host telemetry allows it
- context or surface complexity proxies

## Scope Protection Notes

- The rework should explicitly resist reintroducing dashboard, RAG/memory, and convenience helpers into the MCP Core.
- The first release should prove a few workflows instead of chasing total helper parity.
- Portability is a design objective, but "same behavior in every host" is not a credible initial promise.

## Hint System Implications

- The hint system should be treated as a trust feature, not only a convenience feature.
- Hint provenance matters: the architecture should distinguish raw library documentation, curated guidance, project-specific hints, and inferred recovery suggestions.
- Hinting should remain advisory by default in v1; automatic silent correction would raise trust and debugging risks too early.
- The most likely architectural homes for hinting are CLI grounding, skill guidance, and structured failure shaping, not the live-state MCP Core unless a specific live repair case truly needs it.
- Hint ranking and conflict resolution will matter once multiple knowledge sources exist.

## Attach-Style Safety Suggestions

- Default to localhost-only exposure with no remote sharing guidance in v1 docs.
- Use ephemeral session credentials instead of static defaults.
- Make attach an explicit operator action, not an automatic background behavior.
- Document how to terminate sessions quickly and verify they are closed.
- Warn that DOM, screenshots, accessibility snapshots, and API payloads may contain secrets or sensitive data.
