from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import re
from typing import Literal

from robot.libdocpkg import LibraryDocumentation

from rfmcp_core.contracts import (
    ErrorEnvelope,
    FailureContext,
    GroundingKeyword,
    GroundingLibrary,
    GroundingResult,
    HintCandidate,
    ProviderFailure,
    ProvenanceKind,
    ProvenanceRecord,
    ScaffoldArtifact,
    ScaffoldResult,
    Severity,
    ValidationResult,
)
from rfmcp_core.hints import resolve_hints
from rfmcp_core.hints.plugin_manager import ProviderPluginManager
from rfmcp_core.robot.validation import validate_robot_artifact


STANDARD_LIBRARIES: tuple[tuple[str, str], ...] = (
    ("BuiltIn", "Robot Framework built-in keyword library."),
    ("Collections", "Robot Framework standard library for collection operations."),
    ("String", "Robot Framework standard library for string operations."),
    ("OperatingSystem", "Robot Framework standard library for filesystem and process-shell helpers."),
    ("Process", "Robot Framework standard library for process execution."),
    ("DateTime", "Robot Framework standard library for date and time helpers."),
)
BROWSER_KEYWORDS = {"new browser", "new page", "click", "type text", "get title", "close browser"}


def _titleize(raw: str, fallback: str) -> str:
    normalized = re.sub(r"[_\-]+", " ", raw).strip()
    if not normalized:
        return fallback
    return " ".join(part.capitalize() for part in normalized.split())


def _library_error(
    code: str,
    message: str,
    suggested_next_step: str,
    *,
    retryable: bool = False,
    details: dict[str, str] | None = None,
) -> ErrorEnvelope:
    return ErrorEnvelope(
        code=code,
        message=message,
        severity=Severity.ERROR,
        provenance=ProvenanceRecord(
            kind=ProvenanceKind.OBSERVED,
            source="rfmcp-cli.grounding",
            source_type="workflow",
            source_id=code,
        ),
        retryable=retryable,
        suggested_next_step=suggested_next_step,
        details=details,
    )


def _dedupe_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = value.casefold()
        if normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(value)
    return ordered


@lru_cache(maxsize=None)
def _load_library_documentation(import_name: str) -> LibraryDocumentation | None:
    try:
        return LibraryDocumentation(import_name)
    except Exception:
        return None


def _library_short_description(import_name: str, documentation: LibraryDocumentation | None, fallback: str | None = None) -> str | None:
    if documentation is not None and getattr(documentation, "doc", ""):
        return documentation.doc.strip().splitlines()[0]
    return fallback


def _provider_catalog() -> tuple[list[GroundingLibrary], list[ProviderFailure]]:
    manager = ProviderPluginManager()
    providers, failures = manager.load_providers()
    libraries: list[GroundingLibrary] = []

    for import_name, description in STANDARD_LIBRARIES:
        documentation = _load_library_documentation(import_name)
        libraries.append(
            GroundingLibrary(
                name=import_name,
                import_name=import_name,
                description=_library_short_description(import_name, documentation, description),
                importable=documentation is not None,
                keyword_count=len(documentation.keywords) if documentation is not None else None,
                provenance=ProvenanceRecord(
                    kind=ProvenanceKind.OFFICIAL,
                    source="robotframework-libdoc",
                    source_type="official-docs",
                    source_id=import_name,
                ),
            )
        )

    for provider in providers:
        for library_name in provider.metadata.library_names:
            documentation = _load_library_documentation(library_name)
            libraries.append(
                GroundingLibrary(
                    name=library_name,
                    import_name=library_name,
                    provider_id=provider.provider_id,
                    description=_library_short_description(library_name, documentation, provider.metadata.description),
                    importable=documentation is not None,
                    keyword_count=len(documentation.keywords) if documentation is not None else None,
                    provenance=ProvenanceRecord(
                        kind=ProvenanceKind.PROVIDER,
                        source=provider.provider_id,
                        source_type="provider",
                        source_id=provider.provider_id,
                        provider_id=provider.provider_id,
                        source_version=provider.metadata.version,
                    ),
                )
            )

    deduped: dict[str, GroundingLibrary] = {}
    for item in libraries:
        deduped.setdefault(item.import_name.casefold(), item)
    return list(deduped.values()), failures


