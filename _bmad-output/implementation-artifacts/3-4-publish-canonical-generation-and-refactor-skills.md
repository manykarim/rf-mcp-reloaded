# Story 3.4: Publish Canonical Generation and Refactor Skills

Status: done

## Story

As an Automation Engineer,
I want reusable skill workflows for generation and refactoring jobs,
so that supported hosts can follow the same task recipe while still preserving deterministic CLI fallback paths.

## Acceptance Criteria

1. **Given** the generation and refactor CLI workflows exist  
   **When** the skill layer story is implemented  
   **Then** canonical workflow definitions, input contracts, fallback mappings, and asset bindings exist for generation and refactor jobs  
   **And** host-specific rendering consumes those canonical definitions instead of redefining the workflow logic per host.

2. **Given** a supported host cannot load or execute a skill reliably  
   **When** an operator follows the documented fallback  
   **Then** they can complete the same job through deterministic CLI commands  
   **And** the host-specific documentation does not pretend the skill path is mandatory or universally identical.

## Tasks / Subtasks

- [x] Add canonical skill input contracts, manifest definitions, and catalog wiring in `packages/rfmcp_skills` for generation and refactor workflows. (AC: 1, 2)
- [x] Publish deterministic fallback mappings and rendered command templates for the new skill workflows without duplicating CLI logic. (AC: 1, 2)
- [x] Add host-agnostic workflow definitions plus asset bindings that point to `assets/skills/<skill_id>/` and companion documentation under `docs/`. (AC: 1, 2)
- [x] Export the new canonical definitions from package entrypoints so later host renderers can consume them directly. (AC: 1, 2)
- [x] Add tests covering manifest/schema validity, fallback stability, asset binding, package inclusion, and documentation honesty about CLI fallback requirements. (AC: 1, 2)

## Dev Notes

- Story 3.4 is the first real `rfmcp_skills` expansion beyond the Browser repair flagship workflow. Keep the skill layer host-agnostic and deterministic.
- Follow the architecture-owned structural rules:
  - canonical workflow definitions live in `packages/rfmcp_skills/src/rfmcp_skills/definitions/`
  - input contracts and manifest-facing support types belong in `packages/rfmcp_skills/src/rfmcp_skills/`
  - deterministic fallback mappings belong in `packages/rfmcp_skills/src/rfmcp_skills/fallbacks.py`
  - authoritative skill assets bind by `skill_id` under `assets/skills/<skill_id>/`
- Reuse Story 3.2 and Story 3.3 CLI contracts instead of introducing a second execution path.
- Documentation must be explicit about MCP/host limits and the CLI fallback path. Do not imply that hosts execute identical skill machinery.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run --group dev python -m unittest tests.test_generation_and_refactor_skill_definitions -v`
- `python3 -m unittest discover -s tests -v`
- `uv run --group dev python scripts/verify_schema_sync.py`
- `uv build --package rfmcp-skills --wheel --out-dir /tmp/rfmcp-skills-dist --clear`
- `timeout 300s kilo run "Review the attached Story 3.4 implementation bundle..." --auto -m minimax/MiniMax-M2.7 --dir /home/many/workspace/rfmcp-reloaded --file=/tmp/story34_review_bundle.txt`
- `cat /tmp/story34_review_bundle.txt | timeout 300s claude -p --model sonnet --dangerously-skip-permissions --tools '' "Review this Story 3.4 implementation bundle..."`

### Completion Notes List

- Added canonical generation and refactor skill input contracts, fallback mappings, packaged assets, and host-agnostic workflow definitions under `rfmcp_skills`.
- Added a shared skill catalog and ID-based lookup surface so later renderers can consume canonical definitions instead of hardcoding per-host workflow logic.
- Preserved Browser repair compatibility by moving it onto the shared canonical definition type while keeping its MCP tool metadata intact.
- Added packaging and regression tests for manifests, input contracts, fallback rendering, asset/doc honesty, registry coverage, and wheel inclusion of the new skill assets.
- Verified the story with targeted skill-definition tests, full-suite execution, schema-sync checks, wheel builds, a clean MiniMax review pass, and a Claude review attempt that degraded into a tool-runtime issue rather than a code finding.

### File List

- _bmad-output/implementation-artifacts/3-4-publish-canonical-generation-and-refactor-skills.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- assets/skills/runnable-test-generation/README.md
- assets/skills/existing-artifact-refactor/README.md
- docs/runnable-test-generation.md
- docs/existing-artifact-refactor.md
- packages/rfmcp_skills/pyproject.toml
- packages/rfmcp_skills/src/rfmcp_skills/__init__.py
- packages/rfmcp_skills/src/rfmcp_skills/catalog.py
- packages/rfmcp_skills/src/rfmcp_skills/inputs.py
- packages/rfmcp_skills/src/rfmcp_skills/fallbacks.py
- packages/rfmcp_skills/src/rfmcp_skills/definitions/__init__.py
- packages/rfmcp_skills/src/rfmcp_skills/definitions/browser_library_repair.py
- packages/rfmcp_skills/src/rfmcp_skills/definitions/generation.py
- packages/rfmcp_skills/src/rfmcp_skills/definitions/refactor.py
- tests/test_generation_and_refactor_skill_definitions.py

## Change Log

- 2026-05-26: Created Story 3.4 implementation brief from Epic 3 planning artifacts, FR-7/FR-8/FR-9 skill workflow requirements, and the `rfmcp_skills` architecture boundaries.
- 2026-05-26: Implemented canonical generation/refactor skill contracts, definitions, fallback mappings, packaged assets, and registry exports.
- 2026-05-26: Closed Story 3.4 after local verification, MiniMax review pass, and Claude review attempts against the Story 3.4 bundle.
