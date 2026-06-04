# rfmcp-reloaded

`rfmcp-reloaded` is a `uv` workspace monorepo for Robot Framework MCP, CLI workflows, skill bundles, and supporting assets.

## Workspace Bootstrap

This repository no longer uses the placeholder single-file scaffold. The approved bootstrap path is the architecture-selected starter command:

```bash
uv init --package rfmcp-reloaded
```

The committed repository state reflects the resulting workspace direction:

- shared root `pyproject.toml`
- shared `uv.lock`
- root-level bootstrap metadata and checks
- reserved `packages/` and `scripts/` structure for follow-on stories

## Required Baseline

- Python: `>=3.11,<3.14`
- Recommended local pin: `3.11`
- `uv`: `0.11.16`

## Verify Your Environment

```bash
python3 scripts/verify_bootstrap_env.py
python3 scripts/verify_workspace_structure.py
```

The verification script fails explicitly when Python or `uv` do not match the expected bootstrap baseline and tells you what to do next.

## Package Layout

The workspace now reserves these package boundaries for follow-on stories:

- `rfmcp_core`
- `rfmcp_mcp`
- `rfmcp_cli`
- `rfmcp_skills`
- `rfmcp_bundles`
- first provider packages under `rfmcp_provider_*`

See [docs/project-structure.md](docs/project-structure.md) for the contributor-facing package map and scaffold verification commands.

## MCP Boundary

The MCP surface is reserved for bounded live-state repair work. Stateless generation, grounding, scaffolding, and validation stay on the CLI side even if they are convenient to expose elsewhere.

See [docs/mcp-live-repair-boundary.md](docs/mcp-live-repair-boundary.md) for the allowlisted live repair tools, transport defaults, and the written MCP-versus-CLI decision rule.

## Contract Authority

Shared payload contracts live in `packages/rfmcp_core/src/rfmcp_core/models` and are re-exported through `packages/rfmcp_core/src/rfmcp_core/contracts`.

Committed JSON Schemas are generated into `assets/schemas/` only through:

```bash
python3 scripts/export_json_schemas.py
python3 scripts/verify_schema_sync.py
```

## Current Local Mismatch

The current implementation environment is known to be below the required `uv` baseline (`0.9.26` locally versus `0.11.16` required). That mismatch is intentional for Story 1.1 verification: the repository now detects it instead of silently proceeding with an unsupported setup.
