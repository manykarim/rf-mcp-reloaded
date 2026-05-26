# Story 2.3: Deliver Repair Diagnostics, Validation Fallback, and Provenance-Aware Hinting

Status: done

## Story

As an Automation Engineer,
I want deterministic repair diagnostics, validation fallback, and provenance-aware hinting,
so that I can continue a repair even when live-state tools are unavailable or the failure mode is unclear.

## Acceptance Criteria

1. **Given** a failing suite or resource change must be inspected outside MCP  
   **When** repair diagnostics and validation fallback are implemented  
   **Then** the CLI exposes stable commands with both readable output and `--json` payloads backed by the shared contracts  
   **And** validation and run-verification results identify likely keyword, library, and execution problems in structured form.

2. **Given** curated YAML packs, provider contributions, and inferred recovery suggestions may all contribute guidance  
   **When** the repair hint workflow runs  
   **Then** the system validates and loads file-based hint packs, discovers providers through `pluggy`, merges results deterministically, and emits provenance-rich hint payloads  
   **And** conflicts and deduplication behavior follow the architecture's precedence rules.

3. **Given** a repair scenario includes missing keywords, wrong arguments, ambiguous usage, or unavailable live-state access  
   **When** the operator or skill consumes the diagnostic payload  
   **Then** the operator receives actionable next-step guidance that distinguishes official docs, curated hints, provider guidance, and inferred suggestions  
   **And** fallback validation and hinting remain sufficient to continue without manually parsing raw logs first.

## Tasks / Subtasks

- [x] Add shared diagnostic, failure-context, provider-metadata, and recovery payload contracts plus schema exports. (AC: 1, 2, 3)
- [x] Implement `rfmcp_core.hints` modules for YAML pack loading, provider discovery via `pluggy`, deterministic merge/precedence, and provenance-rich hint resolution. (AC: 2, 3)
- [x] Add curated hint assets and a Browser Library provider implementation through the `rfmcp.providers` entry-point surface. (AC: 2, 3)
- [x] Add stable CLI repair-diagnostics and repair-hints commands with readable and `--json` outputs backed by shared contracts. (AC: 1, 3)
- [x] Add tests covering pack validation, provider ordering/failure isolation, deterministic deduplication, CLI output contracts, and actionable fallback guidance. (AC: 1, 2, 3)

## Dev Notes

- Keep this story on the deterministic CLI side. Do not widen the MCP surface; Story 2.3 exists specifically to keep repair moving when live-state access is unavailable.
- Use the architecture-owned locations and names for the new hint subsystem:
  - `rfmcp_core.hints.hookspecs`
  - `rfmcp_core.hints.plugin_manager`
  - `rfmcp_core.hints.loader`
  - `rfmcp_core.hints.merger`
  - `rfmcp_core.hints.precedence`
- The architecture is explicit that curated YAML packs are authoritative static truth and live under `assets/hints/libraries/`. Providers contribute dynamic enrichment and recovery behavior but must not compete with or mutate authoritative packs.
- Provider discovery must go through Python entry points under the `rfmcp.providers` group. The stable entry-point name is the `provider_id`, and providers must execute in sorted `provider_id` order.
- Pack validation must fail closed. Optional provider failures must stay isolated, produce structured reporting, and must not silently disappear.
- Reuse shared contracts instead of inventing local dict shapes. The new CLI `--json` outputs should be backed by shared models and exported to `assets/schemas/`.
- Preserve canonical provenance semantics. Curated, provider, and inferred guidance must remain visibly distinct, and inferred guidance must never masquerade as curated or provider-authored truth.
- Keep merge behavior deterministic:
  - authoritative core-derived context fields win
  - provider normalization may fill missing context fields but not overwrite authoritative fields
  - conflicting provider normalizations are first-wins by sorted `provider_id`, with conflicts retained in diagnostics
  - hint candidates and recovery candidates are unioned, deduplicated by stable candidate key, then ordered deterministically
