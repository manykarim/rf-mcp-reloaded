from __future__ import annotations

import typer

from rfmcp_cli.commands.repair_diagnostics import repair_diagnostics_command
from rfmcp_cli.commands.repair_hints import repair_hints_command
from rfmcp_cli.commands.validate import validate_command


app = typer.Typer(help="Robot Framework MCP and workflow CLI.", no_args_is_help=True)


@app.callback()
def main_callback() -> None:
    """Root CLI callback to preserve subcommand mode."""


app.command("validate")(validate_command)
app.command("repair-diagnostics")(repair_diagnostics_command)
app.command("repair-hints")(repair_hints_command)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
