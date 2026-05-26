# Critical Architectural Review of rf-mcp and Alternatives for Robot Framework × AI Coding Agents

## TL;DR

- **Don't deprecate rf-mcp — but radically shrink it.** The genuinely defensible core is the live RF `ExecutionContext` bridge (interactive `execute_step`, `attach`, RF Namespace introspection). Everything else — keyword discovery, library docs, scenario analysis, suite generation, locator guidance, the Django dashboard, library recommendations, intent_action, memory/RAG — should move to Agent Skills + a thin CLI, because that is the only path that is portable across Claude Code, VS Code Copilot, Cursor, Codex CLI, JetBrains AI Assistant, OpenCode, and Goose without the schema-bloat tax that is now well-documented for MCP servers (Anthropic's own engineering team reports tool definitions consuming up to 134K tokens — 67% of a 200K context window — before optimization).
- **Bet on the Agent Skills standard, not on MCP, for the bulk of value.** Skills are now natively supported by Claude Code, Cursor 2.4, GitHub Copilot in VS Code, Codex CLI (Simon Willison, December 12 2025: *"OpenAI aren't talking about it yet, but it turns out they've adopted Anthropic's brilliant 'skills' mechanism in a big way — Skills are now live in both ChatGPT and their Codex CLI tool"*), OpenCode, and Goose; they all read SKILL.md from `.claude/skills/`, `.cursor/skills/`, `.codex/skills/`, `~/.config/goose/skills/`, etc. They use progressive disclosure (~20–50 tokens per skill until loaded), so they don't burn 30–70% of the context window the way a 15-tool MCP server does. `robotframework-agentskills` is already the right vehicle; rf-mcp's 15+ tool surface is the wrong one.
- **Recommended target architecture (Option B, "Minimal MCP + Skills + CLI"):** keep an rf-mcp `core` with ≤5 tools (`execute_step`, `get_rf_context`, `attach_status/stop`, `run_dry`), move documentation/templates/workflows to `robotframework-agentskills`, and add a thin `rfa` CLI (`rfa libdoc`, `rfa dry-run`, `rfa keyword-search`, `rfa scaffold`) that agents call via their universal Bash tool. Drop the Django dashboard, drop HTTP/Kubernetes transport, drop the library recommender, drop the memory/RAG layer.

---

## 1. What rf-mcp Actually Is Today (verified against repo `main` @ v0.31.1)

### 1.1 Code-level facts

- **Build/runtime:** `hatchling`, `requires-python >=3.10`, FastMCP `>=2.8.0`, Robot Framework `>=7.0`. 393 commits, 18 releases since launch; latest tagged release v0.30.0 on Feb 16 2026; `main` is already at v0.31.1.
- **Core dependencies (small):** `fastmcp`, `robotframework`, `pydantic`, `beautifulsoup4`, `lxml`, `python-dotenv`, `pyyaml` — only seven. The architectural-debt picture is **not** ChromaDB / diskcache / sentence-transformers (those are not in `pyproject.toml`); the actual vector stack is an optional `memory` extra: `sqlite-vec>=0.1.6` + `model2vec>=0.4.0`. The Django dashboard is an opt-in `frontend` extra (`django>=4.2,<5.0` + `uvicorn[standard]>=0.24`). This matters: rf-mcp's *core* is leaner than commonly assumed. The bloat is in **tool surface and feature scope**, not transitive dependencies.
- **Tool surface (≈15 top-level tools):** `analyze_scenario`, `recommend_libraries`, `manage_library_plugins`, `manage_session`, `execute_step`, `execute_flow`, `intent_action`, `find_keywords`, `get_keyword_info`, `get_session_state`, `check_library_availability`, `set_library_search_order`, `manage_attach`, `build_test_suite`, `run_test_suite`, `get_locator_guidance` — with extras (`memory`) adding more. The README itself states that full-surface tool descriptions consume **~7,000 tokens** and that tool profiles compress this to ~1,000.
- **Notable internal hack:** `utils/rf_variables_compatibility.py` monkey-patches Robot Framework's `Variables`/`Namespace` to add `set_global/set_test/set_suite/start_keyword/end_keyword/replace_variables` shims for RF 6↔7 compatibility — concrete evidence that rf-mcp is reaching deep into RF internals, which is both its unique value and its maintenance time-bomb.
- **Debug attach bridge:** `robotmcp.attach.McpAttach` is a real RF library that opens an HTTP server on `127.0.0.1:7317` and exposes the live `ExecutionContext` (variables, imports, keyword search order) so `execute_step(..., use_context=true)` can run inside a debugged RobotCode session. **This is the part with no equivalent anywhere else in the ecosystem.**

