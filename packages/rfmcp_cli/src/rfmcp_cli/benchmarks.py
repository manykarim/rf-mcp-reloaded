from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from rfmcp_core.observability.events import JsonlEventWriter, WorkflowEvent
from rfmcp_core.models.payloads import ProvenanceKind

from rfmcp_cli.workflows.generation import generate_suite_artifact
from rfmcp_cli.workflows.grounding import run_grounding
from rfmcp_cli.workflows.refactor import refactor_existing_artifact, regenerate_existing_artifact


class BenchmarkScenarioResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_id: str = Field(min_length=1)
    workflow: str = Field(min_length=1)
    target_kind: Literal["suite", "resource"]
    setup_friction: int = Field(ge=0)
    tool_call_count: int = Field(ge=0)
    failed_tool_call_rate: float = Field(ge=0.0)
    validation_success: bool
    runnable_status: Literal["passed", "failed", "not-applicable"]
    first_pass_runnable: bool | None = None
    human_correction_rate: float = Field(ge=0.0)
    correction_burden: int = Field(ge=0)
    input_context_size: int = Field(ge=0)
    deterministic: bool
    elapsed_ms: int = Field(ge=0)
    grounding_matches: int | None = Field(default=None, ge=0)
    notes: str | None = None


class BenchmarkSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scenario_count: int = Field(ge=0)
    runnable_scenario_count: int = Field(ge=0)
    runnable_success_count: int = Field(ge=0)
    deterministic_scenario_count: int = Field(ge=0)
    deterministic_success_count: int = Field(ge=0)
    average_correction_burden: float = Field(ge=0.0)


class Epic3BenchmarkReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_version: str = Field(default="1.0", min_length=1)
    generated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    scenarios: list[BenchmarkScenarioResult] = Field(default_factory=list)
    summary: BenchmarkSummary


def _emit_event(writer: JsonlEventWriter | None, workflow: str, event_type: str, detail: str, metadata: dict[str, str]) -> None:
    if writer is None:
        return
    writer.write(
        WorkflowEvent(
            surface="cli",
            workflow=workflow,
            event_type=event_type,
            detail=detail,
            provenance_kind=ProvenanceKind.OBSERVED,
            benchmark=True,
            metadata=metadata,
        )
    )


def _count_context_items(*collections: list[str]) -> int:
    return sum(1 for collection in collections for item in collection if item.strip())


def _summarize(scenarios: list[BenchmarkScenarioResult]) -> BenchmarkSummary:
    runnable_scenarios = [item for item in scenarios if item.runnable_status != "not-applicable"]
    deterministic_scenarios = [item for item in scenarios if item.deterministic]
    average_correction = 0.0
    if scenarios:
        average_correction = sum(item.correction_burden for item in scenarios) / len(scenarios)
    return BenchmarkSummary(
        scenario_count=len(scenarios),
        runnable_scenario_count=len(runnable_scenarios),
        runnable_success_count=sum(1 for item in runnable_scenarios if item.runnable_status == "passed"),
        deterministic_scenario_count=len(scenarios),
        deterministic_success_count=len(deterministic_scenarios),
        average_correction_burden=average_correction,
    )


def _canonicalize_text(value: str, *targets: str) -> str:
    normalized = value
    variants: list[tuple[str, str]] = []
    for target in targets:
        path = Path(target)
        variants.extend([(target, "<target>"), (path.name, "<artifact>")])
    for raw, placeholder in sorted(variants, key=lambda item: len(item[0]), reverse=True):
        normalized = normalized.replace(raw, placeholder)
    return normalized


def _canonicalize_json(value: object, *targets: str) -> object:
    if isinstance(value, str):
        return _canonicalize_text(value, *targets)
    if isinstance(value, list):
        return [_canonicalize_json(item, *targets) for item in value]
    if isinstance(value, dict):
        return {key: _canonicalize_json(item, *targets) for key, item in value.items()}
    return value


