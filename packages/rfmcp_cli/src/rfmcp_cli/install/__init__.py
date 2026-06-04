"""rfmcp install/onboarding subcommands: init, doctor, skills.

Three commands that turn ``pip install rfmcp-cli`` into a working agent setup:

- ``rfmcp init <client>`` — write a ready-to-paste MCP-server snippet (or full
  merged config) for the named agent host (claude-code, claude-desktop, cursor,
  kilo, codex). ``--print`` always works; ``--write`` actually edits the host's
  config file with an idempotent merge.
- ``rfmcp doctor`` — diagnose the local install: Python / uv / Robot Framework
  versions, Browser Library + ``rfbrowser init``, local policy file, and which
  agent hosts have rfmcp configured.
- ``rfmcp skills`` (list / install / uninstall / which) — copy or symlink the
  bundled skills under ``assets/skills/`` into the agent host's skill directory.
"""

from __future__ import annotations

import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any

import typer


SUPPORTED_CLIENTS = ("claude-code", "claude-desktop", "cursor", "kilo", "codex")

SERVER_KEY = "rfmcp"


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def _assets_dir() -> Path:
    """Return the bundled assets/skills directory.

    Prefer the source tree's ``assets/skills/`` when running from a checkout
    (walk up from this file until ``assets/skills/`` exists); fall back to the
    wheel's ``rfmcp_cli/_assets/skills/`` once we start shipping it inside the
    package itself.
    """
    here = Path(__file__).resolve()
    for parent in (here.parent, *here.parents):
        candidate = parent / "assets" / "skills"
        if candidate.is_dir():
            return candidate
    return here.parent / "_assets" / "skills"


def _claude_code_skills_dir() -> Path:
    return Path.home() / ".claude" / "skills"


@dataclass(frozen=True)
class ClientConfigSpec:
    """Where this client stores its MCP config + which on-disk format it uses."""

    name: str
    config_path: Path
    fmt: str  # "json" | "toml"
    server_key: str = SERVER_KEY
    notes: str = ""


def _client_config_spec(name: str) -> ClientConfigSpec:
    home = Path.home()
    if name == "claude-code":
        # User-scoped config; Claude Code also honors project-local .mcp.json.
        return ClientConfigSpec(
            name=name,
            config_path=home / ".claude.json",
            fmt="json",
            notes="Use --scope project to write .mcp.json in the current directory instead.",
        )
    if name == "claude-desktop":
        if sys.platform == "darwin":
            path = home / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
        elif sys.platform == "win32":
            appdata = os.environ.get("APPDATA", str(home))
            path = Path(appdata) / "Claude" / "claude_desktop_config.json"
        else:
            path = home / ".config" / "Claude" / "claude_desktop_config.json"
        return ClientConfigSpec(name=name, config_path=path, fmt="json")
    if name == "cursor":
        # User-scoped default; --scope project writes .cursor/mcp.json in the cwd.
        return ClientConfigSpec(
            name=name,
            config_path=home / ".cursor" / "mcp.json",
            fmt="json",
            notes="Use --scope project to write .cursor/mcp.json in the current directory instead.",
        )
    if name == "kilo":
        return ClientConfigSpec(name=name, config_path=home / ".kilo" / "mcp.json", fmt="json")
    if name == "codex":
        return ClientConfigSpec(name=name, config_path=home / ".codex" / "config.toml", fmt="toml")
    raise typer.BadParameter(
        f"Unsupported client '{name}'. Choose from: {', '.join(SUPPORTED_CLIENTS)}."
    )


def _server_block() -> dict[str, Any]:
    """Canonical rfmcp MCP-server block used across all JSON clients."""
    return {
        "command": "rfmcp",
        "args": ["serve"],
    }


def _scope_override_path(client_name: str, scope: str) -> Path | None:
    """When the user asks for project-scope, return the project-local path."""
    if scope != "project":
        return None
    cwd = Path.cwd()
    if client_name == "claude-code":
        return cwd / ".mcp.json"
    if client_name == "cursor":
        return cwd / ".cursor" / "mcp.json"
    return None


# ---------------------------------------------------------------------------
# Config writers — JSON
# ---------------------------------------------------------------------------


def _merge_json_mcp_server(config_path: Path, server_key: str, server_block: dict[str, Any]) -> dict[str, Any]:
    """Read existing JSON config (or {} if absent), add/replace the rfmcp server, return the merged dict."""
    if config_path.is_file():
        try:
            existing = json.loads(config_path.read_text(encoding="utf-8") or "{}")
        except json.JSONDecodeError as exc:
            raise typer.BadParameter(
                f"Existing config at {config_path} is not valid JSON ({exc}). "
                "Repair it or use --print to inspect the snippet before retrying."
            )
    else:
        existing = {}
    if not isinstance(existing, dict):
        raise typer.BadParameter(
            f"Existing config at {config_path} does not contain a JSON object."
        )
    servers = existing.setdefault("mcpServers", {})
    if not isinstance(servers, dict):
        raise typer.BadParameter(
            f"Existing 'mcpServers' field at {config_path} is not an object."
        )
    servers[server_key] = server_block
    return existing


