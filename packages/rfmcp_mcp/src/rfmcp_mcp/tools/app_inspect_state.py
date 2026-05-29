"""Live application-state inspection tool.

Captures approved inspection snapshots from the real loaded library instances
in the active session and persists them to disk under
``${RFMCP_SNAPSHOTS_DIR:-.rfmcp/snapshots}/<session_id>/<seq>_<kind>.<ext>``.

Every response carries a small :class:`SnapshotManifest` (path, byte count,
sha256, format, plus a kind-specific ``summary``). The raw payload is **not**
returned by default — the agent reads the file when it needs it. To include
the payload in-band, pass ``return_inline=True``; the inline content is capped
per kind (DOM 8 KiB, DOM_SELECTOR 16 KiB, ARIA 32 KiB, CONSOLE_LOG 4 KiB) and
``truncated`` is set when the cap fired. Screenshots are never inlined
(returning base64 in tool output wastes tokens; read the file directly).
"""

from __future__ import annotations

from typing import Annotated

from pydantic import Field

from rfmcp_core.contracts import ErrorEnvelope, SnapshotKind
from rfmcp_core.runtime.session import LiveSessionStore
from rfmcp_core.runtime.snapshot import capture_inspection_snapshot
from rfmcp_mcp.tools._errors import unexpected_tool_error


def build_app_inspect_state_tool(store: LiveSessionStore):
    def app_inspect_state(
        session_id: Annotated[
            str,
            Field(description="The id of an open live session (from rf_session action='open')."),
        ],
        snapshot_kind: Annotated[
            SnapshotKind,
            Field(
                description=(
                    "Which approved live-app slice to capture: app_context | dom | dom_selector | "
                    "aria | screenshot | console_log | network_log. Prefer 'aria' for structural "
                    "inspection (Playwright walks Shadow DOM + iframes automatically)."
                ),
            ),
        ],
        selector: Annotated[
            str | None,
            Field(
                default=None,
                description=(
                    "Element selector. Required for snapshot_kind='dom_selector'. Optional for "
                    "'aria' (defaults to 'css=html'). Ignored for other kinds."
                ),
            ),
        ] = None,
        return_inline: Annotated[
            bool,
            Field(
                default=False,
                description=(
                    "When True, include the snapshot payload inline in the response (capped per kind). "
                    "When False (default), only the manifest + summary are returned; read manifest.path "
                    "for the full payload."
                ),
            ),
        ] = False,
        inline_max_bytes: Annotated[
            int | None,
            Field(
                default=None,
                description=(
                    "Override the per-kind inline cap (only meaningful when return_inline=True). "
                    "Defaults: dom=8KiB, dom_selector=16KiB, aria=32KiB, console_log=4KiB."
                ),
            ),
        ] = None,
        summary_only: Annotated[
            bool,
            Field(
                default=False,
                description=(
                    "When True, force-omit inline content even if return_inline is set. Useful for "
                    "lean polling loops that only care about the manifest summary."
                ),
            ),
        ] = False,
        include_shadow_dom: Annotated[
            bool,
            Field(
                default=False,
                description=(
                    "snapshot_kind='dom' only. When True, walk open shadow roots via Evaluate "
                    "JavaScript and emit declarative shadow DOM (<template shadowrootmode='open'>). "
                    "Browser Library required. ARIA already traverses Shadow DOM + iframes natively."
                ),
            ),
        ] = False,
    ) -> dict:
        """Capture an approved inspection snapshot, persist it to disk, return a manifest.

        Returns ``{ok: True, snapshot: InspectionSnapshotResult}`` on success. The result
        always carries ``manifest`` (path / bytes / sha256 / format / kind-specific
        ``summary``). ``content`` is populated only when ``return_inline=True`` (truncated
        to ``inline_max_bytes`` or the per-kind cap); ``truncated`` flags when that fired.

        Returns ``{ok: False, error: ErrorEnvelope}`` when the requested kind is not
        allowlisted for the session, no live source can provide it, or the session is
        not open.

        Per-kind capability matrix:

          kind          library required    selector     extra flags          summary key fields
          app_context   —                   ignored      —                    library_count, variable_count
          dom           Browser | Selenium  ignored      include_shadow_dom*  title, iframe_count, interactive_count,
                                                                              has_declarative_shadow_roots, byte_count
          dom_selector  Browser | Selenium  REQUIRED     —                    selector, byte_count, interactive_count
          aria          Browser             optional     —                    node_count, distinct_roles, top_roles,
                                            (css=html)                        depth, selector
          screenshot    Browser | Selenium  ignored      —                    width, height, byte_count
          console_log   Browser             ignored      —                    entry_count, level_histogram,
                                                                              last_error_excerpt
          network_log   —                   —            —                    v1 stub: record a HAR at New Context
                                                                              creation (record_har_path=...) and read
                                                                              the file directly

        * ``include_shadow_dom=True`` walks open shadow roots via ``Evaluate JavaScript``
          and emits declarative ``<template shadowrootmode="open">`` (Browser only). ``aria``
          already traverses Shadow DOM + iframes via Playwright — usually the cheaper choice.

        Inline caps when ``return_inline=True`` (override via ``inline_max_bytes``):

          app_context    always full inline (compact JSON)
          dom            8 KiB     aria           32 KiB     console_log   4 KiB
          dom_selector  16 KiB     network_log     4 KiB     screenshot    never inline (binary)

        When the cap fires, ``content`` is the truncated UTF-8 prefix, ``truncated=True``,
        and the full payload is always at ``manifest.path``.
        """

        try:
            result = capture_inspection_snapshot(
                store,
                session_id,
                snapshot_kind.value if isinstance(snapshot_kind, SnapshotKind) else snapshot_kind,
                selector=selector,
                return_inline=return_inline,
                inline_max_bytes=inline_max_bytes,
                summary_only=summary_only,
                include_shadow_dom=include_shadow_dom,
            )
            if isinstance(result, ErrorEnvelope):
                return {"ok": False, "error": result.model_dump(mode="json")}
            return {"ok": True, "snapshot": result.model_dump(mode="json")}
        except Exception as exc:
            error = unexpected_tool_error("app_inspect_state", exc)
            return {"ok": False, "error": error.model_dump(mode="json")}

    return app_inspect_state