### 1.2 What rf-mcp does well (genuine strengths)

1. **Live, in-process RF execution with state persistence.** Nothing else — not RobotCode's REPL, not `robot --dryrun`, not Playwright MCP — gives an agent a long-lived RF `Namespace` + `VariableScopes` it can poke, mutate, and inspect between calls. This is the only capability that strictly *needs* an MCP server.
2. **Attach bridge.** Re-using a developer's live debug session is a genuinely novel idea and the highest-leverage feature for "fix failing test" workflows.
3. **RF-native execution semantics.** Because it goes through `EXECUTION_CONTEXTS`, keywords behave the same as in a real run (search order, variables, library state), unlike toy "exec keyword" wrappers.
4. **Multi-library coverage with profiles.** The `tool_profile` mechanism (`browser_exec`, `api_exec`, `discovery`, `minimal_exec`, `full`) is a real, pragmatic answer to MCP token bloat.
5. **Small-LLM optimizations.** `intent_action`, type-constrained `Literal` enums, auto-coercion of JSON-stringified arrays, navigate-fallback — these are well-considered for 8K-32K models.

### 1.3 Where rf-mcp is structurally weak

1. **Tool surface is too broad for what MCP is good at.** Of the ~15 tools, only `execute_step`, `execute_flow`, `get_session_state`, `manage_session`, and `manage_attach` actually need live server state. `find_keywords`, `get_keyword_info`, `get_locator_guidance`, `recommend_libraries`, `check_library_availability`, `analyze_scenario`, `build_test_suite`, `run_test_suite` are pure-function or one-shot operations that would be cheaper and more portable as CLI commands invoked from a skill.
2. **Self-confessed 7K-token tool description footprint.** Samir Amzani's Apideck engineering blog measured a real team running GitHub + Playwright + an IDE integration MCP server simultaneously: *"That's 72% of the context window burned on tool definitions. The agent had 57,000 tokens left for the actual conversation."* Anthropic's own engineering team writes *"At Anthropic, we've seen tool definitions consume 134K tokens before optimization"* — 67% of a 200K context window — and Anthropic's Tool Search delivers *"an 85% reduction in token usage."* rf-mcp's "tool profiles" workaround is treating a symptom of having too many tools registered in the first place.
3. **Hidden coupling to RF internals.** The `CompatibleVariables`/`CompatibleNamespace` monkey-patch is a leading indicator: every RF point release threatens to break rf-mcp in ways `robot --dryrun` does not. RF 8 will be expensive.
4. **Three deployment modes for one user.** stdio + HTTP + Docker + Docker-VNC + Django dashboard + Kubernetes. For a tool whose 95% use case is "a developer with VS Code on their laptop," this is wildly over-built.
5. **Discoverability/onboarding friction.** Setup requires the right venv, the right Python, often `rfbrowser init`, often Playwright deps, optionally Docker, optionally the dashboard. Compare to a skill: `git clone … ~/.claude/skills/robotframework-browser-skill` — done.
6. **Agent-quality variance.** rf-mcp's interactive pattern depends heavily on the agent calling tools repeatedly in the right order. This works well in Claude Code, is hit-or-miss in Cursor and Cline, and is poorly documented for Codex CLI / Goose / OpenCode users who would benefit from skills instead.
7. **Community footprint is small.** ~72 stars / 13 forks / 5 contributors at the time of review. Maintenance is overwhelmingly on the user. Reducing surface area is a survival strategy, not a vanity exercise.

---

## 2. The Alternative Approaches, Honestly Compared

### 2.1 Agent Skills (SKILL.md) — the strongest contender

