# MCP Live Repair Boundary

`rfmcp-reloaded` keeps MCP narrow on purpose. MCP exists for live-state repair sessions that need persistent context between steps. Stateless helpers stay in the CLI layer.

## Allowlisted MCP Tools

| Tool | Why It Belongs in MCP |
| --- | --- |
| `rf_open_repair_session` | Creates the live repair context that later steps reuse. |
| `rf_get_repair_session` | Reads the current live repair session state without rebuilding runtime context. |
| `rf_execute_repair_step` | Advances one repair step while preserving live context between steps. |
| `rf_close_repair_session` | Ends the live repair session explicitly so operators can stop the privileged path deliberately. |
| `rf_get_context` | Reads bounded Robot Framework runtime variables and loaded libraries from the active repair session. |
| `rf_set_context` | Updates bounded Robot Framework runtime variables inside the active repair session. |
| `app_inspect_state` | Captures approved, attributable inspection snapshots such as DOM, accessibility, screenshots, last API response, or current app context. |

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