- Existing relevant surfaces and files:
  - shared models/contracts: `packages/rfmcp_core/src/rfmcp_core/models/` and `packages/rfmcp_core/src/rfmcp_core/contracts/`
  - current CLI pattern: `packages/rfmcp_cli/src/rfmcp_cli/commands/validate.py`
  - current presenters: `packages/rfmcp_cli/src/rfmcp_cli/presenters/`
  - Browser provider scaffold: `packages/rfmcp_provider_browser/src/rfmcp_provider_browser/`
  - schema export: `scripts/export_json_schemas.py`
  - current repair tests: `tests/test_mcp_live_repair_surface.py`
- Story 2.2 established the pattern that repair outputs must stay attributable and machine-usable. If a fallback or synthetic result is surfaced here, label it explicitly rather than making it indistinguishable from authoritative evidence.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run --group dev python -m unittest tests.test_repair_diagnostics_and_hints -v`
- `uv run --group dev python -m unittest discover -s tests -v`
- `uv run --group dev python scripts/export_json_schemas.py`
- `uv run --group dev python scripts/verify_schema_sync.py`
- `uv build --package rfmcp-core --wheel --out-dir /tmp/rfmcp-core-dist --clear`
- `timeout 300s claude -p --model opus --dangerously-skip-permissions --tools "" < /tmp/story23_claude_prompt.txt`
- `timeout 300s kilo run --auto --dir /home/many/workspace/rfmcp-reloaded -m minimax/MiniMax-M2.7 -f /tmp/story23_review_bundle.txt -- 'Review the attached Story 2.3 bundle...'`

### Completion Notes List

- Added shared repair diagnostics and hint-resolution contracts, including provider metadata, recovery candidates, discovery-attempt state, and diagnostics-carried hint/recovery/provider-failure payloads.
- Implemented deterministic hint-pack loading with fail-closed validation, install-safe bundled asset inclusion via wheel force-include, and provider contract checks for normalization and provenance attribution.
- Wired `repair-diagnostics` and `repair-hints` to expose actionable curated, provider, official-docs, inferred, and recovery guidance in both JSON and human-readable output.
- Added regression coverage for bundled-pack fallback, provider isolation and attribution, fail-closed diagnostics, and diagnostics payload propagation.

### File List

- _bmad-output/implementation-artifacts/2-3-deliver-repair-diagnostics-validation-fallback-and-provenance-aware-hinting.md
- assets/hints/libraries/robotframework.browser.yaml
- packages/rfmcp_cli/src/rfmcp_cli/commands/repair_diagnostics.py
- packages/rfmcp_cli/src/rfmcp_cli/commands/repair_hints.py
- packages/rfmcp_cli/src/rfmcp_cli/presenters/human.py
- packages/rfmcp_core/pyproject.toml
- packages/rfmcp_core/src/rfmcp_core/data/__init__.py
- packages/rfmcp_core/src/rfmcp_core/data/hints/__init__.py
- packages/rfmcp_core/src/rfmcp_core/data/hints/libraries/__init__.py
- packages/rfmcp_core/src/rfmcp_core/hints/__init__.py
- packages/rfmcp_core/src/rfmcp_core/hints/loader.py
- packages/rfmcp_core/src/rfmcp_core/hints/merger.py
- packages/rfmcp_core/src/rfmcp_core/hints/plugin_manager.py
- packages/rfmcp_core/src/rfmcp_core/models/payloads.py
- packages/rfmcp_core/src/rfmcp_core/robot/diagnostics.py
- packages/rfmcp_provider_browser/src/rfmcp_provider_browser/plugin.py
- tests/test_repair_diagnostics_and_hints.py

## Change Log

- 2026-05-25: Created Story 2.3 implementation brief from Epic 2 planning artifacts, architecture hint-extension rules, and current repo structure.
- 2026-05-25: Implemented deterministic repair diagnostics and hinting, hardened provider and pack-failure handling, verified schema sync, and validated install-path packaging for bundled hint assets.
