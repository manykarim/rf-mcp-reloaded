from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class LocalPolicyDefaults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attach_enabled: bool = False
    loopback_only_http: bool = True
    explicit_opt_in_required: bool = True
    persist_session_credentials: bool = False
    context_write_enabled: bool = True
    inspection_snapshot_enabled: bool = True
