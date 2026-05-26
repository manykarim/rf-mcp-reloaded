from __future__ import annotations

from pathlib import Path

import typer

from rfmcp_cli.presenters.human import render_refactor_result
from rfmcp_cli.presenters.structured import render_refactor_result_json
from rfmcp_cli.workflows.refactor import regenerate_existing_artifact


def regenerate_command(
    target: Path = typer.Argument(..., exists=False),
    rename_to: str | None = typer.Option(None, "--rename-to", help="Rename the first test case or keyword."),
    documentation: str | None = typer.Option(None, "--documentation", help="Replace the top-level documentation."),
    step: list[str] | None = typer.Option(None, "--step", help="Replace the body with these steps."),
    assertion: list[str] | None = typer.Option(None, "--assertion", help="Replace the body with these assertions."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    result = regenerate_existing_artifact(
        str(target),
        rename_to=rename_to,
        documentation=documentation,
        steps=step,
        assertions=assertion,
    )
    output = render_refactor_result_json(result) if as_json else render_refactor_result(result)
    typer.echo(output)
    raise typer.Exit(code=0 if result.ok else 1)
