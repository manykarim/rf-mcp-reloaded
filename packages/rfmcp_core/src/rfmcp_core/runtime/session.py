from __future__ import annotations

from typing import Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from rfmcp_core.contracts import ErrorEnvelope, RepairSessionSummary, SessionStatus
from rfmcp_core.models.payloads import SnapshotKind


@dataclass
class LiveRepairSessionRecord:
    session_id: str
    transport: str
    created_at: datetime
    attach_requested: bool = False
    http_host: str | None = None
    status: SessionStatus = SessionStatus.OPEN
    step_count: int = 0
    last_error: ErrorEnvelope | None = None
    steps: list[str] = field(default_factory=list)
    rf_context: dict[str, Any] = field(default_factory=lambda: {"${CURRENT_TEST}": "Repair Session"})
    libraries: list[str] = field(default_factory=lambda: ["BuiltIn", "Collections"])
    allow_context_write: bool = True
    allowed_snapshot_kinds: tuple[SnapshotKind, ...] = field(default_factory=lambda: tuple(SnapshotKind))

    def to_summary(self) -> RepairSessionSummary:
        return RepairSessionSummary(
            session_id=self.session_id,
            status=self.status,
            transport=self.transport,
            created_at=self.created_at,
            step_count=self.step_count,
            attach_requested=self.attach_requested,
            http_host=self.http_host,
            last_error=self.last_error,
        )


class LiveRepairSessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, LiveRepairSessionRecord] = {}
        self._lock = Lock()

    def open_session(
        self,
        transport: str,
        *,
        attach_requested: bool = False,
        http_host: str | None = None,
    ) -> RepairSessionSummary:
        record = LiveRepairSessionRecord(
            session_id=f"repair-{uuid4().hex[:12]}",
            transport=transport,
            created_at=datetime.now(timezone.utc),
            attach_requested=attach_requested,
            http_host=http_host,
        )
        with self._lock:
            self._sessions[record.session_id] = record
        return record.to_summary()

    def get_record(self, session_id: str) -> LiveRepairSessionRecord | None:
        with self._lock:
            return self._sessions.get(session_id)

    def get_summary(self, session_id: str) -> RepairSessionSummary | None:
        record = self.get_record(session_id)
        return record.to_summary() if record else None

    def close_session(self, session_id: str) -> RepairSessionSummary | None:
        with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                return None
            record.status = SessionStatus.CLOSED
            return record.to_summary()

    def record_step(self, session_id: str, instruction: str) -> RepairSessionSummary | None:
        with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                return None
            record.step_count += 1
            record.steps.append(instruction)
            return record.to_summary()

    def record_error(
        self,
        session_id: str,
        error: ErrorEnvelope,
        *,
        status: SessionStatus | None = None,
    ) -> RepairSessionSummary | None:
        with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                return None
            record.last_error = error
            if status is not None:
                record.status = status
            return record.to_summary()

    def set_context_value(self, session_id: str, key: str, value: Any) -> RepairSessionSummary | None:
        with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                return None
            record.rf_context[key] = value
            return record.to_summary()

    def configure_capabilities(
        self,
        session_id: str,
        *,
        allow_context_write: bool | None = None,
        allowed_snapshot_kinds: tuple[SnapshotKind, ...] | None = None,
    ) -> RepairSessionSummary | None:
        with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                return None
            if allow_context_write is not None:
                record.allow_context_write = allow_context_write
            if allowed_snapshot_kinds is not None:
                record.allowed_snapshot_kinds = allowed_snapshot_kinds
            return record.to_summary()
