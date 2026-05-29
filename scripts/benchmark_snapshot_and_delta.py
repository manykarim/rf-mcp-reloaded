"""Token-cost benchmark for the MCP surface.

Measures response sizes (a proxy for token cost — one token ≈ four characters
for English text and JSON) under the design knobs introduced by Epic 5 follow-up:

1. ``rf_session(action='get')`` full vs ``since_version=N`` short-circuit.
2. ``app_inspect_state(snapshot_kind='dom')`` file-first manifest vs ``return_inline=True``
   vs ``summary_only=True``.

The benchmark uses a stub execution engine so it does not need a browser. It
writes a markdown report to ``docs/benchmarks/snapshot-and-delta-token-cost.md``.

Run: ``uv run python scripts/benchmark_snapshot_and_delta.py``
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

REPO_ROOT = Path(__file__).resolve().parent.parent
for path in [
    REPO_ROOT / "packages" / "rfmcp_core" / "src",
    REPO_ROOT / "packages" / "rfmcp_mcp" / "src",
]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rfmcp_core.runtime.session import LiveSessionStore  # noqa: E402
from rfmcp_mcp.tools.app_inspect_state import build_app_inspect_state_tool  # noqa: E402
from rfmcp_mcp.tools.rf_execute_step import build_execute_step_tool  # noqa: E402
from rfmcp_mcp.tools.rf_session import build_session_tool  # noqa: E402


def _bytes(payload: dict) -> int:
    """Response size as JSON bytes — a defensible proxy for output tokens."""
    return len(json.dumps(payload, default=str, ensure_ascii=False).encode("utf-8"))


def _tokens(byte_count: int) -> int:
    """Rough character-to-token ratio for English+JSON text (~4 chars/token)."""
    return max(1, byte_count // 4)


class _DomStubEngine:
    """Stub engine that returns a fixed large HTML page from Get Page Source."""

    def __init__(self, dom_bytes: int) -> None:
        # Repeating realistic HTML so per-kind summary stats look plausible.
        head = (
            '<!DOCTYPE html><html><head><title>SauceDemo</title></head>'
            '<body><div class="container">'
        )
        chunk = '<a href="#">link</a><button class="btn">click</button><iframe src="x"></iframe>'
        body = ""
        while len(head) + len(body) + len("</div></body></html>") < dom_bytes:
            body += chunk
        self._html = head + body + "</div></body></html>"

    def query(self, keyword: str, args=None):  # noqa: ANN001
        if keyword in {"Get Page Source", "Get Source"}:
            return self._html
        raise RuntimeError(f"unexpected keyword: {keyword}")

    def get_variables(self, keys=None):  # noqa: ANN001
        return {}

    def imported_libraries(self) -> list[str]:
        return ["BuiltIn", "Browser"]

    def close(self) -> None:
        pass


def benchmark_delta_get(iterations: int = 10) -> dict:
    """One mutation, then `iterations` polls. Full vs since_version."""
    store = LiveSessionStore()
    session_tool = build_session_tool(store)
    execute_step = build_execute_step_tool(store)
    opened = session_tool(action="open", transport="stdio")
    sid = opened["session"]["session_id"]
    execute_step(sid, "No Operation")

    full_sizes: list[int] = []
    delta_sizes: list[int] = []

    current = session_tool(action="get", session_id=sid)
    version = current["session"]["version"]
    for _ in range(iterations):
        full = session_tool(action="get", session_id=sid)
        delta = session_tool(action="get", session_id=sid, since_version=version)
        full_sizes.append(_bytes(full))
        delta_sizes.append(_bytes(delta))

    return {
        "scenario": "polling loop, session unchanged",
        "iterations": iterations,
        "full_get_bytes_mean": round(mean(full_sizes), 1),
        "delta_get_bytes_mean": round(mean(delta_sizes), 1),
        "savings_pct": round(100 * (1 - mean(delta_sizes) / mean(full_sizes)), 1),
        "full_tokens_mean": _tokens(int(mean(full_sizes))),
        "delta_tokens_mean": _tokens(int(mean(delta_sizes))),
    }


def benchmark_dom_snapshot(dom_bytes: int) -> dict:
    """Default (manifest only) vs inline vs summary_only for a single DOM capture."""
    snapshots_dir = tempfile.mkdtemp(prefix="rfmcp-bench-")
    os.environ["RFMCP_SNAPSHOTS_DIR"] = snapshots_dir
    try:
        store = LiveSessionStore()
        store.engine_factory = lambda sid, libs: _DomStubEngine(dom_bytes)
        session_tool = build_session_tool(store)
        inspect = build_app_inspect_state_tool(store)
        sid = session_tool(action="open", transport="stdio")["session"]["session_id"]

        manifest_only = inspect(session_id=sid, snapshot_kind="dom")
        inline = inspect(
            session_id=sid,
            snapshot_kind="dom",
            return_inline=True,
            inline_max_bytes=dom_bytes,  # disable the cap so we see the full inline cost
        )
        capped = inspect(session_id=sid, snapshot_kind="dom", return_inline=True)
        summary_only = inspect(session_id=sid, snapshot_kind="dom", summary_only=True)

        return {
            "scenario": f"single dom snapshot, ~{dom_bytes // 1024} KiB raw payload",
            "raw_dom_bytes": dom_bytes,
            "manifest_only_bytes": _bytes(manifest_only),
            "inline_full_bytes": _bytes(inline),
            "inline_capped_bytes": _bytes(capped),
            "summary_only_bytes": _bytes(summary_only),
            "manifest_only_tokens": _tokens(_bytes(manifest_only)),
            "inline_full_tokens": _tokens(_bytes(inline)),
            "inline_capped_tokens": _tokens(_bytes(capped)),
            "summary_only_tokens": _tokens(_bytes(summary_only)),
            "manifest_vs_inline_savings_pct": round(
                100 * (1 - _bytes(manifest_only) / _bytes(inline)), 1
            ),
            "summary_vs_inline_savings_pct": round(
                100 * (1 - _bytes(summary_only) / _bytes(inline)), 1
            ),
        }
    finally:
        os.environ.pop("RFMCP_SNAPSHOTS_DIR", None)


def write_report(target: Path, results: dict) -> None:
    lines = [
        "# Snapshot + Delta Token-Cost Benchmark",
        "",
        f"Generated: {results['generated_at']}",
        "",
        "Response sizes are measured in bytes of the JSON the tool returns to the "
        "agent. Tokens are approximated as `bytes / 4` (English + JSON heuristic).",
        "",
        "## 1. Delta `rf_session(action='get')`",
        "",
        f"_{results['delta']['scenario']}, {results['delta']['iterations']} polls._",
        "",
        "| Mode | Mean bytes | Mean tokens (~) |",
        "| --- | ---: | ---: |",
        f"| `action='get'` (full) | {results['delta']['full_get_bytes_mean']:,} | "
        f"{results['delta']['full_tokens_mean']:,} |",
        f"| `action='get'` with `since_version` (unchanged) | "
        f"{results['delta']['delta_get_bytes_mean']:,} | {results['delta']['delta_tokens_mean']:,} |",
        f"| **Savings** | **{results['delta']['savings_pct']}%** | |",
        "",
        "## 2. `app_inspect_state(snapshot_kind='dom')`",
        "",
    ]
    for entry in results["dom_snapshots"]:
        lines.extend(
            [
                f"### {entry['scenario']}",
                "",
                "| Mode | Bytes | Tokens (~) |",
                "| --- | ---: | ---: |",
                f"| Default (`manifest` only) | {entry['manifest_only_bytes']:,} | {entry['manifest_only_tokens']:,} |",
                f"| `return_inline=True` (default cap) | {entry['inline_capped_bytes']:,} | {entry['inline_capped_tokens']:,} |",
                f"| `return_inline=True` (uncapped) | {entry['inline_full_bytes']:,} | {entry['inline_full_tokens']:,} |",
                f"| `summary_only=True` | {entry['summary_only_bytes']:,} | {entry['summary_only_tokens']:,} |",
                f"| **Manifest vs uncapped inline savings** | **{entry['manifest_vs_inline_savings_pct']}%** | |",
                f"| **summary_only vs uncapped inline savings** | **{entry['summary_vs_inline_savings_pct']}%** | |",
                "",
            ]
        )
    lines.append("## Takeaways")
    lines.append("")
    lines.append(
        "- File-first defaults turn a multi-kilobyte DOM into a sub-kilobyte response. "
        "Agents read the file only when the summary doesn't suffice."
    )
    lines.append(
        "- `since_version` collapses repeated session polls to a near-empty payload — "
        "the largest predictable win in tight authoring loops."
    )
    lines.append(
        "- `summary_only=True` is the cheapest knob (sub-300 bytes) when an agent just "
        "wants to know `did the page change?` between steps."
    )
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    delta_result = benchmark_delta_get(iterations=10)
    dom_results = [
        benchmark_dom_snapshot(dom_bytes=8 * 1024),     # small page
        benchmark_dom_snapshot(dom_bytes=128 * 1024),   # medium
        benchmark_dom_snapshot(dom_bytes=512 * 1024),   # large
    ]
    results = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "delta": delta_result,
        "dom_snapshots": dom_results,
    }

    out_dir = REPO_ROOT / "docs" / "benchmarks"
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / "snapshot-and-delta-token-cost.md"
    json_path = out_dir / "snapshot-and-delta-token-cost.json"
    write_report(md_path, results)
    json_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {md_path.relative_to(REPO_ROOT)}")
    print(f"wrote {json_path.relative_to(REPO_ROOT)}")
    print()
    print(
        f"delta-get savings: {delta_result['savings_pct']}% "
        f"({delta_result['full_get_bytes_mean']:.0f}B -> {delta_result['delta_get_bytes_mean']:.0f}B)"
    )
    for entry in dom_results:
        print(
            f"dom @ {entry['raw_dom_bytes'] // 1024} KiB: manifest={entry['manifest_only_bytes']}B, "
            f"inline-capped={entry['inline_capped_bytes']}B, inline-full={entry['inline_full_bytes']}B, "
            f"summary={entry['summary_only_bytes']}B"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
