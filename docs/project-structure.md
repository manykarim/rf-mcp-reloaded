# Project Structure

## Workspace Packages

- `packages/rfmcp_core`: shared contracts, model types, policy helpers, hint infrastructure, Robot Framework helpers, and other cross-surface logic.
- `packages/rfmcp_mcp`: live-state MCP transport and allowlisted tool wiring only.
- `packages/rfmcp_cli`: stateless CLI commands, workflows, installers, and presentation.
- `packages/rfmcp_skills`: canonical host-agnostic workflow definitions and fallback mappings.
- `packages/rfmcp_bundles`: generated host bundle and manifest rendering only.

## Provider Packages

Provider packages are optional extensions. They contribute hinting or workflow-adjacent behavior and never own MCP tool registration.

- `packages/rfmcp_provider_browser`
- `packages/rfmcp_provider_selenium`
- `packages/rfmcp_provider_requests`
- `packages/rfmcp_provider_appium`
- `packages/rfmcp_provider_database`

Each provider scaffold keeps three files visible from the start:

- `__init__.py` for package identity
- `metadata.py` for provider-level descriptive data
- `plugin.py` for the extension entrypoint

## Contributor Checks

Run these commands after adding or moving package scaffolds:

```bash
python3 scripts/verify_bootstrap_env.py
python3 scripts/verify_workspace_structure.py
uv lock
python3 -m unittest discover -s tests -v
```
