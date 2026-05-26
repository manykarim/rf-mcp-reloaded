# Story 1.4: Ship Deterministic Validate Workflow With Structured Failure Output

Status: done

## Story

As an Automation Engineer,
I want a deterministic validation command with structured failure output,
so that I can verify Robot Framework artifacts early instead of waiting for later workflow layers to exist.

## Acceptance Criteria

1. **Given** the contract and schema pipeline exists  
   **When** the validation story is implemented  
   **Then** the project exposes a minimal `validate` command with human-readable output and a stable `--json` shape backed by the shared contracts  
   **And** the command gives a real operator-visible CLI workflow before the broader repair and generation epics complete.

2. **Given** validation fails on a malformed Robot Framework artifact or baseline mismatch  
   **When** the command returns the result  
   **Then** the output uses the shared structured error envelope with error code, severity, provenance, retryability, and suggested next step  
   **And** the failure does not require raw-log inspection to understand what to do next.

## Tasks / Subtasks

- [x] Add the minimal CLI validate command and entrypoint. (AC: 1)
- [x] Implement deterministic Robot Framework artifact validation backed by the shared contracts. (AC: 1, 2)
- [x] Add human-readable and `--json` presenters for validation results. (AC: 1, 2)
- [x] Cover malformed artifact and baseline mismatch paths with tests. (AC: 2)
- [x] Verify the command through the workspace CLI runner and record outputs. (AC: 1, 2)

## Dev Notes

- Build on Story 1.3 contracts rather than introducing any ad hoc validation payloads.
- The validation path can be a minimal static checker in this story; it does not need full Robot execution yet.
- The baseline mismatch path should reuse the environment-verification logic from Story 1.1 instead of inventing a second version check.

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv lock`
- `uv run --group dev python -m unittest discover -s tests -v`
- `uv run --group dev rfmcp validate README.md --json`
- `uv run --group dev python -m rfmcp_cli.main validate README.md`

### Completion Notes List

- Added a minimal `rfmcp validate` command with both human-readable and JSON presenters.
- Added shared static Robot artifact validation backed by the Story 1.3 contract layer.
- Reused the bootstrap verifier through `rfmcp_core.utils.bootstrap` so baseline mismatch failures are exposed through the shared error envelope.
- Fixed the CLI shape to remain a real `rfmcp validate` subcommand and made the workspace command runnable via the root dev group.

### File List

- packages/rfmcp_cli/pyproject.toml
- packages/rfmcp_cli/src/rfmcp_cli/commands/validate.py
- packages/rfmcp_cli/src/rfmcp_cli/main.py
- packages/rfmcp_cli/src/rfmcp_cli/presenters/human.py
- packages/rfmcp_cli/src/rfmcp_cli/presenters/structured.py
- packages/rfmcp_core/src/rfmcp_core/robot/validation.py
- packages/rfmcp_core/src/rfmcp_core/utils/bootstrap.py
- pyproject.toml
- scripts/verify_bootstrap_env.py
- tests/test_validate_command.py
- tests/test_verify_bootstrap_env.py
- uv.lock

## Change Log

- 2026-05-25: Created Story 1.4 implementation brief from Epic 1 planning artifacts.
- 2026-05-25: Implemented the validate CLI workflow, contract-backed presenters, and bootstrap-backed failure path; promoted story to review.
- 2026-05-25: Completed Story 1.4 after fixing the installed-CLI bootstrap import path and validating the command through `uv run`.
