# Story 2.4: Complete the Browser Library Flagship Repair Workflow

Status: done

## Story

As an Automation Engineer,
I want a documented Browser Library repair workflow with deterministic fallbacks,
so that I can repair a real failing test end to end and verify the fix with confidence.

## Acceptance Criteria

1. **Given** the bounded repair session, approved inspection, and repair-diagnostic stories are complete  
   **When** Browser Library repair is implemented as the chosen flagship repair scenario  
   **Then** the project ships the canonical repair skill definition, its host-agnostic assets, and the mapped fallback CLI commands  
   **And** the documentation shows where MCP is used and where deterministic CLI paths take over.

2. **Given** the flagship repair scenario runs in local verification  
   **When** end-to-end tests and benchmark capture execute  
   **Then** the workflow proves a failing test can be diagnosed, repaired, and rerun successfully  
   **And** the project records evidence for runnable success, failure shaping quality, and repair-path determinism.

## Tasks / Subtasks

- [x] Add the canonical Browser repair workflow definition in `packages/rfmcp_skills/` with a stable `skill_id`, input contract usage, and deterministic fallback command mapping. (AC: 1)
- [x] Add authoritative host-agnostic skill assets under `assets/skills/<skill_id>/` that document the Browser repair flow, MCP/CLI boundary, and expected operator inputs. (AC: 1)
- [x] Add the flagship repair workflow documentation that explicitly shows when MCP live-state tools are used and when deterministic CLI repair commands take over. (AC: 1)
- [x] Add a runnable local flagship Browser repair proof path, including end-to-end scenario fixtures plus benchmark/event capture for diagnose, repair, and rerun stages. (AC: 2)
- [x] Add tests covering workflow manifest validity, fallback mapping integrity, end-to-end repair success, benchmark evidence emission, and deterministic fallback behavior. (AC: 1, 2)

## Dev Notes

- This story is the Epic 2 capstone. Reuse the bounded MCP tools from Story 2.1, approved context/inspection surfaces from Story 2.2, and deterministic diagnostics/hints from Story 2.3 rather than inventing a second repair system.
- The architecture-owned structural mapping is explicit:
  - canonical workflow definitions live in `packages/rfmcp_skills/`
  - authoritative host-agnostic assets live in `assets/skills/`
  - deterministic fallback command mapping lives in `packages/rfmcp_skills/fallbacks.py`
  - host-aware rendering belongs to `packages/rfmcp_bundles/`, but Story 2.4 only needs the canonical workflow and proof surfaces, not host-specific renderers yet
- Keep the skill definition schema-backed through the existing `SkillManifest` contract and committed `assets/schemas/skill-manifest.schema.json`. Do not invent a new manifest format.
- The flagship scenario is Browser Library failure repair. Favor a hermetic local scenario that proves the workflow without requiring an external browser stack or networked dependency beyond the current repo baseline.
- AC 1 requires both workflow content and operator clarity:
  - show the ordered repair steps
  - show the live-state MCP tools used during diagnosis/inspection
  - show the fallback CLI commands used when live-state access is unavailable or when rerun/verification returns to deterministic proof
- AC 2 requires proof, not just docs:
  - a failing `.robot` fixture that is diagnosable via the repair commands
  - a repaired artifact or deterministic patch step
  - a rerun/validation result proving runnable success
  - benchmark/evidence capture for diagnose, repair, and rerun stages using the existing JSONL event writer surfaces
- Prefer local JSONL evidence under a deterministic path in the repo or test tempdir; do not add remote telemetry, databases, or background services.
- Existing relevant surfaces and files:
  - CLI commands: `packages/rfmcp_cli/src/rfmcp_cli/commands/repair_diagnostics.py`, `repair_hints.py`, `validate.py`
  - presenters: `packages/rfmcp_cli/src/rfmcp_cli/presenters/`
  - repair diagnostics and hints: `packages/rfmcp_core/src/rfmcp_core/robot/diagnostics.py`, `packages/rfmcp_core/src/rfmcp_core/hints/`
  - observability: `packages/rfmcp_core/src/rfmcp_core/observability/events.py`, `packages/rfmcp_cli/src/rfmcp_cli/logging.py`, `packages/rfmcp_mcp/src/rfmcp_mcp/logging.py`
  - Browser provider: `packages/rfmcp_provider_browser/src/rfmcp_provider_browser/`
  - live-state boundary doc: `docs/mcp-live-repair-boundary.md`
  - deterministic repair doc: `docs/repair-diagnostics.md`
- Keep outputs attributable. If the workflow includes a synthetic repair step or canned fixture patching, mark it clearly so benchmark evidence does not masquerade as live application truth.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv lock`
- `uv run --group dev python -m unittest tests.test_browser_library_flagship_repair_workflow -v`
- `uv run --group dev python -m unittest discover -s tests -v`
- `uv run --group dev python scripts/export_json_schemas.py`
- `uv run --group dev python scripts/verify_schema_sync.py`
- `uv build --package rfmcp-skills --wheel --out-dir /tmp/rfmcp-skills-dist --clear`
- `uv build --package rfmcp-core --wheel --out-dir /tmp/rfmcp-core-dist --clear`
- `claude -p --model opus --dangerously-skip-permissions --tools ""`
- `kilo run --auto -m minimax/MiniMax-M2.7`
- `codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check`

### Completion Notes List

- Added the canonical Browser flagship workflow definition, stable manifest, and shell-safe fallback rendering surface in `rfmcp_skills`.
- Added authoritative host-agnostic skill assets and operator docs that explicitly separate host-level MCP triage from deterministic CLI proof.
- Hardened the workflow to capture baseline failure evidence, emit abort evidence on mismatch, avoid duplicate Browser imports across equivalent Robot syntax, and mark synthetic patching in benchmark metadata.
- Packaged the flagship non-code assets with `rfmcp-skills` and added runtime dependency coverage for `robotframework` so the local proof path is installable from the package.
- Added regression coverage for manifest schema validity, packaged asset inclusion, unsupported scenarios, baseline-mismatch handling, idempotence, and deterministic benchmark output.

### File List

- _bmad-output/implementation-artifacts/2-4-complete-the-browser-library-flagship-repair-workflow.md
- assets/skills/browser-library-flagship-repair/README.md
- docs/browser-library-flagship-repair.md
- packages/rfmcp_core/src/rfmcp_core/robot/diagnostics.py
- packages/rfmcp_skills/pyproject.toml
- packages/rfmcp_skills/src/rfmcp_skills/__init__.py
- packages/rfmcp_skills/src/rfmcp_skills/fallbacks.py
- packages/rfmcp_skills/src/rfmcp_skills/definitions/__init__.py
- packages/rfmcp_skills/src/rfmcp_skills/definitions/browser_library_repair.py
- pyproject.toml
- tests/test_browser_library_flagship_repair_workflow.py
- uv.lock

## Change Log

- 2026-05-26: Created Story 2.4 implementation brief from Epic 2 planning artifacts, Browser repair workflow requirements, and current repo structure.
- 2026-05-26: Implemented and verified the Browser flagship repair workflow, hardened benchmark and packaging behavior from multi-model review findings, and closed Story 2.4.
