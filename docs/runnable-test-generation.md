# Runnable Test Generation Workflow

This canonical workflow packages the deterministic generation path added in Epic 3.

Host-specific reality:
- hosts may collect generation intent through their own UI or prompt surface
- hosts should not redefine the workflow logic or claim identical skill execution behavior across products
- if a host cannot load or execute the skill reliably, the operator should use the CLI fallback directly

Authoritative CLI path:
1. `rfmcp ground <keyword-or-library-query> --json`
2. `rfmcp scaffold-suite <target.robot> --library <LibraryName> --json`
3. `rfmcp generate <target.robot> --step '<step>' --assertion '<assertion>' --json`

Expected outcome:
- grounding evidence remains attributable
- scaffold output is deterministic
- generation returns validation, execution proof, and correction-path guidance instead of a host-specific opaque result
