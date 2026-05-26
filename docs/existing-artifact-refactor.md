# Existing Artifact Refactor Workflow

This canonical workflow packages the deterministic refactor and regenerate path added in Epic 3.

Host-specific reality:
- hosts may expose refactor jobs in different ways
- hosts should not pretend that the skill path is mandatory or universally identical
- if a host cannot apply or verify edits reliably, the operator should use the CLI fallback commands directly

Authoritative CLI path:
1. `rfmcp refactor <target.robot> --replace 'OLD=NEW' --json`
2. `rfmcp regenerate <target.robot> --step '<step>' --assertion '<assertion>' --json`
3. `rfmcp validate <target.robot> --json`

Expected outcome:
- the canonical workflow returns a structured diff and change list
- suite refactors carry runnable proof or correction-path guidance
- resource refactors surface explicit manual follow-up instead of false runnable claims
