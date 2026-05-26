from __future__ import annotations

import pluggy

from rfmcp_core.contracts import (
    FailureContext,
    FailureNormalization,
    HintCandidate,
    ProviderMetadata,
    RecoveryCandidate,
)


hookspec = pluggy.HookspecMarker("rfmcp")
hookimpl = pluggy.HookimplMarker("rfmcp")


class HintProviderSpec:
    @hookspec
    def get_provider_metadata(self) -> ProviderMetadata:
        """Return provider metadata."""

    @hookspec
    def normalize_failure_context(self, context: FailureContext) -> FailureNormalization | None:
        """Fill missing failure-context fields without overwriting authoritative core fields."""

    @hookspec
    def contribute_contextual_hints(self, context: FailureContext) -> list[HintCandidate]:
        """Contribute provider-specific hint candidates for the current failure context."""

    @hookspec
    def contribute_recovery_candidates(self, context: FailureContext) -> list[RecoveryCandidate]:
        """Contribute provider-specific recovery actions for the current failure context."""
