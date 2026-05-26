from __future__ import annotations

from rfmcp_core.contracts import (
    ErrorEnvelope,
    FailureCategory,
    FailureContext,
    HintCandidate,
    HintPayload,
    HintResolutionResult,
    ProvenanceKind,
    ProvenanceRecord,
    Severity,
)
from rfmcp_core.hints.loader import HintPackValidationError, LoadedHintPack, load_hint_packs
from rfmcp_core.hints.merger import apply_normalizations, convert_recovery_candidates, merge_hint_candidates
from rfmcp_core.hints.plugin_manager import ProviderPluginManager


def _matches_pack_entry(pack: LoadedHintPack, entry_index: int, context: FailureContext) -> HintCandidate | None:
    entry = pack.manifest.hints[entry_index]
    message = (context.failure_message or "").casefold()
    libraries = {item.casefold() for item in context.libraries}
    if context.library:
        libraries.add(context.library.casefold())
    keywords = {item.casefold() for item in context.observed_keywords}
    if context.keyword:
        keywords.add(context.keyword.casefold())

    if entry.error_codes and context.error_code not in entry.error_codes:
        return None
    if entry.libraries and not libraries.intersection(item.casefold() for item in entry.libraries):
        return None
    if entry.keywords and not keywords.intersection(item.casefold() for item in entry.keywords):
        return None
    if entry.message_contains and not any(fragment.casefold() in message for fragment in entry.message_contains):
        return None
    if entry.categories and not any(category in context.categories for category in entry.categories):
        return None

    provenance = entry.provenance.model_copy(
        update={
            "source": pack.manifest.pack_id,
            "source_type": entry.provenance.source_type or "curated-pack",
            "source_id": entry.provenance.source_id or pack.manifest.pack_id,
            "source_version": entry.provenance.source_version or pack.manifest.version,
            "source_path": pack.source_path,
            "provider_id": entry.provenance.provider_id or pack.manifest.provider_id,
        }
    )
    return HintCandidate(
        hint_id=entry.hint_id,
        summary=entry.summary,
        recovery=entry.recovery,
        provenance=provenance,
        confidence=entry.confidence,
        tags=list(entry.tags),
    )


def _inferred_candidates(context: FailureContext) -> list[HintCandidate]:
    inferred: list[HintCandidate] = []
    if FailureCategory.KEYWORD in context.categories:
        inferred.append(
            HintCandidate(
                hint_id="inferred-keyword-grounding",
                summary="Ground the failing keyword against available library context before retrying.",
                recovery="Inspect the library imports and compare the failing keyword spelling with the authoritative library keyword list.",
                provenance=ProvenanceRecord(
                    kind=ProvenanceKind.INFERRED,
                    source="repair-diagnostics",
                    source_type="inferred",
                    source_id="repair-diagnostics.keyword-grounding",
                ),
                confidence=0.6,
                tags=["keyword", "fallback"],
            )
        )
    if FailureCategory.ARGUMENT in context.categories:
        inferred.append(
            HintCandidate(
                hint_id="inferred-argument-check",
                summary="Review keyword arguments against the expected call shape.",
                recovery="Compare the failing keyword invocation against the library documentation or provider guidance and adjust the argument count or names.",
                provenance=ProvenanceRecord(
                    kind=ProvenanceKind.INFERRED,
                    source="repair-diagnostics",
                    source_type="inferred",
                    source_id="repair-diagnostics.argument-check",
                ),
                confidence=0.55,
                tags=["argument", "fallback"],
            )
        )
    if not context.live_state_available:
        inferred.append(
            HintCandidate(
                hint_id="inferred-live-state-fallback",
                summary="Continue with deterministic CLI fallback because live-state access is unavailable.",
                recovery="Use repair diagnostics and hint resolution outputs to adjust the artifact before attempting another live repair session.",
                provenance=ProvenanceRecord(
                    kind=ProvenanceKind.INFERRED,
                    source="repair-diagnostics",
                    source_type="inferred",
                    source_id="repair-diagnostics.live-state-fallback",
                ),
                confidence=0.7,
                tags=["fallback", "live-state"],
            )
        )
    return inferred


def resolve_hints(
    context: FailureContext,
    *,
    provider_manager: ProviderPluginManager | None = None,
) -> HintResolutionResult:
    manager = provider_manager or ProviderPluginManager()
    try:
        packs = load_hint_packs()
    except HintPackValidationError as exc:
        error = ErrorEnvelope(
            code="hint-pack-validation-failed",
            message=str(exc),
            severity=Severity.ERROR,
            provenance=ProvenanceRecord(
                kind=ProvenanceKind.OBSERVED,
                source="hint-pack-loader",
                source_type="curated-pack",
                source_id="assets.hints.libraries",
            ),
            retryable=False,
            suggested_next_step="Fix the authoritative hint pack asset before retrying hint resolution.",
            details={"provider_discovery": "not-attempted"},
        )
        return HintResolutionResult(
            ok=False,
            context=context,
            hint=HintPayload(error_code=context.error_code or "diagnostic", candidates=[]),
            recovery_candidates=[],
            error=error,
            packs=[],
            providers=[],
            provider_discovery_attempted=False,
            provider_failures=[],
        )

    providers, provider_failures = manager.load_providers()
    normalizations, normalization_failures = manager.normalize_context(providers, context)
    normalized_context = apply_normalizations(context, normalizations)
    provider_hints, hint_failures = manager.contextual_hints(providers, normalized_context)
    recovery_candidates, recovery_failures = manager.recovery_candidates(providers, normalized_context)

    curated_candidates = [
        candidate
        for pack in packs
        for index in range(len(pack.manifest.hints))
        if (candidate := _matches_pack_entry(pack, index, normalized_context)) is not None
    ]
    merged_payload, conflicts = merge_hint_candidates(
        normalized_context.error_code or "diagnostic",
        curated_candidates + provider_hints + convert_recovery_candidates(recovery_candidates) + _inferred_candidates(normalized_context),
    )
    if not merged_payload.candidates:
        merged_payload, conflicts = merge_hint_candidates(
            normalized_context.error_code or "diagnostic",
            [
                HintCandidate(
                    hint_id="inferred-generic-repair-fallback",
                    summary="Use deterministic validation and targeted library review to continue the repair.",
                    recovery="Run the repair diagnostics command, inspect the structured findings, and adjust the failing suite before retrying execution.",
                    provenance=ProvenanceRecord(
                        kind=ProvenanceKind.INFERRED,
                        source="repair-diagnostics",
                        source_type="inferred",
                        source_id="repair-diagnostics.generic-fallback",
                    ),
                    confidence=0.4,
                    tags=["fallback"],
                )
            ],
        )

    return HintResolutionResult(
        ok=True,
        context=normalized_context,
        hint=merged_payload,
        recovery_candidates=recovery_candidates,
        packs=[pack.manifest.pack_id for pack in packs],
        providers=[provider.provider_id for provider in providers],
        provider_discovery_attempted=True,
        provider_failures=provider_failures + normalization_failures + hint_failures + recovery_failures,
        conflicts=conflicts,
    )


__all__ = ["ProviderPluginManager", "resolve_hints"]
