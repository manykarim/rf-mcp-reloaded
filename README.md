# rfmcp-reloaded

**A bounded MCP server + CLI for driving Robot Framework with an AI agent.**

`rfmcp-reloaded` exposes six MCP tools that let an agent open a live Robot Framework session, execute keywords one at a time (preserving variables, imports, and library state across calls), inspect the live application (DOM, ARIA, screenshots, console log) with file-first manifests so big payloads don't blow your context window, and export the finished suite as canonical RF7. The same package ships a `rfmcp` CLI for installation, agent-host setup, diagnostics, and stateless authoring helpers (`validate`, `generate`, `refactor`).

[![Live proof against selectorshub + DB Schenker](https://img.shields.io/badge/live%20proof-passing-brightgreen)](docs/reports/shadow-dom-stress-comparison.md)

## The 6-tool MCP surface

| Tool | What it does |
|------|--------------|
| `rf_session` | Lifecycle (action=`open` \| `get` \| `close`). `get` supports `since_version` for ~63% byte savings on polling loops. |
| `rf_execute_step` | One Robot Framework keyword, or a deterministic batch (`instructions=[...]`). On `step-failed`, the error envelope's `suggested_next_step` carries a concrete `app_inspect_state` call — including a role-locator alternative when ARIA hints suggest one. |
| `rf_context` | Read/write runtime variables (action=`get` \| `set`). |
| `rf_manage_session` | Declarative session manifest: imports, `*** Variables ***`, setups, teardowns, tags. Routes through the stepper so imports hoist into the final suite's Settings. |
| `rf_export_suite` | Renders the session's recorded steps + manifest into a canonical RF7 `.robot` via `robot.api.parsing`. File-first; opt-in inline. |
| `app_inspect_state` | DOM, ARIA, screenshot, console log, app context, network log. File-first manifest by default; opt-in inline (capped per kind). Shadow DOM walked optionally; closed shadow roots flagged. |

Full reference: [`docs/mcp-live-repair-boundary.md`](docs/mcp-live-repair-boundary.md).

## Quickstart (5 commands)

### 1. Install

```bash
# From a checkout
git clone https://github.com/manykarim/rf-mcp-reloaded.git
cd rf-mcp-reloaded
uv sync --group dev --group web
```

A future PyPI release will allow `pip install rfmcp-reloaded` directly.

### 2. Initialize Browser Library (only if you want web automation)

```bash
uv run rfbrowser init
```

### 3. Configure your agent host

Pick your client. `rfmcp init` prints the snippet by default — pass `--write` to merge it into the host's config file with an automatic `.bak`:

```bash
uv run rfmcp init claude-code --write     # ~/.claude.json
uv run rfmcp init claude-desktop --write  # platform-specific Claude Desktop path
uv run rfmcp init cursor --write          # ~/.cursor/mcp.json
uv run rfmcp init kilo --write            # ~/.kilo/mcp.json
uv run rfmcp init codex --write           # ~/.codex/config.toml
```

For project-scoped configuration (claude-code → `./.mcp.json`, cursor → `./.cursor/mcp.json`):

```bash
uv run rfmcp init claude-code --scope project --write
```

### 4. Verify

```bash
uv run rfmcp doctor --client claude-code
```

`doctor` checks Python / uv / Robot Framework / Browser Library + `rfbrowser init` / the local policy file. Pass `--client <name>` to also verify the host has an `rfmcp` entry. Exits non-zero on any failure.

### 5. Run your first agent scenario

Restart your agent host so it picks up the new MCP server. Then ask it:

> Open a live Robot Framework session, navigate to https://selectorshub.com/xpath-practice-page/, capture an ARIA snapshot, and tell me what interactive elements you see.

The agent will call `rf_session(action=open)` → `rf_execute_step(instructions=[...])` for setup → `app_inspect_state(snapshot_kind=aria)`. The ARIA summary surfaces ready-to-paste Playwright role locators directly to the agent.

## CLI reference

```bash
# Server
rfmcp serve                            # stdio (default, used by all agent hosts)
rfmcp serve --transport http --port 8080

# Onboarding
rfmcp init <client> [--write] [--scope user|project]
rfmcp doctor [--client <name>] [--json]

# Skills
rfmcp skills list
rfmcp skills install <skill-id> [--symlink] [--force]
rfmcp skills uninstall <skill-id>
rfmcp skills which <skill-id>

# Stateless authoring helpers (no MCP session required)
rfmcp validate <target.robot>
rfmcp generate <target.robot> --task "..." --step "..."
rfmcp refactor <target.robot> [--rename-to ...] [--replace OLD=NEW]
rfmcp regenerate <target.robot> --step ...
rfmcp repair-diagnostics <target.robot> [--failure-message "..."]
rfmcp repair-hints <target.robot> [--failure-message "..."]
```

## Skills

Three workflow skills ship under `assets/skills/`:

| Skill | What it captures |
|-------|------------------|
| `browser-library-flagship-repair` | The canonical "missing `Library    Browser`" repair workflow. Documents which MCP tools to reach for in which order. |
| `existing-artifact-refactor` | The Epic 3 refactor / regenerate flow. |
| `runnable-test-generation` | The Epic 3 generation flow. |

Install one into Claude Code's skill directory:

```bash
rfmcp skills install browser-library-flagship-repair
```

Use `--symlink` in development so edits to `assets/skills/<id>/` are picked up live. `--force` replaces an existing install.

## Documentation

- [`docs/mcp-live-repair-boundary.md`](docs/mcp-live-repair-boundary.md) — full MCP tool reference with parameters, response shapes, and policy notes.
- [`docs/benchmarks/snapshot-and-delta-token-cost.md`](docs/benchmarks/snapshot-and-delta-token-cost.md) — token-cost benchmark for delta-get, file-first snapshots, batched steps.
- [`docs/reports/shadow-dom-stress-comparison.md`](docs/reports/shadow-dom-stress-comparison.md) — head-to-head live proof against selectorshub and DB Schenker book-and-track, with the cross-review of further-enhancement proposals.
- [`docs/reports/cross-reviews/`](docs/reports/cross-reviews/) — verbatim reviews from claude and kilo CLIs.
- [`docs/workspace-bootstrap.md`](docs/workspace-bootstrap.md) — contributor-facing workspace structure and verification scripts.

## Status

The runtime surface is implemented in 6 user-facing tools (`MAX_USER_FACING_TOOLS = 6`). Suite: 200+ tests green. Live proofs against selectorshub + DB Schenker re-run on every push. Versioning: pre-1.0 — the contract may evolve, but the response envelopes (`ErrorEnvelope`, `StepResult`, `SnapshotManifest`, `SessionSummary`) are stable.

## License

TBD — currently unlicensed.
