from __future__ import annotations

import json
from pathlib import Path

from rfmcp_core.models.policy import LocalPolicyDefaults


REPO_ROOT = Path(__file__).resolve().parents[5]
DEFAULT_POLICY_PATH = REPO_ROOT / "assets" / "policy" / "local-defaults.json"


def load_local_policy_defaults(path: Path | None = None) -> LocalPolicyDefaults:
    target = path or DEFAULT_POLICY_PATH
    payload = json.loads(target.read_text())
    return LocalPolicyDefaults.model_validate(payload)