def _run_generation_scenario(writer: JsonlEventWriter | None) -> BenchmarkScenarioResult:
    with TemporaryDirectory() as tmpdir:
        query = "Log"
        workflow_calls = 0
        failed_calls = 0
        ground = run_grounding(query, libraries=["BuiltIn"])
        workflow_calls += 1
        failed_calls += int(not ground.ok)
        target_a = Path(tmpdir) / "generated_a.robot"
        target_b = Path(tmpdir) / "generated_b.robot"
        tasks = ["verify greeting output"]
        steps = ["Set Test Variable    ${message}    hello"]
        assertions = ["Should Be Equal As Strings    ${message}    hello"]
        _emit_event(writer, "epic3-generation-proof", "scenario-start", "Running generation reference scenario.", {"scenario": "generation-suite"})
        start_a = perf_counter()
        result_a = generate_suite_artifact(
            str(target_a),
            tasks=tasks,
            steps=steps,
            assertions=assertions,
            libraries=["BuiltIn"],
            documentation="Generated benchmark suite.",
        )
        elapsed_a = perf_counter() - start_a
        workflow_calls += 1
        failed_calls += int(not result_a.ok)
        start_b = perf_counter()
        result_b = generate_suite_artifact(
            str(target_b),
            tasks=tasks,
            steps=steps,
            assertions=assertions,
            libraries=["BuiltIn"],
            documentation="Generated benchmark suite.",
        )
        elapsed_b = perf_counter() - start_b
        elapsed_ms = int(((elapsed_a + elapsed_b) / 2) * 1000)
        deterministic = (
            result_a.ok == result_b.ok
            and result_a.artifact.content == result_b.artifact.content
            and [item.model_dump(mode="json") for item in result_a.evidence] == [item.model_dump(mode="json") for item in result_b.evidence]
            and result_a.execution.ok == result_b.execution.ok
        )
        scenario = BenchmarkScenarioResult(
            scenario_id="generation-suite",
            workflow="generate",
            target_kind="suite",
            setup_friction=0,
            tool_call_count=workflow_calls,
            failed_tool_call_rate=failed_calls / workflow_calls if workflow_calls else 0.0,
            validation_success=result_a.artifact.validation.ok,
            runnable_status="passed" if result_a.execution.ok else "failed",
            first_pass_runnable=result_a.execution.ok,
            human_correction_rate=0.0 if result_a.execution.ok else 1.0,
            correction_burden=len(result_a.correction_path),
            input_context_size=_count_context_items(tasks, steps, assertions, ["BuiltIn"]),
            deterministic=deterministic,
            elapsed_ms=elapsed_ms,
            grounding_matches=len(ground.keywords),
            notes="Grounding plus generate workflow for a new suite.",
        )
        _emit_event(
            writer,
            "epic3-generation-proof",
            "scenario-complete",
            "Completed generation reference scenario.",
            {
                "scenario": scenario.scenario_id,
                "runnable_status": scenario.runnable_status,
                "deterministic": str(scenario.deterministic).lower(),
                "correction_burden": str(scenario.correction_burden),
            },
        )
        return scenario


def _run_refactor_suite_scenario(writer: JsonlEventWriter | None) -> BenchmarkScenarioResult:
    with TemporaryDirectory() as tmpdir:
        original = (
            "*** Settings ***\n"
            "Documentation    Original suite.\n\n"
            "*** Test Cases ***\n"
            "Old Name\n"
            "    Set Test Variable    ${message}    hello\n"
            "    Log    ${message}\n"
        )
        target_a = Path(tmpdir) / "run_a" / "refactor.robot"
        target_b = Path(tmpdir) / "run_b" / "refactor.robot"
        target_a.parent.mkdir(parents=True, exist_ok=True)
        target_b.parent.mkdir(parents=True, exist_ok=True)
        target_a.write_text(original, encoding="utf-8")
        target_b.write_text(original, encoding="utf-8")
        workflow_calls = 0
        _emit_event(writer, "epic3-refactor-proof", "scenario-start", "Running refactor suite reference scenario.", {"scenario": "refactor-suite"})
        start_a = perf_counter()
        result_a = refactor_existing_artifact(
            str(target_a),
            rename_to="Updated Name",
            documentation="Updated benchmark suite.",
            replace=["Log    ${message}=Log To Console    ${message}"],
        )
        elapsed_a = perf_counter() - start_a
        workflow_calls += 1
        start_b = perf_counter()
        result_b = refactor_existing_artifact(
            str(target_b),
            rename_to="Updated Name",
            documentation="Updated benchmark suite.",
            replace=["Log    ${message}=Log To Console    ${message}"],
        )
        elapsed_b = perf_counter() - start_b
        elapsed_ms = int(((elapsed_a + elapsed_b) / 2) * 1000)
        deterministic = (
            result_a.ok == result_b.ok
            and result_a.artifact.updated_content == result_b.artifact.updated_content
            and _canonicalize_text(result_a.artifact.diff, str(target_a), str(target_b))
            == _canonicalize_text(result_b.artifact.diff, str(target_a), str(target_b))
            and [item.model_dump(mode="json") for item in result_a.changes] == [item.model_dump(mode="json") for item in result_b.changes]
            and _canonicalize_json(result_a.run_verification.model_dump(mode="json"), str(target_a), str(target_b))
            == _canonicalize_json(result_b.run_verification.model_dump(mode="json"), str(target_a), str(target_b))
        )
        scenario = BenchmarkScenarioResult(
            scenario_id="refactor-suite",
            workflow="refactor",
            target_kind="suite",
            setup_friction=1,
            tool_call_count=workflow_calls,
            failed_tool_call_rate=1.0 if not result_a.ok else 0.0,
            validation_success=result_a.validation.ok,
            runnable_status=result_a.run_verification.status,
            first_pass_runnable=result_a.run_verification.status == "passed",
            human_correction_rate=0.0 if not result_a.manual_follow_up else 1.0,
            correction_burden=len(result_a.correction_path) + len(result_a.manual_follow_up),
            input_context_size=_count_context_items(["Updated Name"], ["Updated benchmark suite."], ["Log    ${message}=Log To Console    ${message}"]),
            deterministic=deterministic,
            elapsed_ms=elapsed_ms,
            notes="Targeted deterministic refactor for an existing suite.",
        )
        _emit_event(
            writer,
            "epic3-refactor-proof",
            "scenario-complete",
            "Completed refactor suite reference scenario.",
            {
                "scenario": scenario.scenario_id,
                "runnable_status": scenario.runnable_status,
                "deterministic": str(scenario.deterministic).lower(),
                "correction_burden": str(scenario.correction_burden),
            },
        )
        return scenario


