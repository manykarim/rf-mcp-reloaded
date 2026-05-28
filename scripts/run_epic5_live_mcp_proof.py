from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
for _path in [
    REPO_ROOT / "packages" / "rfmcp_core" / "src",
    REPO_ROOT / "packages" / "rfmcp_mcp" / "src",
]:
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from rfmcp_mcp.benchmarks import write_live_mcp_proof_pack  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the Epic 5 live MCP repair proof pack.")
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "dist" / "benchmarks" / "epic5-live-mcp-proof.json",
    )
    args = parser.parse_args()
    proof = write_live_mcp_proof_pack(args.output)
    print(
        f"Wrote Epic 5 live MCP repair proof to {args.output} "
        f"(runnable_success={proof.runnable_success}, tool_calls={proof.tool_calls}, "
        f"failed_tool_calls={proof.failed_tool_calls})"
    )
    # Non-zero exit on a failed proof so CI can treat this as a release gate.
    return 0 if proof.runnable_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
