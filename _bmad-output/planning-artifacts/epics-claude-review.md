# Claude Critical Review of `epics.md`

Date: 2026-05-24
Reviewer: `claude -p --dangerously-skip-permissions --model opus`
Scope: Critical review of the epic/story plan against the PRD and architecture constraints.

## Prompt Focus

- Verify FR1-FR16 coverage.
- Check that epics are organized around user value instead of pure technical layers.
- Check for forward dependencies or oversized stories.
- Check preservation of the narrow MCP boundary, shared contract/schema requirements, provenance-aware hints, portability claims, benchmark proof, and the required starter-template setup in Epic 1 Story 1.
- Check for mismatch between the PRD host set and the bundle/install plan.

## Claude Findings

### Blocking Findings Reported

1. FR4 and FR5 were mis-mapped to Epic 1 even though no user-facing CLI command existed there yet.
2. FR14 was incorrectly claimed by Story 1.1 even though the PRD defines it as operator onboarding to a reference workflow.
3. FR12 did not land in generation/refactor work even though preventive hinting is an authoring concern.
4. Story 1.1 did not name the architecture-selected starter command explicitly.
5. Story 2.2 was oversized because it combined session management, stepwise execution, Robot context access, and inspection snapshots.
6. Story 1.2 did not explicitly deliver the shared error envelope and hint payload schema.
7. Skill manifest schema was implicit even though later skill and bundle stories depend on it.
8. YAML hint pack schema was implicit even though later hint-loading stories depend on it.

### Non-Blocking Improvements Reported

- Story 1.1 could still be split further if implementation context becomes too large.
- Story 2.6 should document its dependencies clearly.
- Story 4.1 may need grouping by renderer family if host packaging diverges.
- CI story preconditions should stay explicit.

## Evaluation and Disposition

### Applied Changes

- Added Story 1.5 to land a minimal user-facing `validate` CLI slice on the shared contracts, making Epic 1 a real FR4/FR5 delivery slice instead of foundation-only work.
- Removed FR14 from Story 1.1 and reassigned FR14 ownership to Epic 4 onboarding and compatibility work.
- Updated Story 1.1 to name the exact architecture-selected starter command: `uv init --package rfmcp-reloaded`.
- Expanded Story 1.2 so it explicitly delivers the shared error envelope, hint payload schema, hint pack schema, and skill-manifest schema.
- Split the former Story 2.2 into:
  - Story 2.2: session and stepwise execution services
  - Story 2.3: Robot context access and approved inspection snapshots
- Added preventive hint coverage to Story 3.1 and Story 3.2 and updated FR12 coverage to span Epic 2 and Epic 3.
- Added a renderer-family complexity guardrail to Story 4.1.

### Deliberate Non-Blocking Follow-Up

- Story 1.1 may still be split during implementation if the workspace scaffold and dependency-baseline work prove too large for one agent context.
- Story 4.4 already carries practical preconditions in its acceptance criteria, but CI dependency sequencing should still be checked when implementation begins.

## Result

The Claude review surfaced substantive planning defects rather than style nits. Those blockers were applied back into [`epics.md`](/home/many/workspace/rfmcp-reloaded/_bmad-output/planning-artifacts/epics.md), and the remaining items are implementation-time sizing concerns rather than coverage or architecture-alignment failures.