**What it is.** A folder with `SKILL.md` (YAML frontmatter `name` + `description`, then Markdown body), optional `scripts/`, `references/`, `assets/`. Loaded via progressive disclosure: ~20–50 tokens of metadata until the agent decides to load the body. Standard is stewarded by the Agentic AI Foundation under the Linux Foundation (per agents.md and agentskills.io); adopters include Claude (Claude Code + claude.ai), OpenAI Codex, GitHub Copilot in VS Code, Cursor 2.4, OpenCode, Goose, Amp, Letta, Kiro, Antigravity. Simon Willison's December 12 2025 blog post is explicit: *"OpenAI aren't talking about it yet, but it turns out they've adopted Anthropic's brilliant 'skills' mechanism in a big way — Skills are now live in both ChatGPT and their Codex CLI tool."* All seven of the user's target agents are Skills-compatible today.

**Why it fits Robot Framework so well.**
- RF testing is heavy on **procedural knowledge** ("when using Browser Library, prefer text= selectors; for Strict Mode multi-match errors, append `>> nth=0`; for API tests use RequestsLibrary's `Create Session` first"). That's exactly the domain skills are designed for.
- The user already maintains `robotframework-agentskills` with 11 skills, the right canonical-source layout (root `skills/` synced to plugin and VS Code extension distributions), and proper script bundles. The infrastructure is already in place.
- Skills carry executable scripts. The 6 of 11 existing skills that are "script-based" (Keyword Builder, Libdoc Search, Testcase Builder, Resource Architect, RF Results, Drift Detection) are exactly the pattern that replaces 80% of rf-mcp's non-execution tools.

**Limitations (real, not handwaved).**
- **No live state.** A skill cannot keep an RF `Namespace` alive between turns. If the workflow is "execute step → inspect variables → execute next step," skills alone cannot do it.
- **Discovery is per-agent.** OpenCode reads `.opencode/skills/`, `.claude/skills/`, `.agents/skills/`; Cursor reads `.cursor/skills/`; Codex CLI reads `.codex/skills/` and `~/.codex/skills/`; Goose reads `~/.config/goose/skills/`. The `~/.agents/skills/` convention is emerging as the cross-tool shared path but is not universally honoured yet.
- **Selection is LLM-driven.** Claude (and clones) decides whether to load a skill from its description alone — no embedding match, no keyword routing. Bad descriptions = skill never fires.
- **No standard skill discovery across the ecosystem yet.** Each host curates its own list; no `.well-known/skills` equivalent of MCP's emerging Server Cards.

**Verdict.** Skills should own everything that is procedural, documentary, or scriptable. That covers ≥70% of rf-mcp's current tool surface.

### 2.2 CLI tools (Bash from the agent)

**What it is.** Ship an `rfa` (or `robotmcp`) CLI with subcommands. Agents call it via their universal Bash/Terminal tool, which every coding agent supports.

**Why it's underrated.** The Playwright MCP README itself now says (verbatim, from `microsoft/playwright-mcp`): *"If you are using a coding agent, you might benefit from using the CLI+SKILLS instead. CLI: Modern coding agents increasingly favor CLI–based workflows exposed as SKILLs over MCP because CLI invocations are more token-efficient: they avoid loading large tool schemas and verbose accessibility trees into the model context."* Bytedance's Lark, Google Workspace (`gws`), and Zilliz/Milvus all shipped CLI+Skills in late 2025 / early 2026 specifically to escape MCP schema bloat. A Scalekit benchmark of 75 head-to-head tasks measured 4–32× higher token usage for MCP vs CLI on identical operations.

**RF already has substantial CLI surface to build on.**
- `robot`, `rebot`, `libdoc`, `testdoc` ship with Robot Framework.
- `robotcode` (Daniel Biehl's toolkit, RobotCode VSCode/PyCharm extension's backbone) provides `robotcode robot`, `robotcode analyze code`, `robotcode discover`, `robotcode testdoc`, `robotcode repl`, `robotcode repl-server` — and `robotcode repl` is *the* stdlib-blessed RF interactive interpreter.
- `robocop` (now the official linter) and `robotidy` (formatter) are best-in-class.

A thin `rfa` CLI need only fill gaps: structured JSON output for libdoc (for keyword search), a one-shot dry-run wrapper that returns a normalized error model, a scaffolder for new suites/resources. Most of rf-mcp's discovery and analysis tools become 20-line Click commands.

