"""Render the active session's recorded steps and declarations into a canonical RF7 suite.

The session's executed steps (recorded by ``rf_execute_step``) plus any declarative
manifest collected via ``rf_manage_session`` (imports, ``*** Variables ***``,
Suite/Test setup/teardown, tags) are fed into
:func:`rfmcp_core.robot.render_suite_text`, which builds a ``robot.api.parsing.File``
and calls ``File.save`` for canonical RF7 output (modern ``AS`` alias, no obsolete
``${r} =``, proper section ordering, leading-``#`` cells escaped).

By default the rendered text is written to disk and the response carries only a
small manifest (path, bytes, sha256). Pass ``return_inline=True`` to include the
suite text inline (capped at 64 KiB). Pass ``target_path=None`` and
``return_inline=True`` for a write-nothing preview.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Annotated

from pydantic import Field

from rfmcp_core.contracts import (
    ErrorEnvelope,
    ProvenanceKind,
    ProvenanceRecord,
    SessionStatus,
    Severity,
    SnapshotManifest,
)
from rfmcp_core.robot import render_suite_text
from rfmcp_core.runtime.session import LiveSessionStore

_INLINE_CAP_BYTES = 64 * 1024


def _error(
    code: str,
    message: str,
    *,
    retryable: bool,
    next_step: str,
    source: str = "rf_export_suite",
    details: dict | None = None,
) -> dict:
    envelope = ErrorEnvelope(
        code=code,
        message=message,
        severity=Severity.ERROR,
        provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source=source),
        retryable=retryable,
        suggested_next_step=next_step,
        details=details or {},
    )
    return {"ok": False, "error": envelope.model_dump(mode="json")}


def build_export_suite_tool(store: LiveSessionStore):
    def rf_export_suite(
        session_id: Annotated[
            str,
            Field(description="The id of an open or closed live session whose state should be rendered."),
        ],
        target_path: Annotated[
            str | None,
            Field(
                default=None,
                description=(
                    "Destination .robot file path (relative to the working directory). When None, the suite "
                    "is not written to disk — combine with return_inline=True for a preview."
                ),
            ),
        ] = None,
        test_case_name: Annotated[
            str,
            Field(
                default="Live Session Test",
                description="Name of the single test case rendered from the session's recorded steps.",
            ),
        ] = "Live Session Test",
        documentation: Annotated[
            str | None,
            Field(
                default=None,
                description="Optional Documentation line written under *** Settings ***.",
            ),
        ] = None,
        force: Annotated[
            bool,
            Field(
                default=False,
                description="Overwrite target_path if it already exists.",
            ),
        ] = False,
        return_inline: Annotated[
            bool,
            Field(
                default=False,
                description="Include the rendered suite text in the response (capped at 64 KiB).",
            ),
        ] = False,
    ) -> dict:
        """Render the session's recorded steps + declarative manifest into a canonical RF7 suite.

        Returns ``{ok: True, manifest, content?}``. ``manifest`` is a :class:`SnapshotManifest`
        pointing at the written file (when ``target_path`` was set) or a synthetic in-memory
        manifest (path empty, format ``"robot"``) when ``target_path`` was None. ``content``
        carries the suite text when ``return_inline=True``.
        """

        record = store.get_record(session_id)
        if record is None:
            return _error(
                "session-not-found",
                f"Live session '{session_id}' was not found.",
                retryable=True,
                next_step="Open a live session before exporting it.",
                source="session-store",
                details={"session_id": session_id},
            )

        if record.status == SessionStatus.OPEN and not record.steps:
            return _error(
                "no-steps-to-export",
                "The session has not recorded any executed steps yet.",
                retryable=True,
                next_step="Run at least one rf_execute_step before exporting.",
                details={"session_id": session_id},
            )

        if target_path:
            path = Path(target_path)
            if path.suffix != ".robot":
                return _error(
                    "unsupported-extension",
                    "Suite export expects a .robot file target.",
                    retryable=False,
                    next_step="Point target_path at a .robot file or omit it for an inline preview.",
                    details={"target_path": target_path, "suffix": path.suffix},
                )
            if path.exists() and not force:
                return _error(
                    "target-exists",
                    f"Target '{target_path}' already exists.",
                    retryable=True,
                    next_step="Rerun with force=True or choose a new target_path.",
                    details={"target_path": target_path},
                )

        text = render_suite_text(
            test_case_name=test_case_name,
            documentation=documentation,
            body_steps=list(record.steps),
            declared_variables=dict(record.declared_variables),
            suite_setup=record.suite_setup,
            suite_teardown=record.suite_teardown,
            test_setup=record.test_setup,
            test_teardown=record.test_teardown,
            test_tags=list(record.test_tags),
            test_case_setup=record.test_case_setup,
            test_case_teardown=record.test_case_teardown,
            test_case_tags=list(record.test_case_tags),
        )
        encoded = text.encode("utf-8")
        sha = hashlib.sha256(encoded).hexdigest()

        if target_path:
            path = Path(target_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            manifest = SnapshotManifest(
                path=str(path),
                bytes=len(encoded),
                sha256=sha,
                format="robot",
                summary={
                    "test_case_name": test_case_name,
                    "step_count": len(record.steps),
                    "declared_variable_count": len(record.declared_variables),
                    "has_suite_setup": record.suite_setup is not None,
                    "has_suite_teardown": record.suite_teardown is not None,
                    "test_tag_count": len(record.test_tags),
                    "test_case_tag_count": len(record.test_case_tags),
                },
            )
        else:
            manifest = SnapshotManifest(
                path="<in-memory-preview>",
                bytes=len(encoded),
                sha256=sha,
                format="robot",
                summary={
                    "test_case_name": test_case_name,
                    "step_count": len(record.steps),
                    "declared_variable_count": len(record.declared_variables),
                    "in_memory_preview": True,
                },
            )

        content: str | None = None
        truncated = False
        if return_inline:
            if len(encoded) <= _INLINE_CAP_BYTES:
                content = text
            else:
                content = encoded[:_INLINE_CAP_BYTES].decode("utf-8", errors="ignore")
                truncated = True

        return {
            "ok": True,
            "manifest": manifest.model_dump(mode="json"),
            "content": content,
            "truncated": truncated,
        }

    return rf_export_suite
