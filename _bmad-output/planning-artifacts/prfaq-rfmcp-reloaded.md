---
title: "PRFAQ: rfmcp-reloaded"
status: "complete"
created: "2026-05-23T13:30:40+02:00"
updated: "2026-05-23T13:30:40+02:00"
stage: 5
inputs:
  - "docs/compass_artifact_wf-cfd59c3b-036d-4b2a-9ce2-522e9727a1c9_text_markdown.md"
  - "docs/deep-research-report (8).md"
  - "https://www.anthropic.com/engineering/advanced-tool-use"
  - "https://github.com/microsoft/playwright-mcp/blob/main/README.md"
  - "https://docs.github.com/en/copilot/concepts/agents/about-agent-skills"
  - "https://openai.com/academy/codex-plugins-and-skills/"
  - "https://openai.com/index/introducing-the-codex-app/"
  - "https://robotcode.io/"
  - "https://www.jetbrains.com/help/ai-assistant/configure-an-mcp-server.html"
  - "https://block.github.io/goose/docs/guides/tips/"
---

# rf-mcp Core and Robot Framework Agent Skills

## An open-source split that keeps live Robot Framework control where it matters and moves everything else into portable skills and CLI workflows

**Berlin, Germany, May 23, 2026** — Today, the maintainers of the Robot Framework MCP ecosystem announced a proposed rework of `rf-mcp`: a smaller `rf-mcp core` for the few workflows that truly require a live Robot Framework execution context, paired with a portable `rfa` CLI and Agent Skills library for discovery, scaffolding, docs, dry runs, and repair workflows across modern coding agents.

Robot Framework engineers increasingly want AI help with the messy parts of test work: understanding unfamiliar libraries, diagnosing failures, scaffolding resources, fixing selectors, and iterating on suites without hand-feeding every step. Today, they often get one of two bad options. Either they use a wide MCP server that exposes many tools and asks the agent to pick the right one repeatedly, or they fall back to loose prompt recipes and shell commands that vary by agent and break under pressure. Both paths create friction: too much context overhead, too much orchestration burden, and too much client-specific behavior.

The rework changes that balance. Instead of treating MCP as the delivery mechanism for every capability, the proposal keeps MCP only for the narrow slice that benefits from persistent live state: interactive keyword execution, attach-mode control, and runtime context inspection. Everything else moves to smaller primitives that coding agents already handle well: CLI commands with structured output, skill bundles with instructions and scripts, and repository guidance files. The outcome for Robot Framework users is simpler setup, better cross-agent portability, and less time spent fighting the transport instead of fixing tests.

> "The proposal gets stronger the moment it stops trying to make MCP the answer to everything. The value is not 'an AI server for Robot Framework.' The value is letting engineers solve Robot Framework problems reliably, with the lightest primitive that actually fits the job."
>
> — Many, project maintainer

### How It Works

A Robot Framework engineer installs three pieces, not one monolith. First, they add `rf-mcp core`, which exposes only the live-state operations that are hard to replace with stateless tools. Second, they install the `rfa` CLI, which handles deterministic one-shot tasks such as keyword search, dry runs, structured docs lookup, and scaffolding. Third, they add Robot Framework Agent Skills that teach their chosen coding agent how to combine those tools for common workflows like "fix this failing Browser test" or "generate a resource file for this page object."

From the engineer's point of view, the workflow becomes cleaner. When the task is discovery, generation, or analysis, the agent mostly uses skills plus CLI commands. When the task needs a live execution context, such as stepping through keywords inside a debug session, the agent escalates into the small MCP surface. That split reduces prompt and schema noise while preserving the one capability that current public Robot Framework tooling does not replace well: live in-process stateful control.

The proposal also assumes a stricter product boundary than the current research memo sometimes suggests. It does not promise a universal abstraction layer that behaves identically across every agent host. It promises a robust hybrid path that is strongest where official support is clear today: Copilot, Codex, Goose, and MCP-capable IDE agents, while treating client-specific skill loading behavior as an adoption variable that must be tested, not marketed away.

> "I don't care whether the fix comes from MCP, a skill, or a CLI command. I care that my agent can find the right keyword, run the right check, and stop wasting half the session deciding between fifteen overlapping tools."
>
> — Robot Framework engineer evaluating the concept

