from __future__ import annotations

from rfmcp_core.contracts import (
    FailureCategory,
    FailureContext,
    FailureNormalization,
    HintCandidate,
    ProvenanceKind,
    ProvenanceRecord,
    RecoveryCandidate,
)
from rfmcp_core.hints.hookspecs import hookimpl
from rfmcp_provider_browser.metadata import get_provider_metadata


BROWSER_KEYWORDS = {
    "new browser",
    "new page",
    "click",
    "type text",
    "get title",
    "close browser",
}


class BrowserProvider:
    @hookimpl
    def get_provider_metadata(self):
        return get_provider_metadata()

    @hookimpl
    def normalize_failure_context(self, context: FailureContext):
        keywords = {item.casefold() for item in context.observed_keywords}
        if context.library is None and (keywords.intersection(BROWSER_KEYWORDS) or "browser" in (context.failure_message or "").casefold()):
            return FailureNormalization(
                provider_id="robotframework.browser",
                library="Browser",
                categories=[FailureCategory.LIBRARY],
                notes=["Browser provider inferred the Browser library from observed keywords or failure text."],
            )
        return None

    @hookimpl
    def contribute_contextual_hints(self, context: FailureContext):
        candidates: list[HintCandidate] = []
        if context.library == "Browser" and context.error_code == "unknown-keyword":
            candidates.append(
                HintCandidate(
                    hint_id="browser-provider-unknown-keyword",
                    summary="The failing keyword looks like a Browser Library call that is missing or misspelled.",
                    recovery="Verify that Browser is imported and compare the keyword spelling against Browser Library documentation.",
                    provenance=ProvenanceRecord(
                        kind=ProvenanceKind.PROVIDER,
                        source="robotframework.browser",
                        source_type="provider",
                        source_id="robotframework.browser.contextual_hints",
                        provider_id="robotframework.browser",
                        source_version="0.1.0",
                    ),
                    confidence=0.9,
                    tags=["browser", "keyword"],
                )
            )
        if context.library == "Browser" and context.error_code in {
            "unknown-keyword",
            "keyword-arguments-mismatch",
            "ambiguous-keyword",
        }:
            candidates.append(
                HintCandidate(
                    hint_id="browser-official-docs",
                    summary="Browser Library documentation is the authoritative source for Browser keyword spelling and call shapes.",
                    recovery="Check the official Browser Library keyword documentation for the exact keyword name and argument signature before retrying.",
                    provenance=ProvenanceRecord(
                        kind=ProvenanceKind.OFFICIAL,
                        source="robotframework-browser-docs",
                        source_type="official-docs",
                        source_id="robotframework.browser.docs",
                        provider_id="robotframework.browser",
                        source_version="0.1.0",
                    ),
                    confidence=0.75,
                    tags=["browser", "official-docs"],
                )
            )
        return candidates

    @hookimpl
    def contribute_recovery_candidates(self, context: FailureContext):
        candidates: list[RecoveryCandidate] = []
        if context.library == "Browser":
            candidates.append(
                RecoveryCandidate(
                    candidate_id="browser-provider-import-recovery",
                    summary="Import Browser explicitly before retrying Browser Library keywords.",
                    action="Add `Library    Browser` in *** Settings *** and rerun repair diagnostics or execution.",
                    provenance=ProvenanceRecord(
                        kind=ProvenanceKind.PROVIDER,
                        source="robotframework.browser",
                        source_type="provider",
                        source_id="robotframework.browser.recovery_candidates",
                        provider_id="robotframework.browser",
                        source_version="0.1.0",
                    ),
                    confidence=0.85,
                    tags=["browser", "library"],
                )
            )
        return candidates


plugin = BrowserProvider()
