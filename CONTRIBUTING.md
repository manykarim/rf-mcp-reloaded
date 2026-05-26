# Contributing

## Bootstrap Baseline

The repository is bootstrapped as a `uv` workspace monorepo derived from the selected starter command:

```bash
uv init --package rfmcp-reloaded
```

The persistent workspace baseline follows the architecture rather than a flat single-package app.

Required bootstrap versions:

- Python: `>=3.11,<3.14`
- Recommended `.python-version`: `3.11`
- `uv`: `0.11.16`

## Verification Commands

Run these commands before adding packages or contracts:

```bash
python3 scripts/verify_bootstrap_env.py
python3 scripts/verify_workspace_structure.py
uv lock
python3 -m unittest discover -s tests -v
```

If `scripts/verify_bootstrap_env.py` reports a mismatch, fix that mismatch before continuing. The script prints the exact next step to rerun after correction.

## Current Story Boundary

Story 1.1 establishes the root workspace baseline only. Package scaffolding for `rfmcp_core`, `rfmcp_mcp`, `rfmcp_cli`, `rfmcp_skills`, `rfmcp_bundles`, and provider packages is deferred to Story 1.2.

## Package Ownership Rules

- `rfmcp_core` owns shared contracts, internal models, policy helpers, hint infrastructure, and Robot Framework-facing core logic.
- `rfmcp_mcp` owns live-state MCP transports and allowlisted tool registration only.
- `rfmcp_cli` owns stateless commands, workflow orchestration, installers, and presentation.
- `rfmcp_skills` owns canonical skill definitions and fallback mappings.
- `rfmcp_bundles` owns generated bundle rendering only.
- `rfmcp_provider_*` packages are optional providers. They may contribute plugin and metadata scaffolds, but they must not register MCP tools.

Contributor rule: if you add or move a workspace package, update `docs/project-structure.md` and rerun `python3 scripts/verify_workspace_structure.py` before continuing.