### How to Participate

The project will succeed only if it launches as a narrow, testable rework instead of a broad rewrite. The first public milestone should be an MVP with a hard boundary:

- `rf-mcp core` limited to live attach, runtime context inspection, and interactive execution
- `rfa` CLI commands for dry runs, keyword search, and scaffolding with structured JSON output
- 3-5 high-value skills focused on Browser, API, failure analysis, and suite/resource generation
- explicit compatibility docs per client rather than one blanket "works everywhere" claim

Maintainers and early adopters can participate by validating the boundary with real workflows, especially the ones the current server handles poorly or too expensively. The initial question is not "can we port every tool?" It is "which jobs become clearly better when moved out of MCP?"

---

<!-- coaching-notes-stage-1 -->
## Coaching Notes: Stage 1

- Concept type: open-source developer tooling initiative with downstream commercial relevance, not a standalone end-user SaaS product.
- Customer-first reframing applied: the raw idea started as "rework the MCP server," which is solution-led. The usable customer problem is "AI-assisted Robot Framework work is too fragile, too heavy, and too client-specific today."
- Initial assumptions challenged:
  - "Skills are the answer everywhere" is too broad; official support is clear in some hosts and fuzzier in others.
  - "MCP tool bloat alone proves the case" is incomplete; Anthropic's own guidance says tool search helps when you have 10+ tools or >10K schema tokens, which means a genuinely minimal MCP may no longer suffer the same penalty.
  - "Deprecate rf-mcp" was weaker than "shrink rf-mcp to its irreducible core."
- Why this direction over alternatives:
  - Pure skills/CLI loses the live Robot Framework execution context.
  - Pure MCP preserves that context but keeps too much orchestration inside the model.
  - Hybrid matches current ecosystem direction more closely than either extreme.
- External findings that shaped framing:
  - Anthropic documented real token overhead from large tool libraries and recommends search/deferred loading for bigger surfaces.
  - Microsoft's Playwright MCP now explicitly positions CLI+SKILLS as better for many coding-agent workflows, while keeping MCP for persistent-state loops.
  - GitHub officially documents Agent Skills for cloud agent, CLI, and VS Code agent mode, including `.agents/skills`.
  - OpenAI documents skills for Codex and says they can be shared across app, CLI, and IDE extension.
  - RobotCode already offers a REPL and `repl-server`, which means the proposal must compose with that ecosystem rather than pretending it does not exist.
  - JetBrains officially documents MCP, but this review did not find equally strong official evidence for native `SKILL.md` behavior there; that is a rollout risk.

## Customer FAQ

### Q: Why should I switch from the current `rf-mcp` design if it already works for interactive Robot Framework tasks?

A: You should not switch just because "smaller is fashionable." You should switch only if the split makes your real workflows more reliable. The case for change is strongest where the current server exposes many one-shot or documentation-heavy tools that do not need persistent state. Those are cheaper to ship as CLI commands and skills. The case is weak if most of your value comes from long-running, live-state interactive loops. The correct answer is not "replace MCP." It is "stop using MCP where it buys nothing."

### Q: How is this different from just adding tool search and keeping the existing MCP server?

A: Tool search addresses one important failure mode: too many tool definitions loaded at once. It does not automatically solve the deeper design issue that many current capabilities are not naturally stateful. If a feature is just "look up docs," "search keywords," or "run a dry run and summarize the result," putting it behind MCP still adds lifecycle, packaging, and tool-selection complexity. Tool search can make a fat server tolerable. It does not make a fat server strategically clean.

### Q: Why not skip MCP entirely and use RobotCode plus scripts?

A: Because there is still one high-value capability public CLI tooling does not replace cleanly: a live Robot Framework execution context that an agent can inspect and step through during debugging. RobotCode's REPL and related tooling are important, and this proposal should compose with them. But if you remove all live-state control, you throw away the most distinctive part of the current system.

### Q: Will this really work across Claude Code, Copilot, Codex, Goose, Cursor, JetBrains, and others?

A: Not with one blanket promise, and saying otherwise would be dishonest. The evidence is strong today for Copilot skills, Codex skills, Goose skills, and widespread MCP support. It is weaker or more client-specific for the rest of the matrix, especially around how skills are discovered and loaded automatically. The right launch posture is explicit compatibility tiers, not marketing symmetry.

