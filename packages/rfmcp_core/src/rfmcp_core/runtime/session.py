from __future__ import annotations

from typing import Any
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

from rfmcp_core.contracts import ErrorEnvelope, SessionSummary, SessionStatus
from rfmcp_core.models.payloads import SnapshotKind


@dataclass
class LiveSessionRecord:
    session_id: str
    transport: str
    created_at: datetime
    attach_requested: bool = False
    http_host: str | None = None
    status: SessionStatus = SessionStatus.OPEN
    step_count: int = 0
    # Monotonic version of observable state. Bumped by every store mutation.
    version: int = 0
    last_error: ErrorEnvelope | None = None
    steps: list[str] = field(default_factory=list)
    rf_context: dict[str, Any] = field(default_factory=lambda: {"${CURRENT_TEST}": "Repair Session"})
    libraries: list[str] = field(default_factory=lambda: ["BuiltIn", "Collections"])
    allow_context_write: bool = True
    allowed_snapshot_kinds: tuple[SnapshotKind, ...] = field(default_factory=lambda: tuple(SnapshotKind))
    # Attach-bridge target for an external Robot Framework process (loopback only).
    attach_host: str | None = None
    attach_port: int | None = None
    attach_token: str | None = None
    # Declarative manifest collected via rf_manage_session for final-suite generation.
    # declared_variables -> *** Variables ***; the rest -> *** Settings *** / test-case settings.
    declared_variables: dict[str, Any] = field(default_factory=dict)
    suite_setup: str | None = None
    suite_teardown: str | None = None
    test_setup: str | None = None
    test_teardown: str | None = None
    test_tags: list[str] = field(default_factory=list)
    test_case_setup: str | None = None
    test_case_teardown: str | None = None
    test_case_tags: list[str] = field(default_factory=list)
    # Snapshot-derived signal: True once any DOM capture probed at least one
    # custom element whose shadowRoot was null. Lets agents adopt ARIA-first
    # before the first dead-end dom_selector call (proposals #1 + #6 from the
    # cross-review). The count is the most recent probe's value.
    has_possible_closed_shadow_roots: bool = False
    possible_closed_shadow_root_count: int = 0
    # ARIA-derived ready-to-paste Playwright role locators from the session's
    # most recent aria capture (proposal #2). Consumed by _diagnostic_next_step
    # to bridge a failed flat CSS selector to a matching role-locator when one
    # exists. Kept on the record (not the summary) so the field doesn't bloat
    # every get-summary response.
    latest_aria_selector_hints: list[dict[str, str]] = field(default_factory=list)
    # Runtime-only handle to the live RF execution engine (never serialized).
    engine: Any = field(default=None, repr=False, compare=False)

    def to_summary(self) -> SessionSummary:
        return SessionSummary(
            session_id=self.session_id,
            status=self.status,
            transport=self.transport,
            created_at=self.created_at,
            step_count=self.step_count,
            version=self.version,
            has_possible_closed_shadow_roots=self.has_possible_closed_shadow_roots,
            possible_closed_shadow_root_count=self.possible_closed_shadow_root_count,
            attach_requested=self.attach_requested,
            http_host=self.http_host,
            attach_host=self.attach_host,
            attach_port=self.attach_port,
            attach_token=self.attach_token,
            last_error=self.last_error,
        )

    def bump_version(self) -> int:
        self.version += 1
        return self.version


class LiveSessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, LiveSessionRecord] = {}
        self._lock = Lock()
        # Overridable for tests: callable(session_id, libraries) -> live engine.
        self.engine_factory: Any = None

    def open_session(
        self,
        transport: str,
        *,
        attach_requested: bool = False,
        http_host: str | None = None,
        attach_host: str | None = None,
        attach_port: int | None = None,
    ) -> SessionSummary:
        record = LiveSessionRecord(
            session_id=f"session-{uuid4().hex[:12]}",
            transport=transport,
            created_at=datetime.now(timezone.utc),
            attach_requested=attach_requested,
            http_host=http_host,
            attach_host=attach_host,
            attach_port=attach_port,
            # Per-session ephemeral credential for the attach bridge.
            attach_token=uuid4().hex if attach_requested else None,
        )
        with self._lock:
            self._sessions[record.session_id] = record
        return record.to_summary()

    def get_record(self, session_id: str) -> LiveSessionRecord | None:
        with self._lock:
            return self._sessions.get(session_id)

    def get_summary(self, session_id: str) -> SessionSummary | None:
        record = self.get_record(session_id)
        return record.to_summary() if record else None

    def get_or_create_engine(self, session_id: str) -> Any:
        """Lazily build (not yet start) the live execution engine for a session."""
        with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                return None
            # Never spin up a fresh engine for an already-closed session (avoids a
            # leaked context if close_session races between a status check and here).
            if record.status == SessionStatus.CLOSED:
                return record.engine
            if record.engine is None:
                if self.engine_factory is not None:
                    record.engine = self.engine_factory(session_id, list(record.libraries))
                elif record.attach_requested:
                    from rfmcp_core.runtime.attach import AttachExecutionContext

                    record.engine = AttachExecutionContext(
                        session_id,
                        host=record.attach_host,
                        port=record.attach_port,
                        token=record.attach_token or "",
                    )
                else:
                    from rfmcp_core.runtime.execution import LiveExecutionContext

                    record.engine = LiveExecutionContext(session_id, libraries=list(record.libraries))
            return record.engine

    def close_session(self, session_id: str) -> SessionSummary | None:
        with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                return None
            record.status = SessionStatus.CLOSED
            record.bump_version()
            engine = record.engine
            record.engine = None
            summary = record.to_summary()
        if engine is not None:
            try:
                engine.close()
            except Exception:
                pass
        return summary

    def record_step(self, session_id: str, instruction: str) -> SessionSummary | None:
        with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                return None
            record.step_count += 1
            record.steps.append(instruction)
            record.bump_version()
            return record.to_summary()

    def record_error(
        self,
        session_id: str,
        error: ErrorEnvelope,
        *,
        status: SessionStatus | None = None,
    ) -> SessionSummary | None:
        with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                return None
            record.last_error = error
            if status is not None:
                record.status = status
            record.bump_version()
            return record.to_summary()

    def set_context_value(self, session_id: str, key: str, value: Any) -> SessionSummary | None:
        with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                return None
            record.rf_context[key] = value
            record.bump_version()
            return record.to_summary()

    def record_declared_variable(
        self, session_id: str, key: str, value: Any
    ) -> SessionSummary | None:
        """Track a variable declared for the suite's *** Variables *** section."""
        with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                return None
            record.declared_variables[key] = value
            record.bump_version()
            return record.to_summary()

    def set_session_setting(
        self, session_id: str, scope: str, kind: str, value: str | None
    ) -> SessionSummary | None:
        """Set a setup/teardown declaration. scope: 'suite'|'test'|'test_case'; kind: 'setup'|'teardown'."""
        field_name = {
            ("suite", "setup"): "suite_setup",
            ("suite", "teardown"): "suite_teardown",
            ("test", "setup"): "test_setup",
            ("test", "teardown"): "test_teardown",
            ("test_case", "setup"): "test_case_setup",
            ("test_case", "teardown"): "test_case_teardown",
        }.get((scope, kind))
        if field_name is None:
            return None
        with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                return None
            setattr(record, field_name, value)
            record.bump_version()
            return record.to_summary()

    def set_session_tags(
        self, session_id: str, scope: str, tags: list[str]
    ) -> SessionSummary | None:
        """Set Test Tags (suite-level) or [Tags] (per test case). scope: 'suite'|'test_case'."""
        field_name = {"suite": "test_tags", "test_case": "test_case_tags"}.get(scope)
        if field_name is None:
            return None
        with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                return None
            setattr(record, field_name, list(tags))
            record.bump_version()
            return record.to_summary()

    def record_aria_selector_hints(
        self, session_id: str, hints: list[dict[str, str]]
    ) -> SessionSummary | None:
        """Persist the most recent ARIA-derived role locators on the session.

        Consumed by ``_diagnostic_next_step`` to suggest a role-locator
        alternative when a flat CSS selector fails. Does not bump version —
        these hints are agent-helper state, not observable session content
        (and bumping for every ARIA capture would defeat ``since_version``
        polling). Soft no-op when ``hints`` is empty so a probe that produced
        zero hints doesn't clobber a useful prior list.
        """
        with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                return None
            if hints:
                record.latest_aria_selector_hints = list(hints)
            return record.to_summary()

    def record_shadow_signal(
        self, session_id: str, *, possible_closed_count: int
    ) -> SessionSummary | None:
        """Persist the most recent closed-shadow-root probe count on the session.

        Lets ``_diagnostic_next_step`` and the agent surface the signal without
        re-running the DOM probe on every step. Bumps version so delta-get
        callers see the signal change.
        """
        with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                return None
            count = max(0, int(possible_closed_count))
            if (
                record.possible_closed_shadow_root_count == count
                and record.has_possible_closed_shadow_roots == (count > 0)
            ):
                # No-op; don't bump version for a duplicate observation.
                return record.to_summary()
            record.possible_closed_shadow_root_count = count
            record.has_possible_closed_shadow_roots = count > 0
            record.bump_version()
            return record.to_summary()

    def configure_capabilities(
        self,
        session_id: str,
        *,
        allow_context_write: bool | None = None,
        allowed_snapshot_kinds: tuple[SnapshotKind, ...] | None = None,
    ) -> SessionSummary | None:
        with self._lock:
            record = self._sessions.get(session_id)
            if record is None:
                return None
            mutated = False
            if allow_context_write is not None:
                record.allow_context_write = allow_context_write
                mutated = True
            if allowed_snapshot_kinds is not None:
                record.allowed_snapshot_kinds = allowed_snapshot_kinds
                mutated = True
            if mutated:
                record.bump_version()
            return record.to_summary()
