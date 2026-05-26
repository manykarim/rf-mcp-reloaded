from __future__ import annotations

import tempfile
from pathlib import Path

try:
    from scripts.export_json_schemas import REPO_ROOT, export_schemas
except ImportError:  # pragma: no cover - direct script execution fallback
    from export_json_schemas import REPO_ROOT, export_schemas


def verify_schema_sync() -> list[str]:
    schemas_dir = REPO_ROOT / "assets" / "schemas"
    schemas_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_dir = Path(tmpdir)
        export_schemas(temp_dir)
        drift: list[str] = []
        for generated_path in sorted(temp_dir.iterdir()):
            committed_path = schemas_dir / generated_path.name
            if not committed_path.exists() or committed_path.read_text() != generated_path.read_text():
                drift.append(generated_path.name)
        return drift


def main() -> int:
    drift = verify_schema_sync()
    if not drift:
        print("Schema sync OK")
        return 0

    print("Schema drift detected:")
    for file_name in drift:
        print(f"- {file_name}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
