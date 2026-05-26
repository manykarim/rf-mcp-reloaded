from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
for path in [
    REPO_ROOT / "packages" / "rfmcp_core" / "src",
    REPO_ROOT / "packages" / "rfmcp_cli" / "src",
]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rfmcp_cli.benchmarks import write_epic3_benchmark_pack  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Epic 3 benchmark and proof pack.")
    parser.add_argument("--output", type=Path, default=REPO_ROOT / "dist" / "benchmarks" / "epic3-proof-pack.json")
    parser.add_argument("--event-log", type=Path, default=REPO_ROOT / "dist" / "benchmarks" / "epic3-proof-pack.jsonl")
    args = parser.parse_args()

    report = write_epic3_benchmark_pack(args.output, args.event_log)
    print(f"Wrote {len(report.scenarios)} Epic 3 benchmark scenarios to {args.output}")


if __name__ == "__main__":
    main()
