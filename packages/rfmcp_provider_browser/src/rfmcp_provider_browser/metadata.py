from __future__ import annotations

from rfmcp_core.contracts import ProviderMetadata


def get_provider_metadata() -> ProviderMetadata:
    return ProviderMetadata(
        provider_id="robotframework.browser",
        name="Browser Library",
        version="0.1.0",
        description="Browser Library provider for deterministic repair hint enrichment.",
        library_names=["Browser"],
    )
