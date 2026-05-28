# MCP Live Repair Boundary

`rfmcp-reloaded` keeps MCP narrow on purpose. MCP exists for live-state sessions that need persistent context between steps — repair is the flagship use case, but the same session also serves authoring and exploration. Stateless helpers stay in the CLI layer.

## Allowlisted MCP Tools

| Tool | Why It Belongs in MCP |
| --- | --- |
| `rf_open_session` | Creates the live execution context that later steps reuse. |
| `rf_get_session` | Reads the current live session state without rebuilding runtime context. |
| `rf_execute_step` | Runs one real Robot Framework keyword in the session's live execution context, preserving variables, imports, and library state between steps. |
| `rf_close_session` | Ends the live session explicitly so operators can stop the privileged path deliberately. |
| `rf_get_context` | Reads bounded Robot Framework runtime variables and loaded libraries from the active live session. |
| `rf_set_context` | Updates bounded Robot Framework runtime variables inside the active live session. |
| `app_inspect_state` | Captures approved inspection snapshots (DOM, accessibility, screenshots, last API response, app context) from the real loaded library instances, with `OBSERVED` provenance. |
| `rf_manage_session` | Declarative session management: import library/resource/variables (routed through the stepper so they hoist into `*** Settings ***`), set/get `*** Variables ***` entries, and declare Suite/Test setup/teardown and Test Tags for the final suite. |

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
