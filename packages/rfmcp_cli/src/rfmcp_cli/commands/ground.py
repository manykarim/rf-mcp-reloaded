from __future__ import annotations

import typer

from rfmcp_cli.presenters.human import render_grounding_result
from rfmcp_cli.presenters.structured import render_grounding_result_json
from rfmcp_cli.workflows.grounding import run_grounding


def ground_command(
    query: str = typer.Argument(..., help="Keyword or library query to ground."),
    library: list[str] | None = typer.Option(None, "--library", help="Limit grounding to specific library import names."),
    limit: int = typer.Option(10, "--limit", min=1, max=50, help="Maximum keyword matches to return."),
    as_json: bool = typer.Option(False, "--json", help="Emit machine-readable JSON output."),
) -> None:
    result = run_grounding(query, libraries=library, limit=limit)
    output = render_grounding_result_json(result) if as_json else render_grounding_result(result)
    typer.echo(output)
    raise typer.Exit(code=0 if result.ok else 1)
