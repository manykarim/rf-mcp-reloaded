from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
for path in [
    REPO_ROOT / "packages" / "rfmcp_core" / "src",
    REPO_ROOT / "packages" / "rfmcp_cli" / "src",
    REPO_ROOT / "packages" / "rfmcp_mcp" / "src",
]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rfmcp_cli.logging import emit_cli_event  # noqa: E402
from rfmcp_core.models.payloads import ProvenanceKind  # noqa: E402
from rfmcp_core.observability.events import WorkflowEvent  # noqa: E402
from rfmcp_core.policy.enforcement import capability_allowed  # noqa: E402
from rfmcp_core.policy.loader import load_local_policy_defaults  # noqa: E402
from rfmcp_core.policy.capabilities import PolicyCapability  # noqa: E402
from rfmcp_mcp.logging import emit_mcp_event  # noqa: E402


class PolicyAndEventsTests(unittest.TestCase):
    def test_load_local_policy_defaults_uses_committed_asset(self) -> None:
        policy = load_local_policy_defaults()
        self.assertFalse(policy.attach_enabled)
        self.assertTrue(policy.loopback_only_http)
        self.assertFalse(policy.persist_session_credentials)

    def test_capability_allowed_reflects_defaults(self) -> None:
        policy = load_local_policy_defaults()
        self.assertFalse(capability_allowed(policy, PolicyCapability.ATTACH))
        self.assertTrue(capability_allowed(policy, PolicyCapability.LOOPBACK_HTTP))

    def test_cli_and_mcp_events_are_machine_readable_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            cli_path = Path(tmpdir) / "cli.jsonl"
            mcp_path = Path(tmpdir) / "mcp.jsonl"
            emit_cli_event(cli_path, "validate", "result", "cli diagnostic", benchmark=True)
            emit_mcp_event(mcp_path, "repair", "snapshot", "mcp diagnostic")

            cli_payload = json.loads(cli_path.read_text().strip())
            mcp_payload = json.loads(mcp_path.read_text().strip())

        self.assertEqual(cli_payload["surface"], "cli")
        self.assertEqual(mcp_payload["surface"], "mcp")
        self.assertEqual(cli_payload["provenance_kind"], ProvenanceKind.OBSERVED.value)
        self.assertTrue(cli_payload["benchmark"])

    def test_workflow_event_distinguishes_provenance(self) -> None:
        event = WorkflowEvent(
            surface="cli",
            workflow="validate",
            event_type="diagnostic",
            detail="observed filesystem mismatch",
            provenance_kind=ProvenanceKind.OBSERVED,
        )
        self.assertEqual(event.provenance_kind, ProvenanceKind.OBSERVED)
