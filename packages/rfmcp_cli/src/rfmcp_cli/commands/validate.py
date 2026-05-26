from __future__ import annotations

from pathlib import Path

import typer

from rfmcp_core.contracts import (
    ErrorEnvelope,
    ProvenanceKind,
    ProvenanceRecord,
    Severity,
    ValidationResult,
)
from rfmcp_core.robot.validation import validate_robot_artifact
from rfmcp_core.utils.bootstrap import verify_environment
from rfmcp_cli.presenters.human import render_validation_result
from rfmcp_cli.presenters.structured import render_validation_result_json


def run_validate(target: str) -> ValidationResult:
    bootstrap_errors = verify_environment()
    if bootstrap_errors:
        first_error = bootstrap_errors[0]
        return ValidationResult(
            ok=False,
            target=target,
            error=ErrorEnvelope(
                code=f"bootstrap-{first_error.check}",
                message=f"Bootstrap baseline check failed: expected {first_error.expected}, got {first_error.actual}.",
                severity=Severity.ERROR,
                provenance=ProvenanceRecord(kind=ProvenanceKind.OBSERVED, source="bootstrap-env"),
                retryable=True,
                suggested_next_step=first_error.next_step,
                details={"check": first_error.check},
            ),
        )
    return validate_robot_artifact(target)


def validate_command(
    target: Path = typer.Argument(..., exists=False),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    result = run_validate(str(target))
    output = render_validation_result_json(result) if as_json else render_validation_result(result)
    typer.echo(output)
    raise typer.Exit(code=0 if result.ok else 1)