**Limitations.**
- No persistent state between invocations (same as skills).
- Each call spawns Python (~200–500 ms cold start without `uv`). For interactive REPL-style work this is the wrong shape.
- Agents will sometimes pipe huge stdout into context if not careful. Need explicit `--json --summary` and `--save-to <file>` patterns.

### 2.3 LSP (RobotCode / robotframework-lsp)

**What it is.** RobotCode (`robotcode-language-server`) and the older Robocorp `robotframework-lsp` already expose completions, diagnostics, hover, refactoring, go-to-definition, semantic tokens, code lens, inlay hints, workspace symbols, and a DAP debugger over LSP — usable by VS Code, IntelliJ/PyCharm (via LSP4IJ), Neovim, Helix, Zed, etc.

**The honest truth about LSP for agents.**
- **LSP is for the IDE, not for the agent.** Agents don't speak LSP; they speak MCP, CLI, file I/O, and now Skills. The right pattern is "use the LSP indirectly via an MCP bridge that exposes LSP features" (a "LSP-as-MCP" wrapper, which Microsoft has been experimenting with for TypeScript) — but for RF this is overkill given `robotcode analyze` already does most of what an agent needs.
- The Robocorp `robotframework-lsp` has effectively been abandoned for RF 7 (community thread on `forum.robotframework.org` explicitly noting "the authors announced that Robot Framework 7 will not be supported"). **RobotCode is the de-facto Robot Framework LSP going forward.**
- The user's planned `rfx` IDE extension should clearly build on `robotcode` rather than reinvent the LSP layer. The right division of labour is: RobotCode owns editor UX; rf-mcp/skills own agent UX; both share the same `robotcode` CLI underneath.

**Bottom line.** Don't compete with RobotCode. Compose with it. Have skills *invoke* `robotcode analyze code --format json` rather than re-implementing analysis in MCP tools.

### 2.4 Convention-based / file-based (`AGENTS.md`, `.cursorrules`, `CLAUDE.md`)

**What it is.** A markdown file at repo root that every modern agent reads automatically. The `AGENTS.md` standard is now governed by the Agentic AI Foundation and supported by OpenAI Codex, Cursor, Factory, Amp, Jules (Google), Aider, and others; OpenAI's own monorepo uses 88 nested `AGENTS.md` files. A Princeton/arXiv study (arXiv:2601.20404) across 124 PRs in 10 repos quantified the effect specifically: *"the presence of AGENTS.md is associated with a lower median runtime (Δ28.64%) and reduced output token consumption (Δ16.58%), while maintaining a comparable task completion behavior."*

**When sufficient.** "Use Robot Framework 7 syntax. Run tests with `uv run robot tests/`. Lint with `robocop`. Format with `robotidy`. Place page objects in `resources/pages/`." That kind of project convention belongs in `AGENTS.md`, full stop.

**When insufficient.** Anything procedural that varies per task ("how to debug a Browser Library Strict Mode failure") is too long for `AGENTS.md`, which agents always-load. That's what skills are for. The two compose: `AGENTS.md` for repo invariants; skills for capabilities.

### 2.5 Hybrid: minimal MCP + Skills + CLI (the recommended target)

**The truly minimal MCP surface (≤5 tools) needed for capabilities that require live state:**

| Tool | Why MCP (not CLI/Skill) |
|---|---|
| `execute_step` | Needs persistent RF `Namespace` and library state between calls |
| `get_rf_context` | Returns variables, imports, libraries, search order, page state, application state — only meaningful against a live process |
| `attach_status` / `attach_stop_bridge` | Manages the live HTTP bridge to a debugged RobotCode suite |
| `run_dry` (optional, could be CLI) | One-shot `robot --dryrun` with normalized JSON — keep here only if combined with state |

Everything else moves out. The MCP server installable shrinks from ~15 tools + Django + Docker + VNC + memory/RAG + plugin registry to **one Python module that wraps RF's `EXECUTION_CONTEXTS` and exposes 4–5 tools.** Most of the `robotmcp.attach.McpAttach` library stays; almost everything in `intent_action`, `recommend_libraries`, `analyze_scenario`, `find_keywords`, `get_keyword_info`, `get_locator_guidance`, `build_test_suite`, `run_test_suite`, `check_library_availability`, `manage_library_plugins` becomes a skill + CLI command.

---

## 3. Cross-Agent Compatibility Matrix

This is the deciding factor. The user wants reach across seven agents.

