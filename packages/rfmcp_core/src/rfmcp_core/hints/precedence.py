from __future__ import annotations

from rfmcp_core.contracts import HintCandidate, ProvenanceKind, ProvenanceRecord


def provenance_rank(record: ProvenanceRecord) -> int:
    if record.kind == ProvenanceKind.OFFICIAL:
        return 0
    if record.kind == ProvenanceKind.CURATED:
        return 1
    if record.kind == ProvenanceKind.PROVIDER:
        return 2
    if record.kind == ProvenanceKind.INFERRED:
        return 3
    return 4


def stable_provenance_key(record: ProvenanceRecord) -> tuple[str, ...]:
    return (
        record.source_type or "",
        record.source_id or "",
        record.provider_id or "",
        record.source_version or "",
        record.source_path or "",
        record.source,
        record.detail or "",
    )


def candidate_sort_key(candidate: HintCandidate) -> tuple[float, int, tuple[str, ...], str]:
    return (
        -candidate.confidence,
        provenance_rank(candidate.provenance),
        stable_provenance_key(candidate.provenance),
        candidate.hint_id,
    )
