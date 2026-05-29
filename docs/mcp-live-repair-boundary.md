# MCP Live Repair Boundary

`rfmcp-reloaded` keeps MCP narrow on purpose. MCP exists for live-state sessions that need persistent context between steps — repair is the flagship use case, but the same session also serves authoring and exploration. Stateless helpers stay in the CLI layer.

## Allowlisted MCP Tools

| Tool | Action(s) | Why It Belongs in MCP |
| --- | --- | --- |
| `rf_session` | `action`: `open` \| `get` \| `close`; on `get` also accepts `since_version` for a near-empty "unchanged" reply | Lifecycle of the live execution context: creates the namespace that later steps reuse, reads its current state, and tears it down deliberately. `session.version` bumps on every observable mutation; pass it back as `since_version` to skip the full summary when nothing changed (~63% byte savings on polling loops). |
| `rf_export_suite` | — (target_path, test_case_name, documentation, force, return_inline) | Renders the session's recorded steps + declarative manifest (imports/variables/setups/teardowns/tags) into a canonical RF7 `.robot` suite via `robot.api.parsing`. File-first; pass `return_inline=True` for an inline preview (capped at 64 KiB). |
| `rf_execute_step` | `instruction` (single) **OR** `instructions: list[str]` (batched); `stop_on_failure` for the batched case | Runs one real Robot Framework keyword (single mode) or a deterministic sequence (batched mode) in the session's live execution context, preserving variables, imports, and library state between steps. Batched mode returns the session summary once instead of once per step (~56% byte savings on a 7-step setup). On `step-failed`, the error envelope's `suggested_next_step` is concrete — when a Browser/Selenium library is loaded and the failing instruction carries a recognizable locator, it points at a specific `app_inspect_state` call ready to copy. |
| `rf_context` | `action`: `get` \| `set` | Reads or writes bounded Robot Framework runtime variables (and reads loaded libraries) inside the active live session's namespace. Transient mutations only; for declarative `*** Variables ***` entries, see `rf_manage_session`. |
| `rf_manage_session` | `action`: `import_library` \| `import_resource` \| `import_variables` \| `set_variable` \| `get_variable` \| `set_setup` \| `set_teardown` \| `set_tags` | Declarative session management: imports route through the stepper so they hoist into `*** Settings ***`; variable/setup/teardown/tag actions record entries destined for the final suite (`*** Variables ***`, `*** Settings ***`, per-test `[Setup]`/`[Teardown]`/`[Tags]`). `scope` enums tighten setup/teardown (`suite`\|`test`\|`test_case`) and tags (`suite`\|`test_case`). |
| `app_inspect_state` | `snapshot_kind`: `app_context` \| `dom` \| `dom_selector` \| `aria` \| `screenshot` \| `console_log` \| `network_log`; plus `selector`, `return_inline`, `inline_max_bytes`, `summary_only`, `include_shadow_dom` | Captures approved inspection snapshots from the real loaded library instances, with `OBSERVED` provenance. Every snapshot is persisted under `${RFMCP_SNAPSHOTS_DIR:-.rfmcp/snapshots}/<session_id>/<seq>_<kind>.<ext>`; responses always carry a small `manifest` (path / bytes / sha256 / format / kind-specific `summary`) and only include the raw payload when `return_inline=True` (capped per kind). Screenshots are never inlined. `include_shadow_dom=True` walks open shadow roots via `Evaluate JavaScript` and emits declarative `<template shadowrootmode="open">` — proven against [selectorshub.com/xpath-practice-page/](https://selectorshub.com/xpath-practice-page/) and [dbschenker.com book-and-track](https://www.dbschenker.com/global/business/services/book-and-track) (see [`docs/reports/shadow-dom-stress-comparison.md`](reports/shadow-dom-stress-comparison.md)). The `dom` summary also carries a `closed_shadow_probe` field that counts custom elements whose `shadowRoot` is null (a strong "content is hidden behind a closed shadow boundary" signal — flagged 13 of 14 custom elements on dbschenker). `network_log` is a stub in v1 — record a HAR at `New Context` creation and read the file directly. |

Any MCP tool must be justified by a concrete live-state need and remain inside the explicit allowlist.

## Explicit Exclusions

These workflows are stateless and stay outside MCP in v1:

- keyword grounding
- suite scaffolding
- general test generation
- deterministic validation
- broad library-document lookup that does not depend on live runtime context

## Transport Defaults

- `stdio` is allowed by default.
- HTTP transport is allowed only on loopback hosts such as `127.0.0.1` or `localhost`.
- Attach-style behavior is disabled by default and requires an explicit local policy change before it can be requested.

## Decision Rule

Use MCP only when the workflow must preserve live repair state across steps. Use CLI when the workflow can run as a deterministic one-shot command without live runtime state.

## Execution Model

The MCP tools execute against a real Robot Framework runtime, not a simulation:

- By default, an in-process Robot Framework execution context runs one keyword per step and keeps variables, imports, and library instances alive across steps within a session.
- Keyword failures are returned as real pass/fail through the shared error envelope — a step is never reported successful unless the keyword actually passed.
- Attach mode (opt-in, loopback-only, policy-gated, off by default) routes the same tools to an already-running external Robot Framework process for inspecting a live application.

See Epic 5 for the live execution engine and `architecture.md` ("Live Execution Engine for the MCP Core") for the design.
