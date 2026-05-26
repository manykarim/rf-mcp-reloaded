from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata
from typing import Iterable, Sequence

import pluggy
from pydantic import ValidationError

from rfmcp_core.contracts import (
    ErrorEnvelope,
    FailureContext,
    FailureNormalization,
    HintCandidate,
    ProviderFailure,
    ProviderMetadata,
    ProvenanceKind,
    ProvenanceRecord,
    RecoveryCandidate,
    Severity,
)
from rfmcp_core.hints.hookspecs import HintProviderSpec


PROVIDER_GROUP = "rfmcp.providers"


@dataclass(frozen=True)
class LoadedProvider:
    provider_id: str
    plugin: object
    metadata: ProviderMetadata
    manager: pluggy.PluginManager


def _provider_error(provider_id: str, stage: str, exc: Exception) -> ProviderFailure:
    error_code = (
        "provider-contract-invalid"
        if isinstance(exc, (ImportError, ModuleNotFoundError, ValidationError, ValueError))
        else "provider-execution-failed"
    )
    return ProviderFailure(
        provider_id=provider_id,
        stage=stage,
        error=ErrorEnvelope(
            code=error_code,
            message=f"Provider '{provider_id}' failed during {stage}.",
            severity=Severity.ERROR,
            provenance=ProvenanceRecord(
                kind=ProvenanceKind.OBSERVED,
                source=provider_id,
                source_type="provider",
                source_id=provider_id,
                provider_id=provider_id,
            ),
            retryable=error_code == "provider-execution-failed",
            suggested_next_step="Inspect the provider package and retry after correcting the provider implementation.",
            details={"stage": stage, "error_type": type(exc).__name__, "message": str(exc)},
        ),
    )


def _iter_entry_points(group: str) -> list[metadata.EntryPoint]:
    discovered = metadata.entry_points()
    if hasattr(discovered, "select"):
        return list(discovered.select(group=group))
    return [entry for entry in discovered if entry.group == group]


def _validate_normalization_provider(
    normalization: FailureNormalization,
    *,
    expected_provider_id: str,
) -> FailureNormalization:
    if normalization.provider_id != expected_provider_id:
        raise ValueError(
            f"Normalization provider id '{normalization.provider_id}' does not match registered provider '{expected_provider_id}'."
        )
    return normalization


def _validate_hint_candidate_provider(
    candidate: HintCandidate,
    *,
    expected_provider_id: str,
) -> HintCandidate:
    provenance = candidate.provenance
    if provenance.provider_id is not None and provenance.provider_id != expected_provider_id:
        raise ValueError(
            f"Hint candidate provenance provider id '{provenance.provider_id}' does not match registered provider '{expected_provider_id}'."
        )
    if provenance.kind in {ProvenanceKind.CURATED, ProvenanceKind.INFERRED, ProvenanceKind.OBSERVED}:
        raise ValueError(
            f"Hint candidate provenance kind '{provenance.kind.value}' is not valid for provider-supplied hint candidates."
        )
    return candidate.model_copy(
        update={
            "provenance": provenance.model_copy(
                update={"provider_id": expected_provider_id}
            )
        }
    )


def _validate_recovery_candidate_provider(
    candidate: RecoveryCandidate,
    *,
    expected_provider_id: str,
) -> RecoveryCandidate:
    provenance = candidate.provenance
    if provenance.provider_id is not None and provenance.provider_id != expected_provider_id:
        raise ValueError(
            f"Recovery candidate provenance provider id '{provenance.provider_id}' does not match registered provider '{expected_provider_id}'."
        )
    if provenance.kind in {ProvenanceKind.CURATED, ProvenanceKind.INFERRED, ProvenanceKind.OBSERVED}:
        raise ValueError(
            f"Recovery candidate provenance kind '{provenance.kind.value}' is not valid for provider-supplied recovery candidates."
        )
    return candidate.model_copy(
        update={
            "provenance": provenance.model_copy(
                update={"provider_id": expected_provider_id}
            )
        }
    )


