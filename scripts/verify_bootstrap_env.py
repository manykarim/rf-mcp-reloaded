from __future__ import annotations

from pathlib import Path
import sys

CORE_SRC = Path(__file__).resolve().parent.parent / "packages" / "rfmcp_core" / "src"
if str(CORE_SRC) not in sys.path:
    sys.path.insert(0, str(CORE_SRC))

from rfmcp_core.utils.bootstrap import (  # noqa: E402
    REQUIRED_UV_VERSION,
    REPO_ROOT,
    VerificationError,
    parse_uv_version as _parse_uv_version,
    python_in_supported_range as _python_in_supported_range,
    python_pin_matches as _python_pin_matches,
    python_version_string as _python_version_string,
    run_uv_version as _run_uv_version,
    verify_environment,
)


def main() -> int:
    errors = verify_environment()
    if not errors:
        print("Bootstrap environment OK")
        print(f"- Python: {_python_version_string()}")
        print(f"- uv: {REQUIRED_UV_VERSION}")
        print("- Next step: `uv lock`")
        return 0

    print("Bootstrap environment verification failed.")
    print("The workspace will not continue silently with an unsupported baseline.")
    print()
    for error in errors:
        print(f"[{error.check}] actual={error.actual} expected={error.expected}")
        print(f"next step: {error.next_step}")
        print()

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
