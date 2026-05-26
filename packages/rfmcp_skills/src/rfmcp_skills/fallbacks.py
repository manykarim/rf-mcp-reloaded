from __future__ import annotations

import shlex

BROWSER_LIBRARY_FLAGSHIP_REPAIR_ID = "browser-library-flagship-repair"

FALLBACK_COMMAND_TEMPLATES_BY_SKILL_ID: dict[str, tuple[str, ...]] = {
    BROWSER_LIBRARY_FLAGSHIP_REPAIR_ID: (
        "rfmcp repair-diagnostics {target} --failure-message {failure_message} --json",
        "rfmcp repair-hints {target} --failure-message {failure_message} --json",
        "rfmcp validate {target} --json",
    )
}

FALLBACK_COMMANDS_BY_SKILL_ID: dict[str, tuple[str, ...]] = {
    BROWSER_LIBRARY_FLAGSHIP_REPAIR_ID: (
        "rfmcp repair-diagnostics <target.robot> --failure-message '<failure message>' --json",
        "rfmcp repair-hints <target.robot> --failure-message '<failure message>' --json",
        "rfmcp validate <target.robot> --json",
    )
}


def fallback_commands_for(skill_id: str) -> tuple[str, ...]:
    return FALLBACK_COMMANDS_BY_SKILL_ID.get(skill_id, ())


def render_fallback_commands(
    skill_id: str,
    *,
    target: str,
    failure_message: str | None = None,
) -> tuple[str, ...]:
    return tuple(
        command.format(
            target=shlex.quote(target),
            failure_message=shlex.quote(failure_message or ""),
        )
        for command in FALLBACK_COMMAND_TEMPLATES_BY_SKILL_ID.get(skill_id, ())
    )