def _grounding_guidance(query: str, matched_libraries: list[GroundingLibrary], matched_keywords: list[GroundingKeyword]) -> list[HintCandidate]:
    lowered = query.casefold()
    browser_related = any(library.name.casefold() == "browser" for library in matched_libraries) or lowered in BROWSER_KEYWORDS or "browser" in lowered
    if browser_related:
        context = FailureContext(
            target=f"grounding:{query}",
            error_code="unknown-keyword",
            failure_message=None,
            live_state_available=False,
            library="Browser",
            keyword=query if lowered != "browser" else None,
            libraries=["Browser"],
            observed_keywords=[query] if lowered != "browser" else [],
        )
        return resolve_hints(context).hint.candidates[:3]

    if matched_keywords or matched_libraries:
        return []

    return [
        HintCandidate(
            hint_id="inferred-ground-before-generation",
            summary="No deterministic keyword grounding matches were found for this query.",
            recovery="Refine the library or keyword query before generation, or ground a known Robot Framework library explicitly.",
            provenance=ProvenanceRecord(
                kind=ProvenanceKind.INFERRED,
                source="rfmcp-cli.grounding",
                source_type="workflow",
                source_id="inferred-ground-before-generation",
            ),
            confidence=0.65,
            tags=["grounding", "generation-prevention"],
        )
    ]


def run_grounding(query: str, *, libraries: list[str] | None = None, limit: int = 10) -> GroundingResult:
    query_text = query.strip()
    selected_libraries = {item.casefold() for item in (libraries or [])}
    catalog, provider_failures = _provider_catalog()
    library_matches: list[GroundingLibrary] = []
    keyword_matches: list[GroundingKeyword] = []
    lowered_query = query_text.casefold()

    for library in catalog:
        if selected_libraries and library.name.casefold() not in selected_libraries and library.import_name.casefold() not in selected_libraries:
            continue

        name_match = lowered_query in library.name.casefold() or lowered_query in library.import_name.casefold()
        documentation = _load_library_documentation(library.import_name) if library.importable else None
        keywords = documentation.keywords if documentation is not None else []
        matched_keywords = [
            keyword for keyword in keywords
            if lowered_query in keyword.name.casefold()
        ]

        if name_match or matched_keywords:
            library_matches.append(library)

        if matched_keywords:
            for keyword in matched_keywords[:limit]:
                keyword_matches.append(
                    GroundingKeyword(
                        library_name=library.name,
                        keyword_name=keyword.name,
                        args_signature=str(keyword.args) if getattr(keyword, "args", None) is not None else None,
                        documentation_excerpt=keyword.doc.strip().splitlines()[0] if getattr(keyword, "doc", "") else None,
                        provenance=library.provenance,
                    )
                )
        elif name_match and keywords:
            for keyword in sorted(keywords, key=lambda item: item.name.casefold())[:limit]:
                keyword_matches.append(
                    GroundingKeyword(
                        library_name=library.name,
                        keyword_name=keyword.name,
                        args_signature=str(keyword.args) if getattr(keyword, "args", None) is not None else None,
                        documentation_excerpt=keyword.doc.strip().splitlines()[0] if getattr(keyword, "doc", "") else None,
                        provenance=library.provenance,
                    )
                )

    deduped_library_matches = _dedupe_preserve_order([library.import_name for library in library_matches])
    ordered_libraries = [next(item for item in library_matches if item.import_name == key) for key in deduped_library_matches]
    guidance = _grounding_guidance(query_text, ordered_libraries, keyword_matches)

    if not ordered_libraries and not keyword_matches:
        error = _library_error(
            "no-grounding-matches",
            f"No deterministic grounding matches were found for '{query_text}'.",
            "Refine the query, specify a library filter, or inspect a known Robot Framework library before generation.",
            details={"query": query_text},
        )
        return GroundingResult(
            ok=False,
            query=query_text,
            libraries=[],
            keywords=[],
            preventive_guidance=guidance,
            provider_failures=provider_failures,
            error=error,
        )

    return GroundingResult(
        ok=True,
        query=query_text,
        libraries=ordered_libraries,
        keywords=keyword_matches[:limit],
        preventive_guidance=guidance,
        provider_failures=provider_failures,
    )


def _generic_scaffold_guidance(kind: str, *, libraries: list[str] | None = None) -> list[HintCandidate]:
    guidance = [
        HintCandidate(
            hint_id=f"inferred-{kind}-grounding-next-step",
            summary="Ground the target library and keywords before filling in real Robot steps.",
            recovery="Run the grounding command for the intended library or keyword set before generation so the scaffold grows from real context.",
            provenance=ProvenanceRecord(
                kind=ProvenanceKind.INFERRED,
                source="rfmcp-cli.scaffold",
                source_type="workflow",
                source_id=f"inferred-{kind}-grounding-next-step",
            ),
            confidence=0.7,
            tags=["scaffold", "grounding", "generation-prevention"],
        )
    ]
    if libraries and any(item.casefold() == "browser" for item in libraries):
        context = FailureContext(
            target=f"scaffold:{kind}",
            error_code="unknown-keyword",
            failure_message=None,
            live_state_available=False,
            library="Browser",
            libraries=["Browser"],
            observed_keywords=["New Page"],
        )
        guidance.extend(resolve_hints(context).hint.candidates[:2])
    return guidance


