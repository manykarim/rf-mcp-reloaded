from __future__ import annotations

from pathlib import Path

import typer

from rfmcp_cli.presenters.human import render_scaffold_result
from rfmcp_cli.presenters.structured import render_scaffold_result_json
from rfmcp_cli.workflows.grounding import scaffold_suite


def scaffold_suite_command(
    target: Path = typer.Argument(..., exists=False),
    suite_name: str | None = typer.Option(None, "--suite-name", help="Override the scaffolded suite display name."),
    test_case_name: str = typer.Option("Smoke Test", "--test-case-name", help="Name for the initial test case."),
    library: list[str] | None = typer.Option(None, "--library", help="Robot Framework libraries to import."),
    resource: list[str] | None = typer.Option(None, "--resource", help="Robot Framework resource files to import."),
    documentation: str | None = typer.Option(None, "--documentation", help="Top-level documentation string."),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing target."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    result = scaffold_suite(
        str(target),
        suite_name=suite_name,
        test_case_name=test_case_name,
        libraries=library,
        resources=resource,
        documentation=documentation,
        force=force,
    )
    output = render_scaffold_result_json(result) if as_json else render_scaffold_result(result)
    typer.echo(output)
    raise typer.Exit(code=0 if result.ok else 1)
