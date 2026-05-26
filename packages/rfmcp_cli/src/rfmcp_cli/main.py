from __future__ import annotations

import typer

from rfmcp_cli.commands.generate import generate_command
from rfmcp_cli.commands.ground import ground_command
from rfmcp_cli.commands.refactor import refactor_command
from rfmcp_cli.commands.regenerate import regenerate_command
from rfmcp_cli.commands.repair_diagnostics import repair_diagnostics_command
from rfmcp_cli.commands.repair_hints import repair_hints_command
from rfmcp_cli.commands.scaffold_resource import scaffold_resource_command
from rfmcp_cli.commands.scaffold_suite import scaffold_suite_command
from rfmcp_cli.commands.validate import validate_command


app = typer.Typer(help="Robot Framework MCP and workflow CLI.", no_args_is_help=True)


@app.callback()
def main_callback() -> None:
    """Root CLI callback to preserve subcommand mode."""


app.command("validate")(validate_command)
app.command("generate")(generate_command)
app.command("ground")(ground_command)
app.command("refactor")(refactor_command)
app.command("regenerate")(regenerate_command)
app.command("scaffold-suite")(scaffold_suite_command)
app.command("scaffold-resource")(scaffold_resource_command)
app.command("repair-diagnostics")(repair_diagnostics_command)
app.command("repair-hints")(repair_hints_command)


def main() -> None:
    app()


if __name__ == "__main__":
    main()