| Agent | MCP support | Agent Skills (SKILL.md) | Bash/Shell tool | `AGENTS.md` |
|---|---|---|---|---|
| Claude Code | First-class | First-class (native) | Yes | Yes (also `CLAUDE.md`) |
| Claude Desktop | First-class | Custom skills via ZIP upload | No (limited) | Partial |
| VS Code + GitHub Copilot | Yes (Agent Mode + MCP, 2025) | Yes (`chatSkills` contribution + workspace `.github/skills` and `.claude/skills` paths read in 2026) | Yes (terminal tool) | Yes |
| Cursor | Yes | Yes (Cursor 2.4, Jan 2026; reads `.cursor/skills/`, plus `.claude/skills/` per docs) | Yes | Yes |
| Codex CLI (OpenAI) | Yes | Yes (announced Dec 2025; `/skills` slash command; `~/.codex/skills`) | Yes (it *is* a CLI) | Yes (created the standard) |
| JetBrains AI Assistant | Yes (2025.2 bundled MCP server) | Indirect — JetBrains AI doesn't yet ship native SKILL.md loading, but Codex/Claude integration via JetBrains IDEs picks them up | Yes | Yes |
| OpenCode | Yes | Yes (first-party `skill` tool since late 2025) | Yes | Yes |
| Goose (Block) | Yes (founding MCP citizen) | Yes (built-in extension; reads `~/.config/goose/skills/` and `~/.claude/skills/`) | Yes | Yes |
| Cline | Yes | Via plugin (not first-party yet) | Yes | Yes |
| Continue.dev | Yes (CI-focused now) | Indirect | Yes | Yes |
| Aider | No native MCP | No native skills | Yes (it *is* the terminal) | Yes |

**Takeaways.**
- **Bash is the only universal capability.** Every agent on the list can execute a CLI.
- **Skills now cover 7 of 7 named agents.** This was not true 12 months ago. It is decisively true today.
- **MCP support quality varies.** Claude Code and Codex CLI are excellent; Cursor and VS Code Copilot work well; Cline and Goose work but tool-bloat impact is heavier on smaller models; Aider effectively doesn't support MCP. A pure-MCP strategy strands Aider users entirely.
- **For Robot Framework specifically:** developers using JetBrains for Python work, Aider for terminal pair-programming, or running smaller local models via Cline/Continue are all *better served by skills + CLI* than by rf-mcp's MCP surface.

---

## 4. Capability-by-Capability Mapping

| Capability | Best primitive | Why |
|---|---|---|
| Interactive keyword execution (stateful) | **MCP tool** (`execute_step`) | Requires persistent RF Namespace |
| RF Namespace / VariableScopes introspection | **MCP tool** (`get_rf_context`) | Live-process-only |
| Batch keyword execution | **MCP tool or CLI** | Stateful → MCP; otherwise a `rfa exec --batch file.yml` |
| Static analysis / `--dryrun` | **CLI** (`robotcode analyze code` or `robot --dryrun`) | One-shot, deterministic |
| Library discovery & docs | **CLI + Skill** (`rfa libdoc --json` invoked from a libdoc-search skill) | `libdoc` already exists; skill provides ranking/intent |
| Test data generation | **Skill** (with optional Python script using Faker / `robotframework-ai`) | Pure procedural knowledge |
| Memory / RAG over keyword library | **Skill + CLI** (`rfa keyword-search "click button"` over a local sqlite-vec index built once) | Don't bake into MCP — the index is just a file |
| Debugging running tests | **MCP tool** (`attach_*`) + Skill that documents the workflow | The bridge is the unique value |
| Refactoring test suites | **Skill + CLI** (`robotidy` + `robocop --fix` + a refactor skill) | Existing tools cover 90% |
| Fixing failing tests | **Skill + MCP (attach)** | Skill describes diagnosis workflow; MCP attach inspects live state |
| Generating tests from requirements | **Skill** (with scripts that scaffold via `robotcode discover` and existing resources) | Pure generation, no live state |
| Reviewing test quality | **Skill + CLI** (`robocop` + a review skill defining the rubric) | Robocop is the engine; skill is the methodology |

**Result: 9 of 12 capabilities have their "best" answer outside MCP.** Only three genuinely need MCP, and they're closely related (interactive execution + RF context + attach bridge).

