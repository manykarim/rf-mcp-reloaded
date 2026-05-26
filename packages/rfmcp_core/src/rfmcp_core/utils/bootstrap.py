from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REQUIRED_UV_VERSION = "0.11.16"
PYTHON_VERSION_PIN = "3.11"
MIN_PYTHON = (3, 11)
MAX_PYTHON_EXCLUSIVE = (3, 14)
REPO_ROOT = Path(__file__).resolve().parents[5]


@dataclass(frozen=True)
class VerificationError:
    check: str
    actual: str
    expected: str
    next_step: str


def parse_uv_version(raw: str) -> str | None:
    match = re.search(r"uv\s+([0-9]+(?:\.[0-9]+){1,2})", raw)
    return match.group(1) if match else None


def run_uv_version() -> tuple[str | None, str]:
    try:
        result = subprocess.run(
            ["uv", "--version"],
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError:
        return None, "uv executable not found"

    raw = (result.stdout or result.stderr).strip()
    return parse_uv_version(raw), raw


def python_version_string() -> str:
    version = sys.version_info
    return f"{version.major}.{version.minor}.{version.micro}"


def python_in_supported_range() -> bool:
    version = sys.version_info[:2]
    return MIN_PYTHON <= version < MAX_PYTHON_EXCLUSIVE


def python_pin_matches() -> bool:
    return sys.version_info[:2] == tuple(int(part) for part in PYTHON_VERSION_PIN.split("."))


def verify_environment(repo_root: Path = REPO_ROOT) -> list[VerificationError]:
    errors: list[VerificationError] = []

    if not python_in_supported_range():
        errors.append(
            VerificationError(
                check="python-range",
                actual=python_version_string(),
                expected=">=3.11,<3.14",
                next_step="Install a Python version in the supported range, then rerun `python3 scripts/verify_bootstrap_env.py`.",
            )
        )

    if python_in_supported_range() and not python_pin_matches():
        errors.append(
            VerificationError(
                check="python-pin",
                actual=python_version_string(),
                expected=PYTHON_VERSION_PIN,
                next_step="Activate Python 3.11 for this repository or update `.python-version` only after an architectural change, then rerun `python3 scripts/verify_bootstrap_env.py`.",
            )
        )

    uv_version, uv_raw = run_uv_version()
    if uv_version != REQUIRED_UV_VERSION:
        actual = uv_version or uv_raw
        errors.append(
            VerificationError(
                check="uv-version",
                actual=actual,
                expected=REQUIRED_UV_VERSION,
                next_step="Install or activate `uv 0.11.16`, then rerun `python3 scripts/verify_bootstrap_env.py`.",
            )
        )

    if not (repo_root / "pyproject.toml").exists():
        errors.append(
            VerificationError(
                check="workspace-root",
                actual="missing pyproject.toml",
                expected="workspace root configuration present",
                next_step="Restore the root `pyproject.toml` before continuing.",
            )
        )

    return errors