def _write_json_with_backup(config_path: Path, data: dict[str, Any]) -> Path | None:
    """Write JSON to ``config_path``, creating parents and a ``.bak`` of any prior file."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    backup: Path | None = None
    if config_path.is_file():
        backup = config_path.with_suffix(config_path.suffix + ".bak")
        backup.write_text(config_path.read_text(encoding="utf-8"), encoding="utf-8")
    config_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return backup


def _render_codex_toml_block() -> str:
    return (
        "[mcp_servers.rfmcp]\n"
        'command = "rfmcp"\n'
        'args = ["serve"]\n'
    )


def _merge_codex_toml(config_path: Path) -> str:
    """Return the merged TOML body with the rfmcp block ensured present."""
    new_block = _render_codex_toml_block()
    if not config_path.is_file():
        return new_block
    existing = config_path.read_text(encoding="utf-8")
    if "[mcp_servers.rfmcp]" in existing:
        # Already configured; leave the file alone.
        return existing
    sep = "" if existing.endswith("\n") else "\n"
    return f"{existing}{sep}\n{new_block}"


def _write_text_with_backup(config_path: Path, body: str) -> Path | None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    backup: Path | None = None
    if config_path.is_file():
        backup = config_path.with_suffix(config_path.suffix + ".bak")
        backup.write_text(config_path.read_text(encoding="utf-8"), encoding="utf-8")
    config_path.write_text(body, encoding="utf-8")
    return backup


# ---------------------------------------------------------------------------
# init command
# ---------------------------------------------------------------------------


def init_command(
    client: Annotated[
        str,
        typer.Argument(
            help=f"Target MCP client. One of: {', '.join(SUPPORTED_CLIENTS)}.",
        ),
    ],
    write: Annotated[
        bool,
        typer.Option(
            "--write",
            help="Actually write the config to disk (with a .bak of any existing file). "
            "Without this flag, init prints the snippet without touching anything.",
        ),
    ] = False,
    scope: Annotated[
        str,
        typer.Option(
            "--scope",
            help="'user' (default; the host's user-level config) or 'project' (claude-code -> "
            "./.mcp.json, cursor -> ./.cursor/mcp.json). Other clients ignore --scope.",
        ),
    ] = "user",
) -> None:
    """Generate (and optionally write) an rfmcp MCP-server entry for the named agent host.

    Examples:

      rfmcp init claude-code            # print the snippet for ~/.claude.json
      rfmcp init claude-code --write    # merge it into ~/.claude.json (with .bak)
      rfmcp init cursor --scope project --write   # write ./.cursor/mcp.json
      rfmcp init codex --write          # append [mcp_servers.rfmcp] to ~/.codex/config.toml
    """

    if client not in SUPPORTED_CLIENTS:
        typer.echo(
            f"Unsupported client '{client}'. Choose from: {', '.join(SUPPORTED_CLIENTS)}.",
            err=True,
        )
        raise typer.Exit(code=2)

    spec = _client_config_spec(client)
    config_path = _scope_override_path(client, scope) or spec.config_path

    if spec.fmt == "json":
        if write:
            merged = _merge_json_mcp_server(config_path, spec.server_key, _server_block())
            backup = _write_json_with_backup(config_path, merged)
            typer.echo(f"Wrote {config_path}")
            if backup is not None:
                typer.echo(f"Previous content saved to {backup}")
            if spec.notes:
                typer.echo(spec.notes)
            return
        # Print the minimal snippet the user has to paste — not their whole
        # existing config. The structural wrapper (mcpServers) is included so
        # the snippet is self-describing for users coming from a blank file.
        snippet = {"mcpServers": {spec.server_key: _server_block()}}
        typer.echo(f"# Target: {config_path}")
        typer.echo("# Merge the snippet below under 'mcpServers' (or use --write to do it for you).")
        if spec.notes:
            typer.echo(f"# {spec.notes}")
        typer.echo(json.dumps(snippet, indent=2))
        return

    if spec.fmt == "toml":
        if write:
            merged_body = _merge_codex_toml(config_path)
            backup = _write_text_with_backup(config_path, merged_body)
            typer.echo(f"Wrote {config_path}")
            if backup is not None:
                typer.echo(f"Previous content saved to {backup}")
            return
        typer.echo(f"# Target: {config_path}")
        typer.echo("# Append the block below to the file (or use --write to do it for you).")
        typer.echo(_render_codex_toml_block())
        return

    typer.echo(f"Unknown config format for client '{client}'.", err=True)
    raise typer.Exit(code=2)


# ---------------------------------------------------------------------------
# doctor command
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str
    fix: str | None = None


def _check_python() -> CheckResult:
    version = sys.version_info
    ok = (version.major, version.minor) >= (3, 11) and (version.major, version.minor) < (3, 14)
    detail = f"Python {version.major}.{version.minor}.{version.micro} on {platform.system().lower()}"
    fix = None if ok else "Install Python 3.11, 3.12, or 3.13 (the supported range)."
    return CheckResult("python_version", ok, detail, fix)


def _check_uv() -> CheckResult:
    uv = shutil.which("uv")
    if not uv:
        return CheckResult(
            "uv",
            False,
            "uv not found on PATH",
            "Install uv from https://docs.astral.sh/uv/ (`curl -LsSf https://astral.sh/uv/install.sh | sh`).",
        )
    try:
        out = subprocess.run([uv, "--version"], capture_output=True, text=True, check=True, timeout=10)
        return CheckResult("uv", True, out.stdout.strip() or "uv present")
    except subprocess.SubprocessError as exc:
        return CheckResult("uv", False, f"uv invocation failed: {exc}", "Reinstall uv.")


def _check_robotframework() -> CheckResult:
    try:
        import robot  # type: ignore  # noqa: F401

        from robot.version import VERSION as rf_version  # type: ignore
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            "robotframework",
            False,
            f"robotframework not importable: {exc}",
            "Reinstall with `pip install robotframework`.",
        )
    return CheckResult("robotframework", True, f"robotframework {rf_version}")


def _check_browser_library() -> CheckResult:
    if importlib.util.find_spec("Browser") is None:
        return CheckResult(
            "robotframework-browser",
            False,
            "Browser library not installed",
            "Install with `pip install rfmcp-cli[web]` (or `uv sync --group web`) and then run `rfmcp doctor` again.",
        )
    return CheckResult("robotframework-browser", True, "Browser library importable")


def _check_rfbrowser_init() -> CheckResult:
    if importlib.util.find_spec("Browser") is None:
        return CheckResult(
            "rfbrowser_init",
            True,
            "skipped (Browser library not installed)",
        )
    try:
        import Browser  # type: ignore

        node_modules = Path(Browser.__file__).resolve().parent / "wrapper" / "node_modules"
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            "rfbrowser_init",
            False,
            f"could not locate Browser package directory: {exc}",
            "Reinstall robotframework-browser and rerun.",
        )
    if node_modules.is_dir():
        return CheckResult("rfbrowser_init", True, f"node_modules present at {node_modules}")
    return CheckResult(
        "rfbrowser_init",
        False,
        f"node_modules missing at {node_modules}",
        "Run `rfbrowser init` (installed by robotframework-browser) to install the Playwright runtime.",
    )


def _check_local_policy() -> CheckResult:
    """The loader reads assets/policy/local-defaults.json. Try to actually load
    it via the canonical entry point so the check matches what the runtime does."""
    try:
        from rfmcp_core.policy.loader import DEFAULT_POLICY_PATH, load_local_policy_defaults

        load_local_policy_defaults()
        return CheckResult("local_policy", True, f"{DEFAULT_POLICY_PATH}")
    except Exception as exc:  # noqa: BLE001
        return CheckResult(
            "local_policy",
            False,
            f"failed to load policy: {exc}",
            "Run from a checkout (assets/policy/local-defaults.json) or reinstall rfmcp-core.",
        )


def _check_client_config(client: str) -> CheckResult:
    spec = _client_config_spec(client)
    if not spec.config_path.is_file():
        return CheckResult(
            f"client:{client}",
            False,
            f"no config at {spec.config_path}",
            f"Run `rfmcp init {client} --write` to add the rfmcp entry.",
        )
    try:
        if spec.fmt == "json":
            data = json.loads(spec.config_path.read_text(encoding="utf-8") or "{}")
            has_entry = (
                isinstance(data, dict)
                and isinstance(data.get("mcpServers"), dict)
                and SERVER_KEY in data["mcpServers"]
            )
        else:  # toml
            has_entry = "[mcp_servers.rfmcp]" in spec.config_path.read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError) as exc:
        return CheckResult(
            f"client:{client}",
            False,
            f"could not read {spec.config_path}: {exc}",
            f"Repair the file or rerun `rfmcp init {client} --write`.",
        )
    if has_entry:
        return CheckResult(f"client:{client}", True, f"rfmcp registered in {spec.config_path}")
    return CheckResult(
        f"client:{client}",
        False,
        f"present at {spec.config_path} but no rfmcp entry",
        f"Run `rfmcp init {client} --write` to add the rfmcp entry.",
    )


def doctor_command(
    clients: Annotated[
        list[str] | None,
        typer.Option(
            "--client",
            "-c",
            help=(
                "Also check whether this MCP client has an rfmcp entry. Can be passed "
                f"multiple times. Supported: {', '.join(SUPPORTED_CLIENTS)}."
            ),
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Emit results as JSON for scripting."),
    ] = False,
) -> None:
    """Diagnose the local rfmcp installation. Exits non-zero if any required check fails."""

    checks: list[CheckResult] = [
        _check_python(),
        _check_uv(),
        _check_robotframework(),
        _check_browser_library(),
        _check_rfbrowser_init(),
        _check_local_policy(),
    ]
    for client in clients or []:
        checks.append(_check_client_config(client))

    if json_output:
        typer.echo(
            json.dumps(
                {
                    "ok": all(c.ok for c in checks),
                    "checks": [
                        {"name": c.name, "ok": c.ok, "detail": c.detail, "fix": c.fix}
                        for c in checks
                    ],
                },
                indent=2,
            )
        )
    else:
        for check in checks:
            mark = "OK  " if check.ok else "FAIL"
            typer.echo(f"  [{mark}] {check.name:<28} {check.detail}")
            if not check.ok and check.fix:
                typer.echo(f"           fix: {check.fix}")

    if not all(c.ok for c in checks):
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# skills sub-app
# ---------------------------------------------------------------------------


skills_app = typer.Typer(
    help="List, install, or remove the bundled agent skills.",
    no_args_is_help=True,
)


def _discover_skills() -> list[Path]:
    base = _assets_dir()
    if not base.is_dir():
        return []
    return sorted(p for p in base.iterdir() if p.is_dir() and not p.name.startswith("."))


@skills_app.command("list")
def skills_list() -> None:
    """List bundled skills + whether each is installed in Claude Code's skill directory."""
    skill_dirs = _discover_skills()
    if not skill_dirs:
        typer.echo("No bundled skills found.")
        return
    target_root = _claude_code_skills_dir()
    for skill in skill_dirs:
        installed = (target_root / skill.name).is_dir()
        marker = "[installed]" if installed else "[available]"
        readme = skill / "README.md"
        first_line = ""
        if readme.is_file():
            for line in readme.read_text(encoding="utf-8").splitlines():
                if line.strip() and not line.startswith("#"):
                    first_line = line.strip()
                    break
        typer.echo(f"  {marker} {skill.name:<40} {first_line[:80]}")


