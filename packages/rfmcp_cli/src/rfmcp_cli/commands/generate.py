from __future__ import annotations

from pathlib import Path

import typer

from rfmcp_cli.presenters.human import render_generation_result
from rfmcp_cli.presenters.structured import render_generation_result_json
from rfmcp_cli.workflows.generation import generate_suite_artifact


def generate_command(
    target: Path = typer.Argument(..., exists=False),
    task: list[str] | None = typer.Option(None, "--task", help="Requested operator task to fulfill."),
    step: list[str] | None = typer.Option(None, "--step", help="Robot step to include in the generated test body."),
    assertion: list[str] | None = typer.Option(None, "--assertion", help="Robot assertion to include in the generated test body."),
    suite_name: str | None = typer.Option(None, "--suite-name", help="Override the scaffolded suite display name."),
    test_case_name: str = typer.Option("Generated Test", "--test-case-name", help="Name for the generated test case."),
    library: list[str] | None = typer.Option(None, "--library", help="Robot Framework libraries to import."),
    resource: list[str] | None = typer.Option(None, "--resource", help="Robot Framework resource files to import."),
    documentation: str | None = typer.Option(None, "--documentation", help="Top-level documentation string."),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing target."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    result = generate_suite_artifact(
        str(target),
        tasks=task,
        steps=step,
        assertions=assertion,
        suite_name=suite_name,
        test_case_name=test_case_name,
        libraries=library,
        resources=resource,
        documentation=documentation,
        force=force,
    )
    output = render_generation_result_json(result) if as_json else render_generation_result(result)
    typer.echo(output)
    raise typer.Exit(code=0 if result.ok else 1)
