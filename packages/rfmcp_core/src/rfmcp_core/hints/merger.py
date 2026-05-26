from __future__ import annotations

from collections import defaultdict

from rfmcp_core.contracts import (
    FailureContext,
    FailureNormalization,
    HintCandidate,
    HintConflict,
    HintPayload,
    RecoveryCandidate,
)
from rfmcp_core.hints.precedence import candidate_sort_key, stable_provenance_key


def apply_normalizations(
    context: FailureContext,
    normalizations: list[FailureNormalization],
) -> FailureContext:
    updated = context.model_copy(deep=True)
    conflicts = list(updated.normalization_conflicts)
    events = list(updated.normalization_events)
    library_source = "core-derived" if updated.library else None
    keyword_source = "core-derived" if updated.keyword else None
    for normalization in normalizations:
        if updated.library is None and normalization.library:
            updated.library = normalization.library
            library_source = normalization.provider_id
            events.append(
                f"provider '{normalization.provider_id}' set library to '{normalization.library}'"
            )
        elif updated.library and normalization.library and updated.library != normalization.library:
            conflicts.append(
                f"provider '{normalization.provider_id}' suggested library '{normalization.library}' but '{updated.library}' from '{library_source or 'core-derived'}' was kept"
            )

        if updated.keyword is None and normalization.keyword:
            updated.keyword = normalization.keyword
            keyword_source = normalization.provider_id
            events.append(
                f"provider '{normalization.provider_id}' set keyword to '{normalization.keyword}'"
            )
        elif updated.keyword and normalization.keyword and updated.keyword != normalization.keyword:
            conflicts.append(
                f"provider '{normalization.provider_id}' suggested keyword '{normalization.keyword}' but '{updated.keyword}' from '{keyword_source or 'core-derived'}' was kept"
            )

        for category in normalization.categories:
            if category not in updated.categories:
                updated.categories.append(category)
                events.append(
                    f"provider '{normalization.provider_id}' added category '{category.value}'"
                )

    updated.normalization_conflicts = conflicts
    updated.normalization_events = events
    return updated


def convert_recovery_candidates(candidates: list[RecoveryCandidate]) -> list[HintCandidate]:
    return [
        HintCandidate(
            hint_id=candidate.candidate_id,
            summary=candidate.summary,
            recovery=candidate.action,
            provenance=candidate.provenance,
            confidence=candidate.confidence,
            tags=list(candidate.tags),
        )
        for candidate in candidates
    ]


def merge_hint_candidates(error_code: str, candidates: list[HintCandidate]) -> tuple[HintPayload, list[HintConflict]]:
    grouped: dict[str, list[HintCandidate]] = defaultdict(list)
    for candidate in candidates:
        grouped[candidate.hint_id].append(candidate)

    merged: list[HintCandidate] = []
    conflicts: list[HintConflict] = []
    for hint_id, items in grouped.items():
        ordered_items = sorted(items, key=candidate_sort_key)
        kept = ordered_items[0]
        merged.append(kept)
        for dropped in ordered_items[1:]:
            conflicts.append(
                HintConflict(
                    hint_id=hint_id,
                    kept_source="|".join(stable_provenance_key(kept.provenance)),
                    dropped_source="|".join(stable_provenance_key(dropped.provenance)),
                )
            )

    return HintPayload(error_code=error_code, candidates=sorted(merged, key=candidate_sort_key)), conflicts
