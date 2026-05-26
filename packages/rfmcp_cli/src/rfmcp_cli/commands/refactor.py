from __future__ import annotations

from pathlib import Path

import typer

from rfmcp_cli.presenters.human import render_refactor_result
from rfmcp_cli.presenters.structured import render_refactor_result_json
from rfmcp_cli.workflows.refactor import refactor_existing_artifact


def refactor_command(
    target: Path = typer.Argument(..., exists=False),
    rename_to: str | None = typer.Option(None, "--rename-to", help="Rename the first test case or keyword."),
    documentation: str | None = typer.Option(None, "--documentation", help="Replace the top-level documentation."),
    replace: list[str] | None = typer.Option(None, "--replace", help="Replace an exact body line using OLD=NEW."),
    add_step: list[str] | None = typer.Option(None, "--add-step", help="Append a step to the existing body."),
    add_assertion: list[str] | None = typer.Option(None, "--add-assertion", help="Append an assertion to the existing body."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    result = refactor_existing_artifact(
        str(target),
        rename_to=rename_to,
        documentation=documentation,
        replace=replace,
        steps=add_step,
        assertions=add_assertion,
    )
    output = render_refactor_result_json(result) if as_json else render_refactor_result(result)
    typer.echo(output)
    raise typer.Exit(code=0 if result.ok else 1)
