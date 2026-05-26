from __future__ import annotations

import json
from dataclasses import dataclass
from ipaddress import ip_address

from pydantic import ValidationError

from rfmcp_core.contracts import ErrorEnvelope, ProvenanceKind, ProvenanceRecord, Severity
from rfmcp_core.policy.capabilities import PolicyCapability
from rfmcp_core.policy.enforcement import capability_allowed
from rfmcp_core.policy.loader import load_local_policy_defaults


def _is_loopback_host(host: str) -> bool:
    if host == "localhost":
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


@dataclass(frozen=True)
class PolicyGateError(Exception):
    error: ErrorEnvelope

    def __str__(self) -> str:
        return self.error.message


def validate_transport_policy(
    transport: str,
    *,
    host: str | None = None,
    attach_requested: bool = False,
) -> ErrorEnvelope | None:
    try:
        policy = load_local_policy_defaults()
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        return ErrorEnvelope(
            code="policy-load-failed",
            message="Local policy defaults could not be loaded for MCP transport validation.",
            severity=Severity.ERROR,
            provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="local-policy"),
            retryable=False,
            suggested_next_step="Restore a valid local policy file before starting the MCP transport.",
            details={"error": type(exc).__name__},
        )
    allowed_transports = {"stdio", "http"}

    if transport not in allowed_transports:
        return ErrorEnvelope(
            code="unsupported-transport",
            message=f"Transport '{transport}' is not part of the bounded MCP surface.",
            severity=Severity.ERROR,
            provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="transport-policy"),
            retryable=False,
            suggested_next_step="Use the stdio or loopback HTTP transport for the live repair session surface.",
            details={"transport": transport, "allowed": sorted(allowed_transports)},
        )

    if attach_requested and not capability_allowed(policy, PolicyCapability.ATTACH):
        return ErrorEnvelope(
            code="policy-attach-disabled",
            message="Attach-style live repair access is disabled by local policy.",
            severity=Severity.ERROR,
            provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="local-policy"),
            retryable=False,
            suggested_next_step="Enable attach explicitly in local policy before requesting attach-style repair access.",
            details={"transport": transport},
        )

    if transport == "http":
        if not capability_allowed(policy, PolicyCapability.LOOPBACK_HTTP):
            return ErrorEnvelope(
                code="policy-http-disabled",
                message="HTTP transport is disabled by local policy.",
                severity=Severity.ERROR,
                provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="local-policy"),
                retryable=False,
                suggested_next_step="Enable loopback HTTP explicitly in local policy or use stdio instead.",
                details={"transport": transport},
            )
        if host is None or not _is_loopback_host(host):
            return ErrorEnvelope(
                code="policy-http-loopback-only",
                message="HTTP transport must bind to a loopback host.",
                severity=Severity.ERROR,
                provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="transport-policy"),
                retryable=True,
                suggested_next_step="Bind the MCP HTTP transport to 127.0.0.1 or localhost.",
                details={"host": host},
            )

    return None
