# Repair Diagnostics

`rfmcp-reloaded` keeps deterministic repair fallback on the CLI so repair can continue even when MCP live-state access is unavailable.

## Commands

- `rfmcp repair-diagnostics <target.robot>` returns structured validation and fallback run-verification findings.
- `rfmcp repair-hints <target.robot>` resolves curated, provider, and inferred guidance with preserved provenance.

Both commands support `--json`.

## Determinism Rules

- Validation fallback stays local and static. It does not pretend to execute the suite.
- Inspection-like fallback payloads must be clearly attributable when they are synthetic or inferred.
- Curated hint packs under `assets/hints/libraries/` are authoritative static truth.
- Provider guidance augments curated packs but does not overwrite authoritative core facts.