@skills_app.command("install")
def skills_install(
    skill_id: Annotated[str, typer.Argument(help="Skill directory name under assets/skills/.")],
    target: Annotated[
        Path | None,
        typer.Option(
            "--target",
            help="Override the install destination. Defaults to ~/.claude/skills/<skill_id>/.",
        ),
    ] = None,
    symlink: Annotated[
        bool,
        typer.Option("--symlink", help="Symlink the skill instead of copying. Useful in dev mode."),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", help="Replace an existing install at the destination."),
    ] = False,
) -> None:
    """Install a bundled skill into the agent host's skill directory."""
    source = _assets_dir() / skill_id
    if not source.is_dir():
        typer.echo(f"Skill '{skill_id}' not found under {_assets_dir()}.", err=True)
        raise typer.Exit(code=2)
    destination = target if target else _claude_code_skills_dir() / skill_id
    if destination.exists():
        if not force:
            typer.echo(
                f"{destination} already exists. Use --force to replace it.",
                err=True,
            )
            raise typer.Exit(code=2)
        if destination.is_symlink() or destination.is_file():
            destination.unlink()
        else:
            shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if symlink:
        destination.symlink_to(source.resolve(), target_is_directory=True)
        typer.echo(f"Symlinked {destination} -> {source.resolve()}")
    else:
        shutil.copytree(source, destination)
        typer.echo(f"Copied {source} -> {destination}")


@skills_app.command("uninstall")
def skills_uninstall(
    skill_id: Annotated[str, typer.Argument(help="Skill directory name.")],
    target: Annotated[
        Path | None,
        typer.Option("--target", help="Override install location."),
    ] = None,
) -> None:
    """Remove an installed skill from the agent host's skill directory."""
    destination = target if target else _claude_code_skills_dir() / skill_id
    if not destination.exists():
        typer.echo(f"Nothing to uninstall at {destination}.", err=True)
        raise typer.Exit(code=1)
    if destination.is_symlink() or destination.is_file():
        destination.unlink()
    else:
        shutil.rmtree(destination)
    typer.echo(f"Removed {destination}")


@skills_app.command("which")
def skills_which(skill_id: Annotated[str, typer.Argument(help="Skill directory name.")]) -> None:
    """Show source + (if installed) destination for a skill."""
    source = _assets_dir() / skill_id
    destination = _claude_code_skills_dir() / skill_id
    typer.echo(f"source: {source if source.is_dir() else '(not found)'}")
    typer.echo(f"install: {destination if destination.exists() else '(not installed)'}")
