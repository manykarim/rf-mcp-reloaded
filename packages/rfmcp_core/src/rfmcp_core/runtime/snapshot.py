"""Approved inspection snapshot capture for the live session surface.

Every snapshot is persisted to disk under
``${RFMCP_SNAPSHOTS_DIR:-.rfmcp/snapshots}/<session_id>/<seq>_<kind>.<ext>``
and the tool response carries a compact :class:`SnapshotManifest` plus a
kind-specific ``summary`` so agents can decide what to do next without spending
tokens on the raw payload. Inline content is opt-in (``return_inline=True``)
and capped per kind to keep transport costs bounded.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import struct
from collections import Counter
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from rfmcp_core.contracts import (
    ErrorEnvelope,
    InspectionSnapshotResult,
    ProvenanceKind,
    ProvenanceRecord,
    Severity,
    SessionStatus,
    SnapshotKind,
    SnapshotManifest,
)
from rfmcp_core.policy.capabilities import PolicyCapability
from rfmcp_core.policy.enforcement import capability_allowed
from rfmcp_core.policy.loader import load_local_policy_defaults
from rfmcp_core.runtime.execution import _json_safe
from rfmcp_core.runtime.session import LiveSessionStore


_DEFAULT_INLINE_CAPS: dict[SnapshotKind, int] = {
    SnapshotKind.APP_CONTEXT: 64 * 1024,   # always inline (compact JSON)
    SnapshotKind.DOM: 8 * 1024,
    SnapshotKind.DOM_SELECTOR: 16 * 1024,
    SnapshotKind.ARIA: 32 * 1024,
    SnapshotKind.SCREENSHOT: 0,            # never inline (binary)
    SnapshotKind.CONSOLE_LOG: 4 * 1024,
    SnapshotKind.NETWORK_LOG: 4 * 1024,
}

_FORMAT_BY_KIND: dict[SnapshotKind, tuple[str, str]] = {
    SnapshotKind.APP_CONTEXT: ("json", "json"),
    SnapshotKind.DOM: ("html", "html"),
    SnapshotKind.DOM_SELECTOR: ("html", "html_fragment"),
    SnapshotKind.ARIA: ("yaml", "yaml"),
    SnapshotKind.SCREENSHOT: ("png", "png"),
    SnapshotKind.CONSOLE_LOG: ("jsonl", "jsonl"),
    SnapshotKind.NETWORK_LOG: ("jsonl", "jsonl"),
}


def _policy_load_error(exc: Exception) -> ErrorEnvelope:
    return ErrorEnvelope(
        code="policy-load-failed",
        message="Local policy defaults could not be loaded for inspection snapshot access.",
        severity=Severity.ERROR,
        provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="local-policy"),
        retryable=False,
        suggested_next_step="Restore a valid local policy file before using inspection snapshot tools.",
        details={"error": type(exc).__name__},
    )


def _session_error(session_id: str, status: str | None = None) -> ErrorEnvelope:
    if status is None:
        return ErrorEnvelope(
            code="session-not-found",
            message=f"Live session '{session_id}' was not found.",
            severity=Severity.ERROR,
            provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="session-store"),
            retryable=True,
            suggested_next_step="Open a live session before requesting an inspection snapshot.",
            details={"session_id": session_id},
        )
    return ErrorEnvelope(
        code="session-not-open",
        message=f"Live session '{session_id}' is not available for inspection snapshots.",
        severity=Severity.ERROR,
        provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="session-store"),
        retryable=True,
        suggested_next_step="Use an open or interrupted live session when requesting inspection snapshots.",
        details={"session_id": session_id, "status": status},
    )


def _observed(source: str) -> ProvenanceRecord:
    return ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source=source)


def _snapshot_unavailable(
    session_id: str,
    snapshot_kind: str,
    *,
    attempted: list[str],
    detail: str | None,
    next_step: str | None = None,
) -> ErrorEnvelope:
    return ErrorEnvelope(
        code="snapshot-unavailable",
        message=f"No live source could provide a '{snapshot_kind}' snapshot for this session.",
        severity=Severity.ERROR,
        provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="live-execution"),
        retryable=True,
        suggested_next_step=next_step
        or "Load a capable library (e.g. Browser or SeleniumLibrary) and drive it before retrying this snapshot kind, or request 'app_context' which is always available.",
        details={
            "session_id": session_id,
            "snapshot_kind": snapshot_kind,
            "attempted_keywords": attempted,
            "error": detail,
        },
    )


# ---------------------------------------------------------------------------
# File-storage helpers
# ---------------------------------------------------------------------------


def _snapshots_root() -> Path:
    """Where snapshot files are persisted. Override via ``RFMCP_SNAPSHOTS_DIR``."""

    return Path(os.environ.get("RFMCP_SNAPSHOTS_DIR", ".rfmcp/snapshots"))


def _session_dir(session_id: str) -> Path:
    directory = _snapshots_root() / session_id
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _next_seq(session_id: str) -> int:
    directory = _session_dir(session_id)
    existing = [p for p in directory.iterdir() if p.is_file() and re.match(r"^\d{4}_", p.name)]
    return len(existing) + 1


def _snapshot_path(session_id: str, kind: SnapshotKind) -> Path:
    ext, _ = _FORMAT_BY_KIND[kind]
    return _session_dir(session_id) / f"{_next_seq(session_id):04d}_{kind.value}.{ext}"


def _persist_text(target: Path, text: str) -> tuple[int, str]:
    target.write_text(text, encoding="utf-8")
    data = text.encode("utf-8")
    return len(data), hashlib.sha256(data).hexdigest()


def _persist_bytes(target: Path, data: bytes) -> tuple[int, str]:
    target.write_bytes(data)
    return len(data), hashlib.sha256(data).hexdigest()


def _build_manifest(path: Path, kind: SnapshotKind, byte_count: int, sha: str, summary: dict[str, Any]) -> SnapshotManifest:
    _, format_label = _FORMAT_BY_KIND[kind]
    return SnapshotManifest(
        path=str(path),
        bytes=byte_count,
        sha256=sha,
        format=format_label,
        summary=summary,
    )


def _maybe_inline_text(
    text: str,
    kind: SnapshotKind,
    *,
    return_inline: bool,
    inline_max_bytes: int | None,
    summary_only: bool,
) -> tuple[str | None, bool]:
    if summary_only or not return_inline:
        return None, False
    cap = inline_max_bytes if inline_max_bytes is not None else _DEFAULT_INLINE_CAPS.get(kind, 0)
    if cap <= 0:
        return None, False
    encoded = text.encode("utf-8")
    if len(encoded) <= cap:
        return text, False
    return encoded[:cap].decode("utf-8", errors="ignore"), True


# ---------------------------------------------------------------------------
# Per-kind capture functions
# ---------------------------------------------------------------------------


def _capture_app_context(engine: Any, session_id: str, kind: SnapshotKind) -> tuple[Path, int, str, dict[str, Any], str]:
    libraries = engine.imported_libraries()
    variable_names = sorted(engine.get_variables().keys())
    body = {
        "session_id": session_id,
        "loaded_libraries": libraries,
        "variables": variable_names,
    }
    text = json.dumps(body, indent=2, sort_keys=True) + "\n"
    path = _snapshot_path(session_id, kind)
    byte_count, sha = _persist_text(path, text)
    summary = {
        "library_count": len(libraries),
        "variable_count": len(variable_names),
    }
    return path, byte_count, sha, summary, text


_DOM_TITLE_RE = re.compile(r"<title[^>]*>([^<]*)</title>", re.IGNORECASE)
_DOM_IFRAME_RE = re.compile(r"<iframe\b", re.IGNORECASE)
_DOM_INTERACTIVE_RE = re.compile(r"<(a|button|input|select|textarea|form)\b", re.IGNORECASE)
_DOM_SHADOW_RE = re.compile(r"shadowroot(?:mode)?\s*=", re.IGNORECASE)


def _dom_summary(html: str) -> dict[str, Any]:
    title_match = _DOM_TITLE_RE.search(html)
    return {
        "title": (title_match.group(1).strip() if title_match else None),
        "iframe_count": len(_DOM_IFRAME_RE.findall(html)),
        "interactive_count": len(_DOM_INTERACTIVE_RE.findall(html)),
        "has_declarative_shadow_roots": bool(_DOM_SHADOW_RE.search(html)),
        "byte_count": len(html.encode("utf-8")),
    }


# Single-line walker using single-quoted JS strings throughout (no `\"` escapes
# that the RF runner can mangle) and no `${...}` template literals (RF would
# treat them as Robot variable references). Returns the page's HTML with open
# shadow roots inlined as declarative `<template shadowrootmode="open">`.
_SHADOW_DOM_WALKER_JS = (
    "(function(){"
    "function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}"
    "function ea(s){return String(s).replace(/\"/g,'&quot;');}"
    "function serialize(root){"
    "var out='';var nodes=root.childNodes;"
    "for(var i=0;i<nodes.length;i++){"
    "var node=nodes[i];"
    "if(node.nodeType===Node.TEXT_NODE){out+=esc(node.nodeValue||'');continue;}"
    "if(node.nodeType===Node.COMMENT_NODE){out+='<!--'+(node.nodeValue||'')+'-->';continue;}"
    "if(node.nodeType!==Node.ELEMENT_NODE){continue;}"
    "var tag=node.localName;var attrs='';var al=node.attributes||[];"
    "for(var j=0;j<al.length;j++){var a=al[j];attrs+=' '+a.name+'=\"'+ea(a.value||'')+'\"';}"
    "out+='<'+tag+attrs+'>';"
    "if(node.shadowRoot){out+='<template shadowrootmode=\"open\">';out+=serialize(node.shadowRoot);out+='</template>';}"
    "out+=serialize(node);out+='</'+tag+'>';"
    "}return out;}"
    "var dt=document.doctype?('<!DOCTYPE '+document.doctype.name+'>'):'';"
    "return dt+serialize(document.documentElement.parentNode);"
    "})()"
)


def _capture_dom(
    engine: Any,
    session_id: str,
    kind: SnapshotKind,
    *,
    include_shadow_dom: bool = False,
) -> tuple[Path, int, str, dict[str, Any], str, str]:
    if include_shadow_dom:
        # Walk shadow roots via Evaluate JavaScript (Browser Library).
        # First arg is the selector; empty means "evaluate against the page".
        try:
            value = engine.query("Evaluate JavaScript", ["", _SHADOW_DOM_WALKER_JS])
        except Exception as exc:
            raise _SnapshotCaptureError(
                attempted=["Evaluate JavaScript"], detail=str(exc) or exc.__class__.__name__
            )
        html = str(value if value is not None else "")
        path = _snapshot_path(session_id, kind)
        byte_count, sha = _persist_text(path, html)
        summary = _dom_summary(html)
        summary["shadow_dom_walked"] = True
        return path, byte_count, sha, summary, html, "Evaluate JavaScript (shadow walker)"

    candidates = ("Get Page Source", "Get Source")
    last_error: str | None = None
    for keyword in candidates:
        try:
            value = engine.query(keyword)
        except Exception as exc:
            last_error = str(exc) or exc.__class__.__name__
            continue
        html = str(value if value is not None else "")
        path = _snapshot_path(session_id, kind)
        byte_count, sha = _persist_text(path, html)
        return path, byte_count, sha, _dom_summary(html), html, keyword
    raise _SnapshotCaptureError(attempted=list(candidates), detail=last_error)


def _capture_dom_selector(engine: Any, session_id: str, kind: SnapshotKind, selector: str) -> tuple[Path, int, str, dict[str, Any], str, str]:
    candidates = (
        ("Get Property", [selector, "outerHTML"]),
        ("Get Element Attribute", [selector, "outerHTML"]),
    )
    last_error: str | None = None
    for keyword, args in candidates:
        try:
            value = engine.query(keyword, args)
        except Exception as exc:
            last_error = str(exc) or exc.__class__.__name__
            continue
        fragment = str(value if value is not None else "")
        path = _snapshot_path(session_id, kind)
        byte_count, sha = _persist_text(path, fragment)
        summary = {
            "selector": selector,
            "byte_count": len(fragment.encode("utf-8")),
            "interactive_count": len(_DOM_INTERACTIVE_RE.findall(fragment)),
            "iframe_count": len(_DOM_IFRAME_RE.findall(fragment)),
        }
        return path, byte_count, sha, summary, fragment, keyword
    raise _SnapshotCaptureError(attempted=[k for k, _ in candidates], detail=last_error)


_ARIA_ROLE_RE = re.compile(r"^\s*-\s*([\w-]+)\b", re.MULTILINE)


def _aria_summary(yaml_text: str) -> dict[str, Any]:
    roles = _ARIA_ROLE_RE.findall(yaml_text)
    histogram = Counter(roles)
    top_roles = dict(histogram.most_common(10))
    max_depth = 0
    for line in yaml_text.splitlines():
        stripped = line.lstrip(" ")
        if not stripped:
            continue
        depth = (len(line) - len(stripped)) // 2
        if depth > max_depth:
            max_depth = depth
    return {
        "node_count": sum(histogram.values()),
        "distinct_roles": len(histogram),
        "top_roles": top_roles,
        "depth": max_depth,
        "byte_count": len(yaml_text.encode("utf-8")),
    }


def _capture_aria(engine: Any, session_id: str, kind: SnapshotKind, selector: str | None) -> tuple[Path, int, str, dict[str, Any], str, str]:
    target_selector = selector or "css=html"
    candidates = (
        ("Get Aria Snapshot", [target_selector, "yaml"]),
    )
    last_error: str | None = None
    for keyword, args in candidates:
        try:
            value = engine.query(keyword, args)
        except Exception as exc:
            last_error = str(exc) or exc.__class__.__name__
            continue
        yaml_text = str(value if value is not None else "")
        path = _snapshot_path(session_id, kind)
        byte_count, sha = _persist_text(path, yaml_text)
        summary = _aria_summary(yaml_text)
        summary["selector"] = target_selector
        return path, byte_count, sha, summary, yaml_text, keyword
    raise _SnapshotCaptureError(attempted=[k for k, _ in candidates], detail=last_error)


def _png_dimensions(data: bytes) -> tuple[int | None, int | None]:
    """Read width/height from a PNG IHDR chunk without depending on Pillow."""

    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None, None
    try:
        width, height = struct.unpack(">II", data[16:24])
        return width, height
    except struct.error:
        return None, None


def _capture_screenshot(engine: Any, session_id: str, kind: SnapshotKind) -> tuple[Path, int, str, dict[str, Any], None, str]:
    target = _snapshot_path(session_id, kind)
    candidates = (
        ("Take Screenshot", [str(target)]),
        ("Capture Page Screenshot", [str(target)]),
    )
    last_error: str | None = None
    for keyword, args in candidates:
        try:
            engine.query(keyword, args)
        except Exception as exc:
            last_error = str(exc) or exc.__class__.__name__
            continue
        # Libraries may write to a default location; normalize to our target.
        if not target.exists():
            written = _locate_recent_png(_session_dir(session_id))
            if written is not None and written != target:
                shutil.move(str(written), str(target))
        if not target.exists():
            last_error = "library did not produce a screenshot file at the expected path"
            continue
        data = target.read_bytes()
        width, height = _png_dimensions(data)
        sha = hashlib.sha256(data).hexdigest()
        summary = {
            "width": width,
            "height": height,
            "byte_count": len(data),
        }
        return target, len(data), sha, summary, None, keyword
    raise _SnapshotCaptureError(attempted=[k for k, _ in candidates], detail=last_error)


def _locate_recent_png(directory: Path) -> Path | None:
    candidates = [p for p in directory.glob("*.png") if p.is_file()]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def _capture_console_log(engine: Any, session_id: str, kind: SnapshotKind) -> tuple[Path, int, str, dict[str, Any], str, str]:
    candidates = (("Get Console Log", None),)
    last_error: str | None = None
    for keyword, args in candidates:
        try:
            value = engine.query(keyword, args)
        except Exception as exc:
            last_error = str(exc) or exc.__class__.__name__
            continue
        entries = list(value) if isinstance(value, (list, tuple)) else [value] if value is not None else []
        lines = [json.dumps(_json_safe(entry), sort_keys=True) for entry in entries]
        text = "\n".join(lines) + ("\n" if lines else "")
        path = _snapshot_path(session_id, kind)
        byte_count, sha = _persist_text(path, text)
        levels = Counter(
            str(entry.get("type") if isinstance(entry, dict) else "unknown").lower()
            for entry in entries
        )
        last_error_entry = next(
            (entry for entry in reversed(entries) if isinstance(entry, dict) and str(entry.get("type", "")).lower() == "error"),
            None,
        )
        summary = {
            "entry_count": len(entries),
            "level_histogram": dict(levels),
            "last_error_excerpt": (str(last_error_entry.get("text"))[:200] if last_error_entry else None),
        }
        return path, byte_count, sha, summary, text, keyword
    raise _SnapshotCaptureError(attempted=["Get Console Log"], detail=last_error)


class _SnapshotCaptureError(RuntimeError):
    def __init__(self, *, attempted: list[str], detail: str | None) -> None:
        super().__init__(detail or "snapshot capture failed")
        self.attempted = attempted
        self.detail = detail


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def capture_inspection_snapshot(
    store: LiveSessionStore,
    session_id: str,
    snapshot_kind: str,
    *,
    selector: str | None = None,
    return_inline: bool = False,
    inline_max_bytes: int | None = None,
    summary_only: bool = False,
    include_shadow_dom: bool = False,
) -> InspectionSnapshotResult | ErrorEnvelope:
    try:
        kind = SnapshotKind(snapshot_kind)
    except ValueError:
        return ErrorEnvelope(
            code="unsupported-snapshot-kind",
            message=f"Snapshot kind '{snapshot_kind}' is not part of the approved inspection surface.",
            severity=Severity.ERROR,
            provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="inspection-surface"),
            retryable=False,
            suggested_next_step="Use one of the approved snapshot kinds: app_context, dom, dom_selector, aria, screenshot, console_log, network_log.",
            details={"snapshot_kind": snapshot_kind},
        )

    if kind in (SnapshotKind.DOM_SELECTOR,) and not (selector and selector.strip()):
        return ErrorEnvelope(
            code="missing-selector",
            message=f"Snapshot kind '{kind.value}' requires a non-empty selector.",
            severity=Severity.ERROR,
            provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="inspection-surface"),
            retryable=False,
            suggested_next_step="Pass a selector such as 'id=main' or 'css=[data-test=foo]'.",
            details={"snapshot_kind": kind.value},
        )

    try:
        policy = load_local_policy_defaults()
    except (OSError, ValueError, ValidationError) as exc:
        return _policy_load_error(exc)
    if not capability_allowed(policy, PolicyCapability.INSPECTION_SNAPSHOT):
        return ErrorEnvelope(
            code="policy-inspection-disabled",
            message="Inspection snapshots are disabled by local policy.",
            severity=Severity.ERROR,
            provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="local-policy"),
            retryable=False,
            suggested_next_step="Enable approved inspection snapshots in local policy or continue without snapshot capture.",
            details={"session_id": session_id, "snapshot_kind": snapshot_kind},
        )

    record = store.get_record(session_id)
    if record is None:
        return _session_error(session_id)
    if record.status == SessionStatus.CLOSED:
        return _session_error(session_id, record.status.value)
    if kind not in record.allowed_snapshot_kinds:
        return ErrorEnvelope(
            code="session-snapshot-disabled",
            message=f"Snapshot kind '{snapshot_kind}' is not enabled for this live session.",
            severity=Severity.ERROR,
            provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="session-store"),
            retryable=True,
            suggested_next_step="Request an allowed snapshot kind for this session or open a session with the required inspection capability.",
            details={"session_id": session_id, "snapshot_kind": snapshot_kind},
        )

    engine = store.get_or_create_engine(session_id)
    if engine is None:
        return _session_error(session_id, SessionStatus.CLOSED.value)

    if kind == SnapshotKind.NETWORK_LOG:
        return _snapshot_unavailable(
            session_id,
            snapshot_kind,
            attempted=[],
            detail="network_log is not produced on-demand; record a HAR at context creation instead.",
            next_step=(
                "Open the Browser context with 'New Context  recordHar={\"path\": \"<file>.har\"}' "
                "to record traffic, then read the HAR file directly. On-demand network_log capture "
                "is not part of the v1 surface."
            ),
        )

    try:
        if kind == SnapshotKind.APP_CONTEXT:
            path, byte_count, sha, summary, payload = _capture_app_context(engine, session_id, kind)
            source = "live-session"
        elif kind == SnapshotKind.DOM:
            path, byte_count, sha, summary, payload, keyword = _capture_dom(
                engine, session_id, kind, include_shadow_dom=include_shadow_dom
            )
            source = f"keyword:{keyword}"
        elif kind == SnapshotKind.DOM_SELECTOR:
            path, byte_count, sha, summary, payload, keyword = _capture_dom_selector(
                engine, session_id, kind, selector or ""
            )
            source = f"keyword:{keyword}"
        elif kind == SnapshotKind.ARIA:
            path, byte_count, sha, summary, payload, keyword = _capture_aria(engine, session_id, kind, selector)
            source = f"keyword:{keyword}"
        elif kind == SnapshotKind.SCREENSHOT:
            path, byte_count, sha, summary, payload, keyword = _capture_screenshot(engine, session_id, kind)
            source = f"keyword:{keyword}"
        elif kind == SnapshotKind.CONSOLE_LOG:
            path, byte_count, sha, summary, payload, keyword = _capture_console_log(engine, session_id, kind)
            source = f"keyword:{keyword}"
        else:  # pragma: no cover — exhausted above
            return _snapshot_unavailable(session_id, snapshot_kind, attempted=[], detail="unhandled kind")
    except _SnapshotCaptureError as exc:
        return _snapshot_unavailable(
            session_id, snapshot_kind, attempted=exc.attempted, detail=exc.detail
        )
    except Exception as exc:
        return _snapshot_unavailable(session_id, snapshot_kind, attempted=[], detail=str(exc))

    manifest = _build_manifest(path, kind, byte_count, sha, summary)

    if kind == SnapshotKind.SCREENSHOT:
        # Binary; never inline.
        content: str | None = None
        truncated = False
    elif kind == SnapshotKind.APP_CONTEXT and not summary_only:
        # Always inline (compact, useful).
        content, truncated = (payload, False)
    else:
        content, truncated = _maybe_inline_text(
            payload,
            kind,
            return_inline=return_inline,
            inline_max_bytes=inline_max_bytes,
            summary_only=summary_only,
        )

    return InspectionSnapshotResult(
        session=record.to_summary(),
        snapshot_kind=kind,
        provenance=_observed(source),
        manifest=manifest,
        content=content,
        truncated=truncated,
    )