### Q: Does this lower adoption effort for a normal Robot Framework engineer, or just move complexity around?

A: It lowers effort only if the first-run path becomes concrete. That means a short install path, opinionated defaults, structured CLI output, and a small set of proven skills. If the rework ships three packaging systems, six compatibility tables, and a vague "choose your agent" story, it will fail the usability test even if the architecture is cleaner.

### Q: What happens if my agent fails to load the right skill or behaves differently across hosts?

A: Then the promise of portability has been overstated. Skill-based orchestration is still model- and host-mediated. That is acceptable only when the fallback path is deterministic: the user can run the same `rfa` CLI commands manually or from a simpler agent prompt. Skills should improve the happy path, not become the only path.

### Q: What about security and privacy, especially in attach mode?

A: The risk does not disappear in the rework. In fact, it becomes more obvious, which is good. The attach bridge remains a privileged local control plane and should be treated that way: localhost-only, opt-in, explicit token handling, documented threat model, and minimal data exposure. The proposed split reduces unnecessary surface area, but it does not make live execution intrinsically safe.

### Q: Who maintains this long term, and what happens if the maintainer burns out?

A: This is one of the hardest questions, and the current concept does not answer it well enough yet. The best sustainability argument for the rework is that it reduces the size and coupling of the MCP core. But the project still needs a maintenance strategy: clear ownership boundaries, contribution paths, compatibility policy, and ruthless scope control. Without that, the rework simply creates three smaller maintenance problems instead of one large one.

<!-- coaching-notes-stage-3 -->
## Coaching Notes: Stage 3

- Customer gaps revealed:
  - The value proposition is much stronger for maintainers and heavy users than for casual users unless the first-run path is dramatically simplified.
  - Cross-agent portability is promising but not uniform; the messaging must avoid implying identical behavior everywhere.
  - Security remains a concern around attach mode and any variable/DOM/state exposure.
- Trade-off decisions:
  - Launch blocker: clearly define compatibility tiers and fallback CLI flows.
  - Fast-follow: richer skills catalog and more hosts.
  - Accepted trade-off: some advanced live-state workflows will remain MCP-only.
- Competitive context surfaced:
  - Playwright's own MCP positioning now validates a hybrid argument instead of an MCP-maximalist one.
  - RobotCode is a real adjacent platform and should be framed as complementary, not displaced.

## Internal FAQ

### Q: What is the hardest technical problem in this rework?

A: Defining the seam. Not building the CLI. Not writing the skills. The hard part is proving which operations truly require a live execution context and which only appear to. If the seam is wrong, the project either keeps too much in MCP and gains little, or strips out workflows that users actually depend on. That boundary must be validated with real task traces, not design taste.

### Q: What evidence do we have that live attach and runtime context are the irreducible core?

A: Strong qualitative evidence, weak quantitative evidence. The research docs make a defensible technical argument that live `ExecutionContext` access is unique. What is missing is hard usage evidence: which tools are actually called in real sessions, in what sequences, and which outcomes depend on state persistence. Before major refactoring, instrument usage and build a deletion candidate list from reality, not intuition.

### Q: What is the MVP, exactly?

A: A real MVP is smaller than the docs currently imply:

- 3-5 MCP tools max for live-state workflows
- `rfa dry-run`, `rfa keyword-search`, `rfa libdoc`, and one scaffolding command
- a small skill set focused on the highest-frequency debugging and generation loops
- one polished reference workflow, such as "fix a failing Browser Library test"

Anything bigger is not an MVP. It is a relapse.

### Q: Do skills give us a durable moat?

A: No. Skills are a distribution and orchestration layer, not a moat. Anyone can write skills. The durable advantage, if there is one, comes from owning the hard Robot Framework-specific workflows, especially the live-state bridge, the repair heuristics, and the packaging discipline that makes the system dependable across agents. If the unique capability is not protected and polished, the rest is easy to clone.

### Q: What is the biggest execution risk outside pure engineering?

A: Product ambiguity. The concept currently serves at least three audiences at once: maintainer, advanced AI-assisted tester, and broad cross-agent user. That is too many for an early rework. If the first release does not pick a primary user and a flagship workflow, the project will spread effort across transport, packaging, docs, and host compatibility without landing obvious value for any one group.