class ProviderPluginManager:
    def __init__(self, entry_points: Sequence[metadata.EntryPoint] | None = None) -> None:
        self._entry_points = list(entry_points) if entry_points is not None else _iter_entry_points(PROVIDER_GROUP)
        self._plugin_manager = pluggy.PluginManager("rfmcp")
        self._plugin_manager.add_hookspecs(HintProviderSpec)

    def load_providers(self) -> tuple[list[LoadedProvider], list[ProviderFailure]]:
        loaded: list[LoadedProvider] = []
        failures: list[ProviderFailure] = []
        for entry_point in sorted(self._entry_points, key=lambda item: item.name):
            provider_id = entry_point.name
            try:
                plugin = entry_point.load()
                provider_manager = pluggy.PluginManager("rfmcp")
                provider_manager.add_hookspecs(HintProviderSpec)
                provider_manager.register(plugin, name=provider_id)
                metadata_payloads = provider_manager.hook.get_provider_metadata()
                provider_metadata = ProviderMetadata.model_validate(metadata_payloads[0])
                if provider_metadata.provider_id != provider_id:
                    raise ValueError(
                        f"Provider metadata id '{provider_metadata.provider_id}' does not match entry-point name '{provider_id}'."
                    )
            except Exception as exc:
                failures.append(_provider_error(provider_id, "load", exc))
                continue
            loaded.append(
                LoadedProvider(
                    provider_id=provider_id,
                    plugin=plugin,
                    metadata=provider_metadata,
                    manager=provider_manager,
                )
            )
        return loaded, failures

    def normalize_context(
        self,
        providers: Iterable[LoadedProvider],
        context: FailureContext,
    ) -> tuple[list[FailureNormalization], list[ProviderFailure]]:
        normalizations: list[FailureNormalization] = []
        failures: list[ProviderFailure] = []
        for provider in providers:
            try:
                payloads = provider.manager.hook.normalize_failure_context(context=context)
                if not payloads or payloads[0] is None:
                    continue
                normalizations.append(
                    _validate_normalization_provider(
                        FailureNormalization.model_validate(payloads[0]),
                        expected_provider_id=provider.provider_id,
                    )
                )
            except Exception as exc:
                failures.append(_provider_error(provider.provider_id, "normalize_failure_context", exc))
        return normalizations, failures

    def contextual_hints(
        self,
        providers: Iterable[LoadedProvider],
        context: FailureContext,
    ) -> tuple[list[HintCandidate], list[ProviderFailure]]:
        candidates: list[HintCandidate] = []
        failures: list[ProviderFailure] = []
        for provider in providers:
            try:
                payloads = provider.manager.hook.contribute_contextual_hints(context=context)
                candidates.extend(
                    _validate_hint_candidate_provider(
                        HintCandidate.model_validate(item),
                        expected_provider_id=provider.provider_id,
                    )
                    for item in (payloads[0] if payloads else [])
                )
            except Exception as exc:
                failures.append(_provider_error(provider.provider_id, "contribute_contextual_hints", exc))
        return candidates, failures

    def recovery_candidates(
        self,
        providers: Iterable[LoadedProvider],
        context: FailureContext,
    ) -> tuple[list[RecoveryCandidate], list[ProviderFailure]]:
        candidates: list[RecoveryCandidate] = []
        failures: list[ProviderFailure] = []
        for provider in providers:
            try:
                payloads = provider.manager.hook.contribute_recovery_candidates(context=context)
                candidates.extend(
                    _validate_recovery_candidate_provider(
                        RecoveryCandidate.model_validate(item),
                        expected_provider_id=provider.provider_id,
                    )
                    for item in (payloads[0] if payloads else [])
                )
            except Exception as exc:
                failures.append(_provider_error(provider.provider_id, "contribute_recovery_candidates", exc))
        return candidates, failures
