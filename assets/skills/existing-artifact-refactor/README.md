# Existing Artifact Refactor

This skill wraps the deterministic Epic 3 authoring path for existing Robot Framework suites and resources.

Host notes:
- hosts may present refactor or regenerate jobs differently, but they should consume the same canonical workflow definition
- not every host can execute the skill path reliably, especially when local file editing or runnable proof is unavailable
- the CLI fallback remains mandatory documentation, not an optional hidden escape hatch

Canonical CLI fallback:
- `rfmcp refactor <target.robot> --replace 'OLD=NEW' --json`
- `rfmcp regenerate <target.robot> --step '<step>' --assertion '<assertion>' --json`
- `rfmcp validate <target.robot> --json`
