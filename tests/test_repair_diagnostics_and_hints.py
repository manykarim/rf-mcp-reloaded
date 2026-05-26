from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

REPO_ROOT = Path(__file__).resolve().parent.parent
for path in [
    REPO_ROOT / "packages" / "rfmcp_core" / "src",
    REPO_ROOT / "packages" / "rfmcp_cli" / "src",
    REPO_ROOT / "packages" / "rfmcp_provider_browser" / "src",
]:
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from rfmcp_cli.main import app  # noqa: E402
from rfmcp_core.contracts import FailureContext, FailureNormalization, HintCandidate, ProvenanceKind, ProvenanceRecord  # noqa: E402
from rfmcp_core.hints import resolve_hints  # noqa: E402
from rfmcp_core.hints.loader import HintPackValidationError, load_hint_packs  # noqa: E402
from rfmcp_core.hints.hookspecs import hookimpl  # noqa: E402
from rfmcp_core.hints.plugin_manager import ProviderPluginManager  # noqa: E402
from rfmcp_core.robot import build_failure_context, run_repair_diagnostics  # noqa: E402
from rfmcp_provider_browser.plugin import BrowserProvider  # noqa: E402


class FakeEntryPoint:
    def __init__(self, name: str, plugin: object) -> None:
        self.name = name
        self._plugin = plugin

    def load(self) -> object:
        return self._plugin


class AlphaProvider:
    @hookimpl
    def get_provider_metadata(self):
        return {
            "provider_id": "alpha.provider",
            "name": "Alpha",
            "version": "1.0.0",
            "description": "Alpha provider",
            "library_names": ["Browser"],
        }

    @hookimpl
    def normalize_failure_context(self, context: FailureContext):
        return FailureNormalization(provider_id="alpha.provider", library="AlphaLibrary")

    @hookimpl
    def contribute_contextual_hints(self, context: FailureContext):
        return [
            HintCandidate(
                hint_id="duplicate-hint",
                summary="Alpha hint",
                recovery="Use alpha recovery.",
                provenance=ProvenanceRecord(
                    kind=ProvenanceKind.PROVIDER,
                    source="alpha.provider",
                    source_type="provider",
                    source_id="alpha.provider.contextual_hints",
                    provider_id="alpha.provider",
                ),
                confidence=0.7,
            )
        ]

    @hookimpl
    def contribute_recovery_candidates(self, context: FailureContext):
        return []


class BrokenProvider(AlphaProvider):
    @hookimpl
    def get_provider_metadata(self):
        return {
            "provider_id": "broken.provider",
            "name": "Broken",
            "version": "1.0.0",
            "description": "Broken provider",
            "library_names": ["Broken"],
        }

    @hookimpl
    def normalize_failure_context(self, context: FailureContext):
        return FailureNormalization(provider_id="broken.provider", library="BrokenLibrary")

    @hookimpl
    def contribute_contextual_hints(self, context: FailureContext):
        raise RuntimeError("boom")


class DuplicateProvider(AlphaProvider):
    @hookimpl
    def get_provider_metadata(self):
        return {
            "provider_id": "duplicate.provider",
            "name": "Duplicate",
            "version": "1.0.0",
            "description": "Duplicate provider",
            "library_names": ["Browser"],
        }

    @hookimpl
    def normalize_failure_context(self, context: FailureContext):
        return FailureNormalization(provider_id="duplicate.provider", library="DuplicateLibrary")

    @hookimpl
    def contribute_contextual_hints(self, context: FailureContext):
        return [
            HintCandidate(
                hint_id="duplicate-hint",
                summary="Duplicate provider hint",
                recovery="Use duplicate provider recovery.",
                provenance=ProvenanceRecord(
                    kind=ProvenanceKind.PROVIDER,
                    source="duplicate.provider",
                    source_type="provider",
                    source_id="duplicate.provider.contextual_hints",
                    provider_id="duplicate.provider",
                ),
                confidence=0.65,
            )
        ]


class RepairDiagnosticsAndHintsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runner = CliRunner()

    def _write_robot_file(self, content: str) -> str:
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        target = Path(tmpdir.name) / "repair.robot"
        target.write_text(content)
        return str(target)

    def test_repair_diagnostics_identify_browser_library_and_live_state_gaps(self) -> None:
        target = self._write_robot_file(
            "*** Test Cases ***\n"
            "Broken Browser Test\n"
            "    New Page    https://example.com\n"
            "    Click    text=Login\n"
        )

        result = run_repair_diagnostics(
            target,
            failure_message="No keyword with name 'New Page' found.",
            live_state_available=False,
            provider_manager=ProviderPluginManager(
                entry_points=[FakeEntryPoint("robotframework.browser", BrowserProvider())]
            ),
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.verification_mode, "static-fallback")
        self.assertEqual(result.context.error_code, "unknown-keyword")
        self.assertEqual(result.context.library, "Browser")
        self.assertIn("browser-library-missing", {finding.code for finding in result.findings})
        self.assertIn("live-state-unavailable", {finding.code for finding in result.findings})
        self.assertIsNotNone(result.hint)
        self.assertIn("browser-official-docs", {candidate.hint_id for candidate in result.hint.candidates})
        self.assertIn(
            "browser-provider-import-recovery",
            {candidate.candidate_id for candidate in result.recovery_candidates},
        )

    def test_hint_resolution_merges_curated_provider_and_inferred_guidance(self) -> None:
        target = self._write_robot_file(
            "*** Test Cases ***\n"
            "Broken Browser Test\n"
            "    New Page    https://example.com\n"
        )
        context = build_failure_context(
            target,
            failure_message="No keyword with name 'New Page' found.",
            live_state_available=False,
        )
        result = resolve_hints(
            context,
            provider_manager=ProviderPluginManager(
                entry_points=[FakeEntryPoint("robotframework.browser", BrowserProvider())]
            ),
        )

        self.assertTrue(result.ok)
        self.assertIn("robotframework.browser.core", result.packs)
        self.assertIn("robotframework.browser", result.providers)
        self.assertIn("browser-library-import-missing", {candidate.hint_id for candidate in result.hint.candidates})
        self.assertIn("browser-provider-unknown-keyword", {candidate.hint_id for candidate in result.hint.candidates})
        self.assertIn("browser-official-docs", {candidate.hint_id for candidate in result.hint.candidates})
        self.assertIn("inferred-live-state-fallback", {candidate.hint_id for candidate in result.hint.candidates})
        self.assertIn(
            "browser-provider-import-recovery",
            {candidate.candidate_id for candidate in result.recovery_candidates},
        )
        curated = next(candidate for candidate in result.hint.candidates if candidate.hint_id == "browser-library-import-missing")
        self.assertEqual(curated.provenance.source_type, "curated-pack")
        self.assertEqual(curated.provenance.source_id, "robotframework.browser.core")
        official = next(candidate for candidate in result.hint.candidates if candidate.hint_id == "browser-official-docs")
        self.assertEqual(official.provenance.kind, ProvenanceKind.OFFICIAL)
        self.assertEqual(official.provenance.source_type, "official-docs")
        inferred = next(candidate for candidate in result.hint.candidates if candidate.hint_id == "inferred-live-state-fallback")
        self.assertEqual(inferred.provenance.kind, ProvenanceKind.INFERRED)
        self.assertEqual(inferred.provenance.source_type, "inferred")

    def test_provider_failures_are_isolated_and_deterministic(self) -> None:
        target = self._write_robot_file(
            "*** Test Cases ***\n"
            "Broken Browser Test\n"
            "    New Page    https://example.com\n"
        )
        context = build_failure_context(target, failure_message="No keyword with name 'New Page' found.")
        manager = ProviderPluginManager(
            entry_points=[
                FakeEntryPoint("broken.provider", BrokenProvider()),
                FakeEntryPoint("alpha.provider", AlphaProvider()),
                FakeEntryPoint("duplicate.provider", DuplicateProvider()),
            ]
        )
        result = resolve_hints(context, provider_manager=manager)

        self.assertTrue(result.ok)
        self.assertEqual(result.providers, ["alpha.provider", "broken.provider", "duplicate.provider"])
        self.assertTrue(any(failure.provider_id == "broken.provider" for failure in result.provider_failures))
        self.assertEqual(next(failure.error.code for failure in result.provider_failures if failure.provider_id == "broken.provider"), "provider-execution-failed")
        self.assertIn("duplicate-hint", {candidate.hint_id for candidate in result.hint.candidates})
        self.assertTrue(any(conflict.hint_id == "duplicate-hint" for conflict in result.conflicts))

    def test_repair_diagnostics_surfaces_provider_failures(self) -> None:
        target = self._write_robot_file(
            "*** Test Cases ***\n"
            "Broken Browser Test\n"
            "    New Page    https://example.com\n"
        )
        manager = ProviderPluginManager(
            entry_points=[
                FakeEntryPoint("broken.provider", BrokenProvider()),
                FakeEntryPoint("alpha.provider", AlphaProvider()),
            ]
        )
        result = run_repair_diagnostics(
            target,
            failure_message="No keyword with name 'New Page' found.",
            provider_manager=manager,
        )

        self.assertFalse(result.ok)
        self.assertTrue(any(failure.provider_id == "broken.provider" for failure in result.provider_failures))

    def test_hint_pack_validation_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            pack_path = Path(tmpdir) / "broken.yaml"
            pack_path.write_text("schema_version: '1.0'\n")
            with self.assertRaises(HintPackValidationError):
                load_hint_packs(Path(tmpdir))

    def test_resolve_hints_returns_structured_error_when_pack_validation_fails(self) -> None:
        target = self._write_robot_file(
            "*** Test Cases ***\n"
            "Broken Browser Test\n"
            "    New Page    https://example.com\n"
        )
        context = build_failure_context(target, failure_message="No keyword with name 'New Page' found.")
        with patch("rfmcp_core.hints.load_hint_packs", side_effect=HintPackValidationError("broken pack")):
            result = resolve_hints(context)

        self.assertFalse(result.ok)
        self.assertEqual(result.error.code, "hint-pack-validation-failed")
        self.assertEqual(result.hint.error_code, "unknown-keyword")
        self.assertFalse(result.provider_discovery_attempted)
        self.assertEqual(result.error.details["provider_discovery"], "not-attempted")

    def test_repair_diagnostics_surfaces_hint_pack_validation_failures(self) -> None:
        target = self._write_robot_file(
            "*** Test Cases ***\n"
            "Broken Browser Test\n"
            "    New Page    https://example.com\n"
        )
        with patch("rfmcp_core.robot.diagnostics.resolve_hints") as resolve_hints_mock:
            resolve_hints_mock.return_value = resolve_hints(
                build_failure_context(target, failure_message="No keyword with name 'New Page' found.")
            ).model_copy(
                update={
                    "ok": False,
                    "error": {
                        "code": "hint-pack-validation-failed",
                        "message": "broken pack",
                        "severity": "error",
                        "provenance": {
                            "kind": "observed",
                            "source": "hint-pack-loader",
                        },
                        "retryable": False,
                        "suggested_next_step": "Fix the authoritative hint pack asset before retrying hint resolution.",
                    },
                }
            )
            result = run_repair_diagnostics(
                target,
                failure_message="No keyword with name 'New Page' found.",
                live_state_available=False,
            )

        self.assertFalse(result.ok)
        self.assertIsNotNone(result.error)
        self.assertEqual(result.error.code, "hint-pack-validation-failed")

    def test_ambiguous_keyword_messages_map_to_ambiguous_keyword_code(self) -> None:
        target = self._write_robot_file(
            "*** Test Cases ***\n"
            "Broken Browser Test\n"
            "    New Page    https://example.com\n"
        )
        result = run_repair_diagnostics(
            target,
            failure_message="Multiple keywords with name 'Click' found. Give the full name of the keyword you want to use.",
        )

        self.assertEqual(result.context.error_code, "ambiguous-keyword")
        self.assertIn("ambiguous-keyword", {finding.code for finding in result.findings})

    def test_keyword_argument_mismatch_maps_to_argument_diagnostic_and_hint(self) -> None:
        target = self._write_robot_file(
            "*** Settings ***\n"
            "Library    Browser\n"
            "*** Test Cases ***\n"
            "Broken Browser Test\n"
            "    New Page    https://example.com\n"
        )
        diagnostics = run_repair_diagnostics(
            target,
            failure_message="Keyword 'Click' expected 1 argument, got 2.",
        )
        self.assertEqual(diagnostics.context.error_code, "keyword-arguments-mismatch")
        self.assertIn("keyword-arguments-mismatch", {finding.code for finding in diagnostics.findings})

        context = build_failure_context(
            target,
            failure_message="Keyword 'Click' expected 1 argument, got 2.",
        )
        result = resolve_hints(
            context,
            provider_manager=ProviderPluginManager(
                entry_points=[FakeEntryPoint("robotframework.browser", BrowserProvider())]
            ),
        )
        self.assertIn("browser-keyword-arguments-review", {candidate.hint_id for candidate in result.hint.candidates})

    def test_cli_commands_emit_stable_json_contracts(self) -> None:
        target = self._write_robot_file(
            "*** Test Cases ***\n"
            "Broken Browser Test\n"
            "    New Page    https://example.com\n"
        )
        diagnostics = self.runner.invoke(
            app,
            [
                "repair-diagnostics",
                target,
                "--failure-message",
                "No keyword with name 'New Page' found.",
                "--no-live-state",
                "--json",
            ],
        )
        self.assertEqual(diagnostics.exit_code, 1)
        diagnostics_payload = json.loads(diagnostics.stdout)
        self.assertEqual(diagnostics_payload["verification_mode"], "static-fallback")
        self.assertEqual(diagnostics_payload["context"]["error_code"], "unknown-keyword")
        self.assertIn("browser-library-missing", {item["code"] for item in diagnostics_payload["findings"]})
        self.assertIn("browser-official-docs", {item["hint_id"] for item in diagnostics_payload["hint"]["candidates"]})
        self.assertIn(
            "browser-provider-import-recovery",
            {item["candidate_id"] for item in diagnostics_payload["recovery_candidates"]},
        )

        hints = self.runner.invoke(
            app,
            [
                "repair-hints",
                target,
                "--failure-message",
                "No keyword with name 'New Page' found.",
                "--no-live-state",
                "--json",
            ],
        )
        self.assertEqual(hints.exit_code, 0)
        hint_payload = json.loads(hints.stdout)
        self.assertTrue(hint_payload["ok"])
        self.assertEqual(hint_payload["context"]["error_code"], "unknown-keyword")
        self.assertIn("robotframework.browser.core", hint_payload["packs"])

    def test_default_hint_pack_lookup_falls_back_to_bundled_package_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            package_dir = Path(tmpdir) / "bundled-packs"
            package_dir.mkdir()
            package_pack = package_dir / "robotframework.browser.yaml"
            package_pack.write_text((REPO_ROOT / "assets" / "hints" / "libraries" / "robotframework.browser.yaml").read_text())
            with patch("rfmcp_core.hints.loader.DEFAULT_HINT_PACK_DIR", Path(tmpdir) / "missing"):
                with patch("rfmcp_core.hints.loader.resources.files", return_value=package_dir):
                    packs = load_hint_packs()

        self.assertIn("robotframework.browser.core", {pack.manifest.pack_id for pack in packs})

    def test_provider_normalization_id_mismatch_is_reported_as_contract_invalid(self) -> None:
        class MismatchedNormalizationProvider:
            @hookimpl
            def get_provider_metadata(self):
                return {
                    "provider_id": "mismatch.provider",
                    "name": "Mismatch",
                    "version": "1.0.0",
                    "description": "Mismatched normalization provider",
                    "library_names": ["Browser"],
                }

            @hookimpl
            def normalize_failure_context(self, context: FailureContext):
                return FailureNormalization(provider_id="different.provider", library="Browser")

            @hookimpl
            def contribute_contextual_hints(self, context: FailureContext):
                return []

            @hookimpl
            def contribute_recovery_candidates(self, context: FailureContext):
                return []

        target = self._write_robot_file(
            "*** Test Cases ***\n"
            "Broken Browser Test\n"
            "    New Page    https://example.com\n"
        )
        context = build_failure_context(target, failure_message="No keyword with name 'New Page' found.")
        result = resolve_hints(
            context,
            provider_manager=ProviderPluginManager(
                entry_points=[FakeEntryPoint("mismatch.provider", MismatchedNormalizationProvider())]
            ),
        )

        self.assertTrue(result.ok)
        failure = next(
            failure
            for failure in result.provider_failures
            if failure.provider_id == "mismatch.provider"
            and failure.stage == "normalize_failure_context"
        )
        self.assertEqual(failure.error.code, "provider-contract-invalid")

    def test_provider_hint_provenance_mismatch_is_reported_as_contract_invalid(self) -> None:
        class MismatchedHintProvider:
            @hookimpl
            def get_provider_metadata(self):
                return {
                    "provider_id": "mismatch.provider",
                    "name": "Mismatch",
                    "version": "1.0.0",
                    "description": "Mismatched hint provider",
                    "library_names": ["Browser"],
                }

            @hookimpl
            def normalize_failure_context(self, context: FailureContext):
                return None

            @hookimpl
            def contribute_contextual_hints(self, context: FailureContext):
                return [
                    HintCandidate(
                        hint_id="mismatched-provider-hint",
                        summary="Bad attribution",
                        recovery="Bad attribution",
                        provenance=ProvenanceRecord(
                            kind=ProvenanceKind.PROVIDER,
                            source="mismatch.provider",
                            source_type="provider",
                            source_id="mismatch.provider.contextual_hints",
                            provider_id="other.provider",
                        ),
                    )
                ]

            @hookimpl
            def contribute_recovery_candidates(self, context: FailureContext):
                return []

        target = self._write_robot_file(
            "*** Test Cases ***\n"
            "Broken Browser Test\n"
            "    New Page    https://example.com\n"
        )
        context = build_failure_context(target, failure_message="No keyword with name 'New Page' found.")
        result = resolve_hints(
            context,
            provider_manager=ProviderPluginManager(
                entry_points=[FakeEntryPoint("mismatch.provider", MismatchedHintProvider())]
            ),
        )

        self.assertTrue(result.ok)
        failure = next(
            failure
            for failure in result.provider_failures
            if failure.provider_id == "mismatch.provider"
            and failure.stage == "contribute_contextual_hints"
        )
        self.assertEqual(failure.error.code, "provider-contract-invalid")


if __name__ == "__main__":
    unittest.main()
