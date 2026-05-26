# Contracts

`rfmcp_core.models` is the authoritative source of shared payload shapes.

`rfmcp_core.contracts` is the public façade used by CLI, MCP, providers, and later bundle renderers.

Current committed schemas:

- error envelope
- hint payload
- hint pack manifest
- skill manifest
- validation result

Regenerate them with:

```bash
uv run python scripts/export_json_schemas.py
uv run python scripts/verify_schema_sync.py
```