---

## 5. Recommended Architectures (with explicit trade-offs)

### Option A — Pure Skills + CLI (deprecate rf-mcp)

- **Shape:** Ship `robotframework-agentskills` (existing) + new `rfa` CLI. No MCP server.
- **Maintenance:** Low. No protocol/transport, no FastMCP version churn, no Django, no Docker images. Two pure-Python packages.
- **Portability:** Highest. Works in Aider, Continue, JetBrains AI, any future agent — anywhere with a shell.
- **Capability gap:** **You lose stateful execution.** No live RF Namespace between turns. Workflows like "execute this, inspect `${customer_id}`, then execute the next step using it" become awkward: agents would have to write step-into-suite, run, parse output, write next step. The current rf-mcp magic (incremental RF building with state) is gone.
- **Honest verdict:** This is correct for ≥80% of test-authoring use cases and wrong for the most-impressive rf-mcp demos.

### Option B — Minimal MCP + Skills + CLI (RECOMMENDED)

- **Shape:** `rf-mcp-core` (≤5 tools, ~2,000 LOC max, single-purpose) + `robotframework-agentskills` (skills + scripts that shell to `rfa`/`robotcode`/`robocop`) + `rfa` CLI.
- **Maintenance:** Medium. The MCP core is small enough that one person can own it; the RF-internal hacks live in one tightly scoped module rather than scattered across 15 tools.
- **Portability:** High for skills/CLI; medium for MCP (the 30% of users on Aider / JetBrains-AI / Continue lose only the interactive execution, which they can fall back on by writing-then-running).
- **Capability coverage:** Full. The unique stateful execution and attach bridge are preserved; everything else moves to portable primitives.
- **UX:** Improves on today. Agents that load 5 small tools have plenty of context left for actual work; small-LLM users no longer need the `tool_profile` workaround.

### Option C — Keep rf-mcp, simplify

- **Shape:** Today's rf-mcp, with deletions: drop Django dashboard, drop Docker-VNC, drop HTTP/Kubernetes transport (stdio-only), drop the memory/RAG extra (or replace with a JSON file), drop `recommend_libraries` (skill), drop `analyze_scenario` (skill), drop `get_locator_guidance` (skill), drop `intent_action` (skill), consolidate `find_keywords`/`get_keyword_info`/`check_library_availability` into a single optional `keyword_search` tool.
- **Maintenance:** Medium-high. Still bound to RF internals, still has 7 tools and tool-profile complexity.
- **Portability:** Same as today — limited by MCP coverage.
- **Capability coverage:** Same as today.
- **Honest verdict:** This is the "I've invested heavily, I don't want to throw work away" path. It's defensible but it doesn't move the user toward where the ecosystem is going.

**Recommendation: Option B.** Specifically, in this order:

1. Move documentation, locator guidance, library recommendations, scenario analysis, and library introspection out of rf-mcp into existing/new skills in `robotframework-agentskills`. (~2 weeks)
2. Author `rfa` CLI (Python + Click + `robotcode` underneath) with: `libdoc-json`, `keyword-search`, `dry-run`, `scaffold-suite`, `lint`, `format`, `repl-once`. (~1–2 weeks)
3. Strip rf-mcp to `rf-mcp-core` = `execute_step`, `execute_flow`, `get_session_state`, `manage_session`, `manage_attach`, plus the `McpAttach` library. Mark old rf-mcp v0.30/0.31 as the last release of the "fat" tree, branch a v1.0 "core" with semantic version reset signalling the change. (~2–3 weeks)
4. Announce: rf-mcp continues for live execution; agent-skills is the supported way to get RF expertise into any agent.

---

## 6. Industry Direction (so the user doesn't bet against the wind)

