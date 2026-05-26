from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
for path in [
    REPO_ROOT / "packages" / "rfmcp_core" / "src",
    REPO_ROOT / "packages" / "rfmcp_cli" / "src",
]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rfmcp_cli.benchmarks import write_epic3_benchmark_pack  # noqa: E402


class Epic3BenchmarkPackTests(unittest.TestCase):
    def test_benchmark_pack_writes_machine_usable_report_and_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "epic3-proof-pack.json"
            event_log = Path(tmpdir) / "epic3-proof-pack.jsonl"
            report = write_epic3_benchmark_pack(output_path, event_log)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            events = [json.loads(line) for line in event_log.read_text(encoding="utf-8").splitlines()]

        self.assertEqual(report.summary.scenario_count, 3)
        self.assertEqual(report.summary.deterministic_scenario_count, 3)
        self.assertEqual(report.summary.deterministic_success_count, 3)
        self.assertEqual({item["scenario_id"] for item in payload["scenarios"]}, {"generation-suite", "refactor-suite", "regenerate-resource"})
        generation = next(item for item in payload["scenarios"] if item["scenario_id"] == "generation-suite")
        refactor = next(item for item in payload["scenarios"] if item["scenario_id"] == "refactor-suite")
        regenerate = next(item for item in payload["scenarios"] if item["scenario_id"] == "regenerate-resource")
        self.assertEqual(generation["runnable_status"], "passed")
        self.assertEqual(refactor["runnable_status"], "passed")
        self.assertEqual(regenerate["runnable_status"], "not-applicable")
        self.assertEqual(regenerate["correction_burden"], 0)
        self.assertEqual(regenerate["human_correction_rate"], 0.0)
        self.assertTrue(all(item["deterministic"] for item in payload["scenarios"]))
        self.assertEqual(len(events), 6)
        self.assertTrue(all(event["benchmark"] for event in events))

    def test_benchmark_script_runs_in_subprocess(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "epic3-proof-pack.json"
            event_log = Path(tmpdir) / "epic3-proof-pack.jsonl"
            result = subprocess.run(
                [
                    "uv",
                    "run",
                    "--group",
                    "dev",
                    "python",
                    "scripts/run_epic3_benchmark_pack.py",
                    "--output",
                    str(output_path),
                    "--event-log",
                    str(event_log),
                ],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["scenario_count"], 3)
            self.assertIn("Wrote 3 Epic 3 benchmark scenarios", result.stdout)
