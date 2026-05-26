# Contract Evolution

## One-Way Rule

Shared payload shapes evolve from the model layer outward:

1. update `rfmcp_core.models`
2. re-export through `rfmcp_core.contracts`
3. regenerate `assets/schemas/`
4. rerun schema-sync verification

Do not redefine payloads independently in CLI, MCP, provider, or bundle packages.

## Contributor Workflow

```bash
uv run python scripts/export_json_schemas.py
uv run python scripts/verify_schema_sync.py
uv run python -m unittest discover -s tests -v
```

If schema sync fails, regenerate the schemas from the model layer rather than editing JSON files manually.
