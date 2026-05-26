# Story 1.5: Add Validation Diagnostics, Local Policy Defaults, and Benchmark Event Foundations

Status: done

## Story

As a maintainer,
I want validation diagnostics, local policy defaults, and structured benchmark events to be explicit,
so that later workflows have trusted evidence, bounded defaults, and reusable diagnostics rather than ad hoc instrumentation.

## Acceptance Criteria

1. **Given** later epics must prove runnable outcomes, tool-call reductions, and benchmark results  
   **When** diagnostics and observability foundations are implemented  
   **Then** shared structured event shapes and logging utilities exist for CLI and MCP code paths  
   **And** benchmark capture remains local-first and does not require a remote telemetry backend.

2. **Given** privileged or attach-style behavior expands later  
   **When** policy defaults and diagnostics are reviewed  
   **Then** local policy assets keep loopback-only and explicit opt-in posture visible  
   **And** emitted diagnostics remain machine-readable and clearly distinguish observed facts from inferred guidance.

## Tasks / Subtasks

- [x] Add shared observability event shapes and local writers. (AC: 1, 2)
- [x] Add local policy assets and loading helpers that keep the default posture explicit. (AC: 2)
- [x] Add CLI and MCP logging helpers backed by shared event shapes. (AC: 1, 2)
- [x] Add tests for policy loading and structured event emission. (AC: 1, 2)
- [x] Verify the event and policy foundation locally without any remote telemetry dependency. (AC: 1, 2)

## Dev Notes

- Reuse the `LocalPolicyDefaults` model introduced in Story 1.3 instead of inventing a second policy shape.
- Keep all benchmark and diagnostic outputs file-first and machine-readable; no remote collectors or hosted telemetry hooks belong in this story.
- Distinguish observed facts from inferred guidance in the event schema itself so later hinting and repair flows can rely on that boundary.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run --group dev python -m unittest discover -s tests -v`
- `python3 scripts/verify_workspace_structure.py`
- `uv run --group dev python scripts/verify_schema_sync.py`

### Completion Notes List

- Added committed local policy defaults under `assets/policy/` and shared loading/enforcement helpers in `rfmcp_core.policy`.
- Added shared JSONL workflow event shapes plus CLI and MCP event emitters for local-first benchmark and diagnostic capture.
- Kept diagnostics machine-readable and provenance-aware by using the shared payload provenance enums in the event model.
- Verified the policy and observability foundation without any remote telemetry dependency.

### File List

- assets/policy/local-defaults.json
- packages/rfmcp_cli/src/rfmcp_cli/logging.py
- packages/rfmcp_core/src/rfmcp_core/models/policy.py
- packages/rfmcp_core/src/rfmcp_core/observability/events.py
- packages/rfmcp_core/src/rfmcp_core/policy/capabilities.py
- packages/rfmcp_core/src/rfmcp_core/policy/enforcement.py
- packages/rfmcp_core/src/rfmcp_core/policy/loader.py
- packages/rfmcp_mcp/src/rfmcp_mcp/logging.py
- tests/test_policy_and_events.py

## Change Log

- 2026-05-25: Created Story 1.5 implementation brief from Epic 1 planning artifacts.
- 2026-05-25: Implemented local policy assets, shared event emission, and benchmark/diagnostic tests; promoted story to review.
- 2026-05-25: Completed Story 1.5 after the local policy/event tests and schema/structure verifiers passed together.