- **Playwright MCP itself now recommends "CLI + SKILLS" over MCP for coding agents.** That's Microsoft, on Microsoft's own showcase MCP server. Trajectory matters.
- **Anthropic shipped MCP Tool Search for Claude Code on January 14 2026.** Thariq Shihipar (Member of Technical Staff, Claude Code) wrote: *"Today we're rolling out MCP Tool Search for Claude Code. As MCP has grown to become a more popular protocol and agents have become more capable, we've found that MCP servers may have up to 50+ tools and take up a large amount of context."* Even the MCP creators are routing around their own protocol's verbosity.
- **OpenAI added Codex Skills in December 2025.** Cursor 2.4 added Skills in January 2026. OpenCode and Goose adopted them in late 2025. The convergence is not subtle.
- **Robot Framework Foundation's RoboCon 2026 program** has multiple AI-into-RF sessions (LLM bug-ticket pipelines, AI-driven PR analyzers, n8n nodes, RobotFramework-AI library) but no other RF MCP server is gaining traction. rf-mcp is essentially the *only* RF MCP server. That's both an opportunity (the user owns the niche) and a warning (no peer pressure has emerged to validate the approach).
- **RobotCode is the LSP center of gravity** for RF; `robotframework-lsp` is effectively dormant for RF 7+. Any IDE-side work (the planned `rfx`) should compose with RobotCode, not duplicate it.

---

## 7. Concrete Examples of the Replacement Patterns

### 7.1 A skill replacing `find_keywords` + `get_keyword_info`

```markdown
---
name: robotframework-keyword-finder
description: Find and document Robot Framework keywords by intent, library, or pattern. Use when the user asks "what keyword does X", "is there a keyword for Y", or needs argument signatures for a known keyword.
---

# Robot Framework Keyword Finder

## When to use
- User asks: "what keyword..." / "is there a keyword..." / "how do I X in Robot Framework"
- Generating a new suite and needing argument signatures
- Checking whether a library covers a specific action

## How
1. Run `rfa keyword-search "<query>" --top 5 --json` to get ranked candidates from the local libdoc index.
2. For the most promising candidate, run `rfa keyword-info "<Library>.<Keyword>" --json` for full argument signature + docstring.
3. If the user's project has resource files, also run with `--include-resources` to surface user keywords.

## Scripts
See `scripts/build_index.py` to (re)build the local sqlite-vec index from installed libraries.
See `scripts/keyword_search.py` for the search implementation (executed by `rfa`).
```

### 7.2 A CLI command replacing `check_library_availability`

```python
# rfa/cli.py
@cli.command("check-lib")
@click.argument("name")
def check_lib(name: str) -> int:
    try:
        import importlib
        importlib.import_module(name)
        click.echo(json.dumps({"available": True, "library": name}))
        return 0
    except ImportError as e:
        click.echo(json.dumps({
            "available": False, "library": name,
            "install": f"pip install robotframework-{name.lower()}",
            "error": str(e),
        }))
        return 1
```

Agent invocation (any agent with a Bash tool): `rfa check-lib Browser` — one round trip, ~20 tokens of output, no MCP schema cost.

### 7.3 The 5-tool minimal rf-mcp core

```python
# rf-mcp-core, full tool surface:
@mcp.tool()
def execute_step(suite: str, keyword: str, args: list[str], use_context: bool = True, assign_to: str | None = None) -> StepResult: ...

@mcp.tool()
def execute_flow(suite: str, flow: ControlFlow) -> FlowResult: ...

@mcp.tool()
def get_rf_context(suite: str, sections: list[Literal["variables","libraries","imports","search_order","page_state","application_state"]] = ["variables"]) -> RfContext: ...

@mcp.tool()
def manage_session(suite: str, action: Literal["init","import_library","set_variable","start_test","end_test","reset"], **kwargs) -> SessionResult: ...

@mcp.tool()
def manage_attach(action: Literal["status","stop"]) -> AttachResult: ...
```

That's it. ~5 tools, ~500–1,500 tokens of descriptions total, ~1,500–2,500 LOC of Python (plus the `McpAttach` library and the RF-internals compatibility shim). One person can own it indefinitely.

---

## 8. Migration Path (if Option B is adopted)

