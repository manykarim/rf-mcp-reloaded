from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts import export_json_schemas, verify_schema_sync


class SchemaSyncTests(unittest.TestCase):
    def test_export_schemas_writes_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            written = export_json_schemas.export_schemas(Path(tmpdir))

        self.assertEqual({path.name for path in written}, set(export_json_schemas.SCHEMAS))

    def test_verify_schema_sync_passes_for_current_repo(self) -> None:
        self.assertEqual(verify_schema_sync.verify_schema_sync(), [])

    def test_verify_schema_sync_detects_drift(self) -> None:
        schema_path = verify_schema_sync.REPO_ROOT / "assets" / "schemas" / "error-envelope.schema.json"
        original = schema_path.read_text() if schema_path.exists() else None
        try:
            schema_path.parent.mkdir(parents=True, exist_ok=True)
            schema_path.write_text("{\"broken\": true}\n")
            self.assertIn("error-envelope.schema.json", verify_schema_sync.verify_schema_sync())
        finally:
            if original is None:
                schema_path.unlink(missing_ok=True)
            else:
                schema_path.write_text(original)


if __name__ == "__main__":
    unittest.main()
