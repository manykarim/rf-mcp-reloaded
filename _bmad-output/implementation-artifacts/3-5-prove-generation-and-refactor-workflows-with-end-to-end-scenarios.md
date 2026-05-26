# Story 3.5: Prove Generation and Refactor Workflows With End-to-End Scenarios

Status: done

## Story

As a maintainer,
I want end-to-end proof for the generation and refactor workflows,
so that the product demonstrates runnable outcomes instead of relying on architecture narrative alone.

## Acceptance Criteria

1. **Given** the flagship generation and refactor workflows are implemented  
   **When** end-to-end and benchmark scenarios execute  
   **Then** the project measures runnable success, correction burden, and workflow determinism for representative scenarios  
   **And** the resulting evidence is suitable for release comparison and regression detection.

2. **Given** a future change regresses output quality or validation behavior  
   **When** the proof suite runs in CI  
   **Then** the regression is caught through explicit workflow checks rather than only unit-level assertions  
   **And** the benchmark pack remains focused on repair, generation, and refactor reference scenarios.

## Tasks / Subtasks

- [x] Add an Epic 3 benchmark/proof harness for representative generation and refactor scenarios, including deterministic metrics suitable for release comparison. (AC: 1, 2)
- [x] Capture runnable success, correction burden, validation outcome, and determinism evidence for at least one generation scenario and one refactor/regenerate scenario. (AC: 1, 2)
- [x] Persist the proof output in a machine-usable report format plus benchmark events that CI or release tooling can diff later. (AC: 1, 2)
- [x] Add regression tests that execute the proof harness and fail loudly when workflow behavior regresses. (AC: 1, 2)
- [x] Verify the proof suite through local test execution and the external review loop. (AC: 1, 2)

## Dev Notes

- Keep Story 3.5 focused on explicit workflow proof, not on general-purpose telemetry expansion.
- Reuse the existing Epic 3 deterministic workflows and observability primitives instead of building a second implementation path.
- Representative scenarios should stay close to the PRD/addendum benchmark pack:
  - runnable generation for a new suite
  - refactor or regenerate for an existing Robot Framework artifact
- Favor machine-usable JSON evidence plus benchmark JSONL events that can be compared across runs.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run --group dev python -m unittest tests.test_epic3_benchmark_pack -v`
- `python3 -m unittest discover -s tests -v`
- `uv run --group dev python scripts/verify_schema_sync.py`
- `uv build --package rfmcp-cli --wheel --out-dir /tmp/rfmcp-cli-dist --clear`
- `uv run --group dev python scripts/run_epic3_benchmark_pack.py`
- `copilot --model claude-sonnet-4.6 -C /home/many/workspace/rfmcp-reloaded -p "Review Story 3.5 only..." --allow-all --no-ask-user --output-format text --stream off`
- `timeout 300s copilot --model claude-sonnet-4.6 -C /home/many/workspace/rfmcp-reloaded -s -p "Review the current Story 3.5 implementation only..." --allow-all --no-ask-user --output-format text --stream off`
- `kilo run --model minimax/MiniMax-M2.7 --auto --dir /home/many/workspace/rfmcp-reloaded "Review Story 3.5 only..."`
- `timeout 300s kilo run --model minimax/MiniMax-M2.7 --auto --dir /home/many/workspace/rfmcp-reloaded "Review the current Story 3.5 implementation only..."`

### Completion Notes List

- Added an Epic 3 benchmark/proof harness that exercises deterministic generation, refactor, and regenerate reference scenarios and writes a machine-usable JSON report plus JSONL benchmark events.
- Fixed benchmark determinism to ignore temp-path-only differences while still comparing substantive diff, change, and execution payloads across paired runs.
- Tightened summary semantics and proof metrics so deterministic counts, elapsed timing, and correction-burden reporting reflect the actual reference workflow behavior instead of inflated or misleading values.
- Added regression coverage for the benchmark pack, the default proof script, exact benchmark event counts, and the regenerate-scenario burden semantics.
- Verified the story with targeted benchmark tests, full-suite execution, schema-sync checks, CLI wheel build, generated proof-pack output under `dist/benchmarks/`, a Copilot Sonnet 4.6 review that surfaced real metric issues, and MiniMax review passes on the same bundle.

### File List

- _bmad-output/implementation-artifacts/3-5-prove-generation-and-refactor-workflows-with-end-to-end-scenarios.md
- _bmad-output/implementation-artifacts/sprint-status.yaml
- packages/rfmcp_cli/src/rfmcp_cli/benchmarks.py
- scripts/run_epic3_benchmark_pack.py
- tests/test_epic3_benchmark_pack.py

## Change Log

- 2026-05-26: Created Story 3.5 implementation brief from Epic 3 planning artifacts, benchmark-pack expectations, and the existing Epic 3 workflow surface.
- 2026-05-26: Implemented the Epic 3 benchmark/proof harness, default proof-pack script, and regression coverage for machine-usable benchmark output.
- 2026-05-26: Closed Story 3.5 after correcting benchmark determinism/metric semantics, rerunning local verification, and incorporating external review findings.
