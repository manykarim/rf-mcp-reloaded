# Runnable Test Generation

This skill wraps the deterministic Epic 3 authoring path for new Robot Framework suites.

Host notes:
- hosts may gather intent differently, but they should consume the same canonical workflow definition
- not every host loads skill assets or executes helper steps identically
- the CLI fallback is the authoritative escape hatch when host skill execution is missing or unreliable

Canonical CLI fallback:
- `rfmcp ground <keyword-or-library-query> --json`
- `rfmcp scaffold-suite <target.robot> --library <LibraryName> --json`
- `rfmcp generate <target.robot> --step '<step>' --assertion '<assertion>' --json`