def _run_regenerate_resource_scenario(writer: JsonlEventWriter | None) -> BenchmarkScenarioResult:
    with TemporaryDirectory() as tmpdir:
        original = (
            "*** Keywords ***\n"
            "Example Keyword\n"
            "    Log    hello\n"
        )
        target_a = Path(tmpdir) / "run_a" / "helpers.resource"
        target_b = Path(tmpdir) / "run_b" / "helpers.resource"
        target_a.parent.mkdir(parents=True, exist_ok=True)
        target_b.parent.mkdir(parents=True, exist_ok=True)
        target_a.write_text(original, encoding="utf-8")
        target_b.write_text(original, encoding="utf-8")
        workflow_calls = 0
        _emit_event(writer, "epic3-regenerate-proof", "scenario-start", "Running regenerate resource reference scenario.", {"scenario": "regenerate-resource"})
        start_a = perf_counter()
        result_a = regenerate_existing_artifact(
            str(target_a),
            steps=["Log    updated"],
            assertions=[],
        )
        elapsed_a = perf_counter() - start_a
        workflow_calls += 1
        start_b = perf_counter()
        result_b = regenerate_existing_artifact(
            str(target_b),
            steps=["Log    updated"],
            assertions=[],
        )
        elapsed_b = perf_counter() - start_b
        elapsed_ms = int(((elapsed_a + elapsed_b) / 2) * 1000)
        deterministic = (
            result_a.ok == result_b.ok
            and result_a.artifact.updated_content == result_b.artifact.updated_content
            and _canonicalize_text(result_a.artifact.diff, str(target_a), str(target_b))
            == _canonicalize_text(result_b.artifact.diff, str(target_a), str(target_b))
            and [item.model_dump(mode="json") for item in result_a.changes] == [item.model_dump(mode="json") for item in result_b.changes]
            and _canonicalize_json(result_a.manual_follow_up, str(target_a), str(target_b))
            == _canonicalize_json(result_b.manual_follow_up, str(target_a), str(target_b))
        )
        scenario = BenchmarkScenarioResult(
            scenario_id="regenerate-resource",
            workflow="regenerate",
            target_kind="resource",
            setup_friction=1,
            tool_call_count=workflow_calls,
            failed_tool_call_rate=1.0 if not result_a.ok else 0.0,
            validation_success=result_a.validation.ok,
            runnable_status=result_a.run_verification.status,
            first_pass_runnable=None,
            human_correction_rate=0.0,
            correction_burden=0,
            input_context_size=_count_context_items(["Log    updated"]),
            deterministic=deterministic,
            elapsed_ms=elapsed_ms,
            notes="Regenerate path for an existing resource with explicit manual verification follow-up that does not count as correction burden.",
        )
        _emit_event(
            writer,
            "epic3-regenerate-proof",
            "scenario-complete",
            "Completed regenerate resource reference scenario.",
            {
                "scenario": scenario.scenario_id,
                "runnable_status": scenario.runnable_status,
                "deterministic": str(scenario.deterministic).lower(),
                "correction_burden": str(scenario.correction_burden),
            },
        )
        return scenario


def write_epic3_benchmark_pack(output_path: Path, event_log_path: Path | None = None) -> Epic3BenchmarkReport:
    writer = JsonlEventWriter(event_log_path) if event_log_path is not None else None
    scenarios = [
        _run_generation_scenario(writer),
        _run_refactor_suite_scenario(writer),
        _run_regenerate_resource_scenario(writer),
    ]
    report = Epic3BenchmarkReport(scenarios=scenarios, summary=_summarize(scenarios))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report.model_dump(mode="json"), indent=2, sort_keys=True), encoding="utf-8")
    return report
