from __future__ import annotations

from pathlib import Path

import typer

from rfmcp_cli.presenters.human import render_scaffold_result
from rfmcp_cli.presenters.structured import render_scaffold_result_json
from rfmcp_cli.workflows.grounding import scaffold_resource


def scaffold_resource_command(
    target: Path = typer.Argument(..., exists=False),
    keyword_name: str = typer.Option("Example Keyword", "--keyword-name", help="Name for the initial keyword."),
    documentation: str | None = typer.Option(None, "--documentation", help="Top-level documentation string."),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing target."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    result = scaffold_resource(
        str(target),
        keyword_name=keyword_name,
        documentation=documentation,
        force=force,
    )
    output = render_scaffold_result_json(result) if as_json else render_scaffold_result(result)
    typer.echo(output)
    raise typer.Exit(code=0 if result.ok else 1)