def _allowed_scaffold_suffixes(kind: Literal["suite", "resource"]) -> tuple[str, ...]:
    if kind == "resource":
        return (".resource", ".robot")
    return (".robot",)


def _write_scaffold(
    target: str,
    *,
    kind: Literal["suite", "resource"],
    content: str,
    existed: bool,
    force: bool,
) -> ScaffoldResult:
    path = Path(target)
    allowed_suffixes = _allowed_scaffold_suffixes(kind)
    if path.suffix not in allowed_suffixes:
        error = _library_error(
            "unsupported-extension",
            f"Scaffolding for {kind} files expects one of: {', '.join(allowed_suffixes)}.",
            f"Point the scaffold command at a supported {kind} file path and retry.",
            details={"target": target, "suffix": path.suffix, "kind": kind},
        )
        return ScaffoldResult(
            ok=False,
            artifact=ScaffoldArtifact(
                path=target,
                kind=kind,
                content=content,
                validation=ValidationResult(ok=False, target=target, error=error),
            ),
            preventive_guidance=[],
            created=False,
            overwritten=False,
            error=error,
        )

    if existed and not force:
        error = _library_error(
            "target-exists",
            f"Scaffold target '{target}' already exists.",
            "Re-run with force enabled or choose a new target path.",
            retryable=True,
            details={"target": target},
        )
        return ScaffoldResult(
            ok=False,
            artifact=ScaffoldArtifact(
                path=target,
                kind=kind,
                content=content,
                validation=ValidationResult(ok=False, target=target, error=error),
            ),
            preventive_guidance=[],
            created=False,
            overwritten=False,
            error=error,
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    validation = validate_robot_artifact(target)
    return ScaffoldResult(
        ok=validation.ok,
        artifact=ScaffoldArtifact(path=target, kind=kind, content=content, validation=validation),
        preventive_guidance=[],
        created=not existed,
        overwritten=existed,
    )


def scaffold_suite(
    target: str,
    *,
    suite_name: str | None = None,
    test_case_name: str = "Smoke Test",
    libraries: list[str] | None = None,
    resources: list[str] | None = None,
    documentation: str | None = None,
    force: bool = False,
) -> ScaffoldResult:
    path = Path(target)
    existed = path.exists()
    deduped_libraries = _dedupe_preserve_order(["BuiltIn", *(libraries or [])])
    deduped_resources = _dedupe_preserve_order(resources or [])
    suite_title = suite_name or _titleize(path.stem, "Scaffolded Suite")
    test_case_title = _titleize(test_case_name, "Smoke Test")

    lines = [
        "*** Settings ***",
        f"Documentation    {documentation or f'Scaffolded suite for {suite_title}.'}",
    ]
    for library in deduped_libraries:
        lines.append(f"Library    {library}")
    for resource in deduped_resources:
        lines.append(f"Resource    {resource}")
    lines.extend(
        [
            "",
            "*** Test Cases ***",
            test_case_title,
            "    No Operation",
            "",
        ]
    )
    content = "\n".join(lines)
    result = _write_scaffold(target, kind="suite", content=content, existed=existed, force=force)
    if result.error is None:
        result = result.model_copy(update={"preventive_guidance": _generic_scaffold_guidance("suite", libraries=deduped_libraries)})
    return result


def scaffold_resource(
    target: str,
    *,
    keyword_name: str = "Example Keyword",
    documentation: str | None = None,
    force: bool = False,
) -> ScaffoldResult:
    path = Path(target)
    existed = path.exists()
    keyword_title = _titleize(keyword_name, "Example Keyword")
    resource_title = _titleize(path.stem, "Scaffolded Resource")

    content = "\n".join(
        [
            "*** Settings ***",
            f"Documentation    {documentation or f'Scaffolded resource for {resource_title}.'}",
            "",
            "*** Keywords ***",
            keyword_title,
            "    No Operation",
            "",
        ]
    )
    result = _write_scaffold(target, kind="resource", content=content, existed=existed, force=force)
    if result.error is None:
        result = result.model_copy(update={"preventive_guidance": _generic_scaffold_guidance("resource")})
    return result
