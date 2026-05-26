from __future__ import annotations

from rfmcp_core.models.policy import LocalPolicyDefaults
from rfmcp_core.policy.capabilities import PolicyCapability


def capability_allowed(policy: LocalPolicyDefaults, capability: PolicyCapability) -> bool:
    if capability == PolicyCapability.ATTACH:
        return policy.attach_enabled
    if capability == PolicyCapability.LOOPBACK_HTTP:
        return policy.loopback_only_http
    if capability == PolicyCapability.SESSION_CREDENTIAL_PERSISTENCE:
        return policy.persist_session_credentials
    if capability == PolicyCapability.CONTEXT_WRITE:
        return policy.context_write_enabled
    if capability == PolicyCapability.INSPECTION_SNAPSHOT:
        return policy.inspection_snapshot_enabled
    return False
