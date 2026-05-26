"""Public contract facade for CLI and MCP payloads."""

from rfmcp_core.contracts.diagnostics import (
    DiagnosticFinding,
    FailureCategory,
    FailureContext,
    RepairDiagnosticResult,
)
from rfmcp_core.contracts.errors import ErrorEnvelope, Severity
from rfmcp_core.contracts.hints import (
    FailureNormalization,
    HintCandidate,
    HintConflict,
    HintEntry,
    HintPackManifest,
    HintPayload,
    HintResolutionResult,
    ProviderFailure,
    ProviderMetadata,
    RecoveryCandidate,
)
from rfmcp_core.contracts.provenance import ProvenanceKind, ProvenanceRecord
from rfmcp_core.contracts.repair import RepairSessionSummary, RepairStepResult, SessionStatus
from rfmcp_core.contracts.results import SkillManifest, ValidationIssue, ValidationResult
from rfmcp_core.contracts.runtime import (
    InspectionSnapshotResult,
    RobotContextMutationResult,
    RobotContextView,
    SnapshotKind,
)

__all__ = [
    "DiagnosticFinding",
    "ErrorEnvelope",
    "FailureCategory",
    "FailureContext",
    "FailureNormalization",
    "HintCandidate",
    "HintConflict",
    "HintEntry",
    "HintPackManifest",
    "HintPayload",
    "HintResolutionResult",
    "InspectionSnapshotResult",
    "ProviderFailure",
    "ProviderMetadata",
    "ProvenanceKind",
    "ProvenanceRecord",
    "RecoveryCandidate",
    "RepairDiagnosticResult",
    "RepairSessionSummary",
    "RepairStepResult",
    "RobotContextMutationResult",
    "RobotContextView",
    "Severity",
    "SessionStatus",
    "SnapshotKind",
    "SkillManifest",
    "ValidationIssue",
    "ValidationResult",
]
