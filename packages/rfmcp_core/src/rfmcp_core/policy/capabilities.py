from __future__ import annotations

from enum import StrEnum


class PolicyCapability(StrEnum):
    ATTACH = "attach"
    LOOPBACK_HTTP = "loopback_http"
    SESSION_CREDENTIAL_PERSISTENCE = "session_credential_persistence"
    CONTEXT_WRITE = "context_write"
    INSPECTION_SNAPSHOT = "inspection_snapshot"
