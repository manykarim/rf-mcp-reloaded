from __future__ import annotations

from pathlib import Path

import typer

from rfmcp_core.robot import run_repair_diagnostics
from rfmcp_cli.presenters.human import render_repair_diagnostic_result
from rfmcp_cli.presenters.structured import render_repair_diagnostic_result_json


def repair_diagnostics_command(
    target: Path = typer.Argument(..., exists=False),
    failure_message: str | None = typer.Option(None, "--failure-message", help="Observed failure message to classify."),
    error_code: str | None = typer.Option(None, "--error-code", help="Observed failure code to classify."),
    live_state_available: bool = typer.Option(
        True,
        "--live-state/--no-live-state",
        help="Whether live-state repair tools are available for this scenario.",
    ),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    result = run_repair_diagnostics(
        str(target),
        failure_message=failure_message,
        error_code=error_code,
        live_state_available=live_state_available,
    )
    output = render_repair_diagnostic_result_json(result) if as_json else render_repair_diagnostic_result(result)
    typer.echo(output)
    raise typer.Exit(code=0 if result.ok else 1)