### Q: What kills this project?

A: Two things. First, trying to migrate every current feature before proving the hybrid boundary. Second, shipping a "portable" story that depends on host-specific skill behavior the project does not control. The project dies if it optimizes architecture before it locks down the user journey.

### Q: What should we explicitly say no to in the first release?

A: Say no to dashboard revival, memory/RAG resurrection, generalized workflow generation, and broad claims about every IDE agent behaving the same. Say no to "one more convenience tool" inside MCP unless it clearly depends on persistent live state. The first release should delete more than it adds.

### Q: What would it take to find out whether the split actually improves user outcomes?

A: Define a narrow benchmark and run it across at least two hosts. Example tasks: diagnose a failing Browser test, scaffold a new page resource, and inspect a live runtime issue. Measure setup time, tool-call count, context cost where available, success rate, and human correction rate. If the hybrid path is not better on a small benchmark, it has not earned a larger rewrite.

### Q: What is the realistic resourcing and timeline?

A: For one maintainer, this is feasible only as a staged extraction over weeks, not a parallel-platform buildout over months. A realistic path is:

- Week 1-2: instrument usage, define seam, freeze new MCP features
- Week 3-4: ship `rfa` CLI prototypes and one or two skills
- Week 5-6: shrink MCP surface and harden one flagship workflow
- Week 7+: compatibility docs, packaging cleanup, and selective expansion

If the project tries to do all clients, all skills, and all migrations at once, the timeline stops being credible.

<!-- coaching-notes-stage-4 -->
## Coaching Notes: Stage 4

- Feasibility risks identified:
  - Boundary between live-state and stateless operations is still hypothesis-heavy.
  - Host-specific skill behavior is not under project control.
  - Security posture for attach mode needs first-class documentation.
- Strategic positioning decisions:
  - Frame against "fat MCP server" and "ad hoc scripts," not against RobotCode itself.
  - Use explicit compatibility tiers rather than universal support claims.
- Unknowns with required discovery work:
  - Usage telemetry or session trace evidence for current tool importance.
  - Benchmark data comparing current and hybrid workflows.
  - Exact minimum viable skills catalog.

## The Verdict

This concept survived the gauntlet, but not in its original shape.

The strong version of the idea is not "replace `rf-mcp` with skills." The strong version is "reduce `rf-mcp` to the tiny set of operations that genuinely need live Robot Framework state, and move everything else to cheaper, more portable primitives." That is a credible product direction. It matches where the broader agent ecosystem is going, it respects what MCP is actually good at, and it preserves the most differentiated part of the current system.

The weak version of the idea is the one that tries to turn this into a general-purpose cross-agent platform narrative. That version overclaims ecosystem uniformity, understates rollout risk, and slides back toward scope sprawl.

### Forged in steel

- The hybrid architecture is the right default stance. Current ecosystem signals now support it, not just theory.
- Live Robot Framework state remains the best argument for keeping a small MCP core.
- RobotCode and CLI tooling make the non-stateful side of the split more credible than it would have been a year earlier.
- Shrinking scope is not cosmetic here; it is the maintainability strategy.

### Needs more heat

- The primary customer needs sharper definition. "All Robot Framework users with AI agents" is too broad.
- Compatibility claims need to be rewritten as tested tiers with concrete host guidance.
- The first flagship workflow must be chosen and benchmarked before larger migration work begins.
- The first-run adoption story needs to be designed, not assumed.

### Cracks in the foundation

- The proposal still lacks hard evidence about which existing tools users actually need most.
- The ecosystem support story is asymmetrical; some hosts have strong official skill support, others mainly show MCP or rules guidance.
- The project could easily relapse into scope creep by rebuilding convenience features inside the new architecture.
- Sustainability is still thin if the rework is carried mostly by one maintainer without strict boundaries.

The honest assessment: this concept is **needs more heat**, not cracked. The architecture direction is sound. The product boundary and rollout discipline are not yet proven. If you keep the scope narrow and benchmark the split on a few real workflows, this can become a strong PRD. If you keep the broader "universal agent platform for Robot Framework" framing, it will drift back into the same complexity trap it is trying to escape.
