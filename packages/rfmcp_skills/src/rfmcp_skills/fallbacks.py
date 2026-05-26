from __future__ import annotations

import shlex

BROWSER_LIBRARY_FLAGSHIP_REPAIR_ID = "browser-library-flagship-repair"
RUNNABLE_TEST_GENERATION_ID = "runnable-test-generation"
EXISTING_ARTIFACT_REFACTOR_ID = "existing-artifact-refactor"

FALLBACK_COMMAND_TEMPLATES_BY_SKILL_ID: dict[str, tuple[str, ...]] = {
    BROWSER_LIBRARY_FLAGSHIP_REPAIR_ID: (
        "rfmcp repair-diagnostics {target} --failure-message {failure_message} --json",
        "rfmcp repair-hints {target} --failure-message {failure_message} --json",
        "rfmcp validate {target} --json",
    ),
    RUNNABLE_TEST_GENERATION_ID: (
        "rfmcp ground {query} --json",
        "rfmcp scaffold-suite {target} --library {library} --json",
        "rfmcp generate {target} --task {task} --step {step} --assertion {assertion} --json",
    ),
    EXISTING_ARTIFACT_REFACTOR_ID: (
        "rfmcp refactor {target} --replace {replace} --json",
        "rfmcp regenerate {target} --step {step} --assertion {assertion} --json",
        "rfmcp validate {target} --json",
    ),
}

FALLBACK_COMMANDS_BY_SKILL_ID: dict[str, tuple[str, ...]] = {
    BROWSER_LIBRARY_FLAGSHIP_REPAIR_ID: (
        "rfmcp repair-diagnostics <target.robot> --failure-message '<failure message>' --json",
        "rfmcp repair-hints <target.robot> --failure-message '<failure message>' --json",
        "rfmcp validate <target.robot> --json",
    ),
    RUNNABLE_TEST_GENERATION_ID: (
        "rfmcp ground '<keyword-or-library-query>' --json",
        "rfmcp scaffold-suite <target.robot> --library <LibraryName> --json",
        "rfmcp generate <target.robot> --task '<task>' --step '<step>' --assertion '<assertion>' --json",
    ),
    EXISTING_ARTIFACT_REFACTOR_ID: (
        "rfmcp refactor <target.robot> --replace 'OLD=NEW' --json",
        "rfmcp regenerate <target.robot> --step '<step>' --assertion '<assertion>' --json",
        "rfmcp validate <target.robot> --json",
    ),
}


def fallback_commands_for(skill_id: str) -> tuple[str, ...]:
    return FALLBACK_COMMANDS_BY_SKILL_ID.get(skill_id, ())


def render_fallback_commands(
    skill_id: str,
    *,
    target: str,
    failure_message: str | None = None,
    **placeholders: str,
) -> tuple[str, ...]:
    values: dict[str, str] = {
        "target": shlex.quote(target),
        "failure_message": shlex.quote(failure_message or ""),
    }
    for key, value in placeholders.items():
        values[key] = shlex.quote(value)

    class _SafeValues(dict[str, str]):
        def __missing__(self, key: str) -> str:
            return f"<{key}>"

    return tuple(
        command.format_map(_SafeValues(values))
        for command in FALLBACK_COMMAND_TEMPLATES_BY_SKILL_ID.get(skill_id, ())
    )
