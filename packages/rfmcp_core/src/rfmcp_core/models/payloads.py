from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ProvenanceKind(str, Enum):
    OBSERVED = "observed"
    OFFICIAL = "official"
    CURATED = "curated"
    PROVIDER = "provider"
    INFERRED = "inferred"


class ProvenanceRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: ProvenanceKind
    source: str = Field(min_length=1)
    detail: str | None = None
    source_type: str | None = None
    source_id: str | None = None
    source_version: str | None = None
    source_path: str | None = None
    provider_id: str | None = None


class SessionStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    INTERRUPTED = "interrupted"


class TransportKind(str, Enum):
    """Transport that hosts the MCP session.

    ``stdio`` is the default in-process transport. ``http`` requires a loopback
    host (enforced by the attach-policy validator) and is the only transport
    that admits attach-bridge requests.
    """

    STDIO = "stdio"
    HTTP = "http"


class SessionAction(str, Enum):
    """Lifecycle action for ``rf_session``.

    - ``open``: create a new live session, returning its summary including ``session_id``.
    - ``get``: read the current summary for an existing session.
    - ``close``: terminate an existing session and release its execution context.
    """

    OPEN = "open"
    GET = "get"
    CLOSE = "close"


class ContextAction(str, Enum):
    """Runtime-context action for ``rf_context``.

    - ``get``: read live runtime variables and loaded libraries from the session's namespace.
    - ``set``: write or update one runtime variable inside the live namespace (transient,
      not recorded as a declared ``*** Variables ***`` entry — use ``rf_manage_session``
      with ``action='set_variable'`` for declarative entries).
    """

    GET = "get"
    SET = "set"


class ManageSessionAction(str, Enum):
    """Declarative session-management action for ``rf_manage_session``.

    Import actions are routed through the same stepper as ``rf_execute_step`` and
    are hoisted into the suite's ``*** Settings ***`` section when the final
    artifact is rendered. Variable, setup/teardown, and tag actions record
    declarations destined for ``*** Variables ***``, ``*** Settings ***``, or
    per-test ``[Setup]``/``[Teardown]``/``[Tags]``.
    """

    IMPORT_LIBRARY = "import_library"
    IMPORT_RESOURCE = "import_resource"
    IMPORT_VARIABLES = "import_variables"
    SET_VARIABLE = "set_variable"
    GET_VARIABLE = "get_variable"
    SET_SETUP = "set_setup"
    SET_TEARDOWN = "set_teardown"
    SET_TAGS = "set_tags"


class SettingScope(str, Enum):
    """Scope for ``set_setup`` / ``set_teardown`` actions.

    - ``suite``: ``Suite Setup`` / ``Suite Teardown`` in ``*** Settings ***``.
    - ``test``: ``Test Setup`` / ``Test Teardown`` in ``*** Settings ***`` (applies to all tests).
    - ``test_case``: per-test ``[Setup]`` / ``[Teardown]`` in the test case body.
    """

    SUITE = "suite"
    TEST = "test"
    TEST_CASE = "test_case"


class TagScope(str, Enum):
    """Scope for ``set_tags`` action.

    - ``suite``: ``Test Tags`` in ``*** Settings ***`` (applies to all tests).
    - ``test_case``: per-test ``[Tags]`` in the test case body.
    """

    SUITE = "suite"
    TEST_CASE = "test_case"


class ErrorEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    severity: Severity
    provenance: ProvenanceRecord
    retryable: bool
    suggested_next_step: str = Field(min_length=1)
    details: dict[str, Any] | None = None


class HintCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hint_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    recovery: str = Field(min_length=1)
    provenance: ProvenanceRecord
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    tags: list[str] = Field(default_factory=list)


class HintPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error_code: str = Field(min_length=1)
    candidates: list[HintCandidate] = Field(default_factory=list)


class FailureCategory(str, Enum):
    KEYWORD = "keyword"
    LIBRARY = "library"
    ARGUMENT = "argument"
    EXECUTION = "execution"


class FailureContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target: str = Field(min_length=1)
    error_code: str | None = None
    failure_message: str | None = None
    live_state_available: bool = True
    library: str | None = None
    keyword: str | None = None
    libraries: list[str] = Field(default_factory=list)
    observed_keywords: list[str] = Field(default_factory=list)
    categories: list[FailureCategory] = Field(default_factory=list)
    validation_issue_codes: list[str] = Field(default_factory=list)
    normalization_conflicts: list[str] = Field(default_factory=list)
    normalization_events: list[str] = Field(default_factory=list)


class DiagnosticFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    severity: Severity
    category: FailureCategory
    provenance: ProvenanceRecord
    suggested_next_step: str = Field(min_length=1)
    details: dict[str, Any] | None = None


class ProviderMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    description: str = Field(min_length=1)
    library_names: list[str] = Field(default_factory=list)


class FailureNormalization(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: str = Field(min_length=1)
    library: str | None = None
    keyword: str | None = None
    categories: list[FailureCategory] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class RecoveryCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    action: str = Field(min_length=1)
    provenance: ProvenanceRecord
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    tags: list[str] = Field(default_factory=list)


class ProviderFailure(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: str = Field(min_length=1)
    stage: str = Field(min_length=1)
    error: "ErrorEnvelope"


class HintConflict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hint_id: str = Field(min_length=1)
    kept_source: str = Field(min_length=1)
    dropped_source: str = Field(min_length=1)


class ValidationIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    severity: Severity
    path: str = Field(min_length=1)
    line: int | None = Field(default=None, ge=1)
    column: int | None = Field(default=None, ge=1)


class ValidationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    target: str = Field(min_length=1)
    issues: list[ValidationIssue] = Field(default_factory=list)
    error: ErrorEnvelope | None = None


class GroundingLibrary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    import_name: str = Field(min_length=1)
    provider_id: str | None = None
    description: str | None = None
    importable: bool
    keyword_count: int | None = Field(default=None, ge=0)
    provenance: ProvenanceRecord


class GroundingKeyword(BaseModel):
    model_config = ConfigDict(extra="forbid")

    library_name: str = Field(min_length=1)
    keyword_name: str = Field(min_length=1)
    args_signature: str | None = None
    documentation_excerpt: str | None = None
    provenance: ProvenanceRecord


class GroundingResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    query: str = Field(min_length=1)
    libraries: list[GroundingLibrary] = Field(default_factory=list)
    keywords: list[GroundingKeyword] = Field(default_factory=list)
    preventive_guidance: list[HintCandidate] = Field(default_factory=list)
    provider_failures: list[ProviderFailure] = Field(default_factory=list)
    error: ErrorEnvelope | None = None


class ScaffoldArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    kind: Literal["suite", "resource"]
    content: str = Field(min_length=1)
    validation: ValidationResult


class ScaffoldResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    artifact: ScaffoldArtifact
    preventive_guidance: list[HintCandidate] = Field(default_factory=list)
    created: bool
    overwritten: bool
    error: ErrorEnvelope | None = None

    @model_validator(mode="after")
    def validate_mutation_flags(self) -> "ScaffoldResult":
        if self.created and self.overwritten:
            raise ValueError("Scaffold results cannot be marked as both created and overwritten.")
        return self


class GenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tasks: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    assertions: list[str] = Field(default_factory=list)
    libraries: list[str] = Field(default_factory=list)
    resources: list[str] = Field(default_factory=list)


class GenerationEvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["task", "step", "assertion"]
    requested: str = Field(min_length=1)
    present_in_artifact: bool
    fulfilled: bool
    detail: str | None = None


class ExecutionProof(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    command: list[str] = Field(default_factory=list)
    return_code: int | None = None
    detail: str = Field(min_length=1)
    output_excerpt: str | None = None


class GenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    request: GenerationRequest
    artifact: ScaffoldArtifact
    evidence: list[GenerationEvidenceItem] = Field(default_factory=list)
    execution: ExecutionProof
    preventive_guidance: list[HintCandidate] = Field(default_factory=list)
    diagnostics: RepairDiagnosticResult | None = None
    hint_resolution: HintResolutionResult | None = None
    correction_path: list[str] = Field(default_factory=list)
    error: ErrorEnvelope | None = None


class RefactorRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["refactor", "regenerate"]
    target: str = Field(min_length=1)
    rename_to: str | None = None
    documentation: str | None = None
    replace: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    assertions: list[str] = Field(default_factory=list)


class RefactorChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: Literal["rename", "documentation", "replace-body-line", "append-body-line", "regenerate-body"]
    summary: str = Field(min_length=1)
    before: str | None = None
    after: str | None = None


class RefactorArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1)
    kind: Literal["suite", "resource"]
    original_content: str = Field(min_length=1)
    updated_content: str = Field(min_length=1)
    diff: str = Field(min_length=1)


class RefactorRunVerification(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["passed", "failed", "not-applicable"]
    execution: ExecutionProof | None = None
    detail: str = Field(min_length=1)


class RefactorResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    request: RefactorRequest
    artifact: RefactorArtifact
    changes: list[RefactorChange] = Field(default_factory=list)
    validation: ValidationResult
    run_verification: RefactorRunVerification
    preventive_guidance: list[HintCandidate] = Field(default_factory=list)
    diagnostics: RepairDiagnosticResult | None = None
    hint_resolution: HintResolutionResult | None = None
    manual_follow_up: list[str] = Field(default_factory=list)
    correction_path: list[str] = Field(default_factory=list)
    error: ErrorEnvelope | None = None


class HintResolutionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    context: FailureContext
    hint: HintPayload
    recovery_candidates: list[RecoveryCandidate] = Field(default_factory=list)
    packs: list[str] = Field(default_factory=list)
    providers: list[str] = Field(default_factory=list)
    provider_discovery_attempted: bool = True
    provider_failures: list[ProviderFailure] = Field(default_factory=list)
    conflicts: list[HintConflict] = Field(default_factory=list)
    error: ErrorEnvelope | None = None


class RepairDiagnosticResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    context: FailureContext
    validation: ValidationResult
    verification_mode: Literal["live-state", "static-fallback"] = "static-fallback"
    findings: list[DiagnosticFinding] = Field(default_factory=list)
    hint: HintPayload | None = None
    recovery_candidates: list[RecoveryCandidate] = Field(default_factory=list)
    provider_failures: list[ProviderFailure] = Field(default_factory=list)
    hint_conflicts: list[HintConflict] = Field(default_factory=list)
    error: ErrorEnvelope | None = None


class SkillManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = Field(min_length=1)
    skill_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    fallback_commands: list[str] = Field(default_factory=list)


class SessionSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=1)
    status: SessionStatus
    transport: Literal["stdio", "http"]
    created_at: datetime
    step_count: int = Field(ge=0)
    # Monotonic version bumped on every observable mutation (status / steps / declarations /
    # tags / setups). Pass back to ``rf_session(action='get', since_version=...)`` to skip
    # the full summary when nothing changed.
    version: int = Field(default=0, ge=0)
    attach_requested: bool = False
    http_host: str | None = None
    # Loopback attach bridge target + the per-session ephemeral token the operator
    # configures on their external Robot Framework listener (None unless attaching).
    attach_host: str | None = None
    attach_port: int | None = None
    attach_token: str | None = None
    last_error: ErrorEnvelope | None = None


class StepResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    session: SessionSummary
    step_index: int = Field(ge=1)
    instruction: str = Field(min_length=1)
    detail: str = Field(min_length=1)
    error: ErrorEnvelope | None = None


class SnapshotKind(str, Enum):
    APP_CONTEXT = "app_context"
    DOM = "dom"
    DOM_SELECTOR = "dom_selector"
    ARIA = "aria"
    SCREENSHOT = "screenshot"
    CONSOLE_LOG = "console_log"
    NETWORK_LOG = "network_log"


class RobotContextView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session: SessionSummary
    variables: dict[str, Any] = Field(default_factory=dict)
    libraries: list[str] = Field(default_factory=list)


class RobotContextMutationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session: SessionSummary
    key: str = Field(min_length=1)
    value: Any


class SnapshotManifest(BaseModel):
    """Pointer to the on-disk snapshot artifact plus a small, kind-specific summary.

    The manifest is always returned. ``content`` on the parent result is only populated
    when the caller asks for it explicitly (``return_inline=True``).
    """

    model_config = ConfigDict(extra="forbid")

    path: str = Field(
        min_length=1,
        description="Repo-relative path to the persisted snapshot artifact (e.g. .rfmcp/snapshots/<sid>/0007_dom.html).",
    )
    bytes: int = Field(ge=0, description="Size of the persisted artifact in bytes.")
    sha256: str = Field(min_length=64, max_length=64, description="SHA-256 hex digest of the persisted artifact.")
    format: str = Field(
        min_length=1,
        description="Artifact format: html | html_fragment | yaml | png | json | jsonl | txt.",
    )
    summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Kind-specific stats (e.g. title, element_count, role_histogram, status_histogram).",
    )


class InspectionSnapshotResult(BaseModel):
    """Result of an ``app_inspect_state`` capture.

    ``manifest`` always points at the file on disk. ``content`` is the inline payload
    when the caller passed ``return_inline=True``; it is ``None`` otherwise to keep the
    response token-cheap. ``truncated`` is ``True`` when ``content`` was capped by the
    per-kind or caller-supplied inline limit.
    """

    model_config = ConfigDict(extra="forbid")

    session: SessionSummary
    snapshot_kind: SnapshotKind
    provenance: ProvenanceRecord
    manifest: SnapshotManifest
    content: str | None = None
    truncated: bool = False