| Phase | Deliverable | Risk |
|---|---|---|
| **0. Decide** | Publish an RFC in `manykarim/rf-mcp` discussions; tag the existing 0.31.x as "rf-mcp classic"; communicate to the small but real user base | Low |
| **1. Build `rfa` CLI** | New repo `manykarim/rfa` (or fold into `rf-mcp` as `rfa` console-script) implementing the gap commands over `robotcode`/`robocop` | Low — most logic already exists somewhere |
| **2. Expand skills** | Promote/port 6–8 new skills from rf-mcp's existing logic: `recommend-libraries`, `analyze-scenario`, `locator-guidance` (split per library), `library-availability`, `keyword-finder`, `build-test-suite`, `run-test-suite`, `intent-action` (now a skill that emits keywords for the active library) | Medium — needs honest prose |
| **3. Slim rf-mcp** | Branch `v1.0-core` with the ≤5 tool surface; preserve `McpAttach`; remove Django frontend, Docker-VNC, HTTP/K8s transports (stdio only by default); keep `sqlite-vec`/`model2vec` memory as **fully optional** | Medium — RF-internals shims still hard |
| **4. Cross-agent docs** | One-page "How to use Robot Framework with X" for Claude Code, VS Code Copilot, Cursor, Codex CLI, JetBrains AI, OpenCode, Goose, Cline, Aider — using skills primarily, MCP only when state is needed | Low |
| **5. RoboCon 2026 / EuroSTAR positioning** | Frame the talk as "what we learned shipping the only RF MCP server, and why we now recommend Skills + CLI for most workflows" — credibility-building, ecosystem-leading | Low |

**What to delete with confidence:** Django frontend (`frontend/`), Dockerfile.vnc (VNC image), HTTP transport in default config (keep behind a flag), `tool_profile` machinery (becomes unnecessary at 5 tools), `intent_action` (skill), `analyze_scenario` (skill), `recommend_libraries` (skill), `get_locator_guidance` (skill), `find_keywords`/`get_keyword_info`/`check_library_availability` (CLI), `build_test_suite`/`run_test_suite` (CLI).

---

## 9. Decision Criteria and Benchmarks

If the user runs the experiment for 4–6 weeks, the thresholds that should change the recommendation are:

| Metric | If you see... | Then... |
|---|---|---|
| Tokens used per successful suite scaffold | <30% of what rf-mcp uses today | Option B is working; deprecate the fat tools |
| Cross-agent coverage (% of named agents where workflows work) | >80% | Skills+CLI are succeeding |
| % of user-reported issues that are "MCP server crashed / didn't start" | <10% | Slim core is stable |
| % of issues that are "agent didn't find/use the skill" | >40% | Skill descriptions need work; not an architecture problem |
| Star/install growth on `robotframework-agentskills` vs `rf-mcp` | Skills overtake | Validates direction |
| RF 8 release breakage cost | Lower than RF 7's | The compatibility-shim surface is genuinely smaller |

If after 6 weeks Skills+CLI cover <60% of common workflows or token usage doesn't improve, reconsider Option C (keep rf-mcp simplified).

---

## 10. Caveats and Honest Uncertainties

- **Skills standard is young (Oct 2025 launch).** Adoption is broad but not universal — JetBrains AI Assistant doesn't yet ship native SKILL.md loading (its MCP support is mature, its skills support is not). For JetBrains-AI-only users, an MCP path may remain necessary in the short term.
- **`AGENTS.md` and `SKILL.md` discovery paths still differ per host** and the cross-tool `~/.agents/skills/` convention is emerging rather than finalized. Expect 6–12 months of churn.
- **Skill selection is LLM-driven and opaque.** A skill with a vague description never fires. This is a real authoring tax that MCP tools (with structured JSON schemas) don't pay.
- **The user's existing investment in rf-mcp is significant** (393 commits, workshops, RoboCon/EuroSTAR materials). The recommendation does not invalidate that work — most of the *logic* migrates to skills+CLI; only the *protocol surface* and the *deployment story* shrink.
- **Industry signals are strong but recent.** "MCP is dying" is overstated — the Linux Foundation now stewards MCP, and Anthropic's December 9 2025 donation announcement states: *"In one year, MCP has become one of the fastest-growing and widely-adopted open-source projects in AI: Over 97 million monthly SDK downloads, 10,000 active servers."* MCP isn't going away — but its sweet spot is narrowing to genuinely stateful integrations, which is exactly where rf-mcp's value lives.
- **The `McpAttach` debug bridge is novel and worth preserving** even if everything else around it shrinks. It's the kind of capability that a future RF Foundation initiative could standardise.
- **I did not get a line-by-line LOC count of `src/robotmcp/`** in the time available; estimates of "~15 tools" and "~7K token tool descriptions" are taken from the README's own claims and the verified `pyproject.toml` at v0.31.1, which are conservative.