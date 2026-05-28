from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
for path in [
    REPO_ROOT / "packages" / "rfmcp_core" / "src",
    REPO_ROOT / "packages" / "rfmcp_mcp" / "src",
]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rfmcp_mcp.benchmarks import run_live_mcp_repair_proof, write_live_mcp_proof_pack  # noqa: E402


class LiveMcpRepairProofTests(unittest.TestCase):
    def test_live_repair_loop_fails_then_repairs_then_passes(self) -> None:
        proof = run_live_mcp_repair_proof()

        self.assertEqual(proof.surface, "mcp")
        self.assertTrue(proof.reproduced_failure)
        self.assertTrue(proof.repaired)
        self.assertTrue(proof.rerun_ok)
        self.assertTrue(proof.runnable_success)
        # Exactly the reproduced failure fails; every other call (incl. close) succeeds.
        self.assertEqual(proof.tool_calls, 7)
        self.assertEqual(proof.failed_tool_calls, 1)

        # Exactly two execute_step calls: the live failure, then the live pass.
        exec_calls = [call for call in proof.calls if call.tool == "rf_execute_step"]
        self.assertEqual(len(exec_calls), 2)
        self.assertFalse(exec_calls[0].ok)  # reproduced failure (real RF)
        self.assertTrue(exec_calls[1].ok)  # rerun passes after repair

        # The whole loop ran through the bounded MCP tool surface.
        tools = {call.tool for call in proof.calls}
        self.assertEqual(
            tools,
            {
                "rf_session",
                "rf_execute_step",
                "rf_context",
                "app_inspect_state",
            },
        )

    def test_proof_pack_writes_concrete_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "epic5-live-mcp-proof.json"
            write_live_mcp_proof_pack(output)
            data = json.loads(output.read_text(encoding="utf-8"))
        # Assert concrete expected values, not a comparison against the same run.
        self.assertEqual(data["surface"], "mcp")
        self.assertEqual(data["scenario"], "live-mcp-repair")
        self.assertTrue(data["runnable_success"])
        self.assertEqual(data["tool_calls"], 7)
        self.assertEqual(data["failed_tool_calls"], 1)
        self.assertEqual(len(data["calls"]), 7)


if __name__ == "__main__":
    unittest.main()
