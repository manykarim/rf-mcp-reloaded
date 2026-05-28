"""Helpers for emitting Robot Framework suite text from step/keyword lines."""

from __future__ import annotations

import re

_CELL_SEPARATOR = re.compile(r"\s{2,}|\t")


def escape_comment_cells(line: str) -> str:
    """Escape a leading ``#`` in each Robot Framework data cell as ``\\#``.

    Robot Framework treats a data cell that begins with ``#`` as a comment, which
    silently drops CSS id selectors used as keyword arguments — e.g.
    ``Fill Text    #user-name    bob`` would parse as ``Fill Text`` with zero
    arguments. Generated suites must therefore escape such cells to ``\\#user-name``.

    Cells are split on Robot's data separator (two or more spaces, or a tab).
    Only a leading ``#`` is escaped (a ``#`` mid-value is literal), and a cell that
    is already escaped (starts with ``\\``) is left untouched.

    This is emit-side escaping: Robot's public ``robot.api`` parser cannot help here,
    because a leading-``#`` cell is swallowed as a comment by the lexer (so the
    intended cell is unrecoverable from a parse). The escaped output is validated
    against ``robot.api``'s own lexer in the test-suite instead.
    """

    cells = _CELL_SEPARATOR.split(line)
    return "    ".join(f"\\{cell}" if cell.startswith("#") else cell for cell in cells)


# Import keyword (normalized) -> the equivalent *** Settings *** declaration.
_IMPORT_SETTING = {
    "importlibrary": "Library",
    "importresource": "Resource",
    "importvariables": "Variables",
}


def _parse_keyword_call(line: str) -> tuple[bool, str, list[str]] | None:
    """Parse one body line into (has_assignment, keyword_name, args) using robot.api.

    Returns ``None`` for blanks, control structures, or unparseable lines.
    """

    text = line.strip()
    if not text:
        return None
    from robot.api import TestSuite

    try:
        suite = TestSuite.from_string(f"*** Test Cases ***\n_\n    {text}\n")
    except Exception:
        return None
    body = list(suite.tests[0].body) if suite.tests else []
    if not body:
        return None
    call = body[0]
    name = getattr(call, "name", None)
    if not name:
        return None
    return bool(getattr(call, "assign", ())), name, list(call.args)


def _format_variable_line(name: str, value) -> str:  # noqa: ANN001
    """Format one *** Variables *** declaration ('${X}    cells...')."""
    if name.startswith("@{") and isinstance(value, (list, tuple)):
        cells = [str(item) for item in value]
    elif name.startswith("&{") and isinstance(value, dict):
        cells = [f"{k}={v}" for k, v in value.items()]
    else:
        cells = [str(value)]
    return "    ".join([name, *cells])


def render_variables_section(declared_variables: dict) -> list[str]:
    """Render the *** Variables *** body (one line per declaration) from a dict."""
    return [_format_variable_line(name, value) for name, value in declared_variables.items()]


def render_session_settings(
    *,
    suite_setup: str | None = None,
    suite_teardown: str | None = None,
    test_setup: str | None = None,
    test_teardown: str | None = None,
    test_tags: list[str] | None = None,
) -> list[str]:
    """Render the Suite/Test setup/teardown and Test Tags entries for *** Settings ***."""
    lines: list[str] = []
    if suite_setup:
        lines.append(f"Suite Setup    {suite_setup}")
    if suite_teardown:
        lines.append(f"Suite Teardown    {suite_teardown}")
    if test_setup:
        lines.append(f"Test Setup    {test_setup}")
    if test_teardown:
        lines.append(f"Test Teardown    {test_teardown}")
    if test_tags:
        lines.append("    ".join(["Test Tags", *test_tags]))
    return lines


def render_test_case_settings(
    *,
    setup: str | None = None,
    teardown: str | None = None,
    tags: list[str] | None = None,
) -> list[str]:
    """Render indented per-test-case settings ([Setup]/[Teardown]/[Tags])."""
    lines: list[str] = []
    if setup:
        lines.append(f"    [Setup]    {setup}")
    if teardown:
        lines.append(f"    [Teardown]    {teardown}")
    if tags:
        lines.append("    " + "    ".join(["[Tags]", *tags]))
    return lines


def _escape_arg_for_cell(value):  # noqa: ANN001, ANN201
    """Pre-escape a value so a leading ``#`` is treated as data, not a comment cell."""
    if isinstance(value, str) and value.startswith("#"):
        return f"\\{value}"
    return value


def _parse_keyword_line(line: str) -> dict | None:
    """Return ``{assign: tuple[str,...], name: str, args: list[str]}`` for a keyword call line, or None."""
    if not line or not line.strip():
        return None
    parsed = _parse_keyword_call(line)
    if parsed is None:
        return None
    has_assign, name, args = parsed
    if not has_assign:
        return {"assign": (), "name": name, "args": args}
    # Recover the structured assignment via robot.api.
    from robot.api import TestSuite
    from robot.variables.search import search_variable

    try:
        suite = TestSuite.from_string(f"*** Test Cases ***\n_\n    {line.strip()}\n")
    except Exception:
        return None
    call = suite.tests[0].body[0]
    assign = tuple(
        match.name
        for match in (search_variable(token) for token in call.assign)
        if match.name
    )
    return {"assign": assign, "name": call.name, "args": list(call.args)}


_CONTROL_FLOW_NAMES = {
    "FOR", "END", "IF", "ELSE", "ELSE IF", "WHILE", "TRY", "EXCEPT", "FINALLY",
    "RETURN", "BREAK", "CONTINUE",
}


def render_keyword_call_line(line: str) -> str | None:
    """Render a flat keyword-call line as canonically-formatted body text via ``robot.api``.

    Returns the line text including the leading 4-space indent (no trailing newline),
    or ``None`` if the line is unparseable, a control-flow header (``FOR``/``IF``/...),
    or already has leading indentation that callers must preserve (nested bodies).
    """

    if not line:
        return None
    rstripped = line.rstrip()
    if not rstripped or rstripped != rstripped.lstrip():
        return None
    parsed = _parse_keyword_line(escape_comment_cells(rstripped))
    if parsed is None or not parsed["name"]:
        return None
    if parsed["name"].upper() in _CONTROL_FLOW_NAMES:
        return None
    import robot.api.parsing as p

    call = p.KeywordCall.from_params(
        name=parsed["name"],
        args=tuple(_escape_arg_for_cell(a) for a in parsed["args"]),
        assign=parsed["assign"],
    )
    return "".join(token.value for token in call.tokens).rstrip("\n")


def render_suite_text(
    *,
    test_case_name: str = "Live Session Test",
    documentation: str | None = None,
    libraries: list[str] | None = None,
    resources: list[str] | None = None,
    variable_files: list[str] | None = None,
    body_steps: list[str] | None = None,
    declared_variables: dict | None = None,
    suite_setup: str | None = None,
    suite_teardown: str | None = None,
    test_setup: str | None = None,
    test_teardown: str | None = None,
    test_tags: list[str] | None = None,
    test_case_setup: str | None = None,
    test_case_teardown: str | None = None,
    test_case_tags: list[str] | None = None,
) -> str:
    """Render a canonically-formatted ``.robot`` test suite via ``robot.api.parsing``.

    Uses Robot Framework's own statement factories (``LibraryImport.from_params``,
    ``KeywordCall.from_params``, ...) and ``File.save`` so the output matches current
    Robot Framework standards (modern ``AS`` aliases, no obsolete ``${x} =`` form,
    canonical 4-space separators, section ordering). Import keyword calls in
    ``body_steps`` are hoisted into ``*** Settings ***``; ``${x}`` declared variables
    into ``*** Variables ***``; setups / teardowns / tags into the proper Settings or
    test-case settings. Values are pre-escaped so a leading ``#`` is not parsed as a
    comment cell (``robot.api.parsing`` does not handle this on output).
    """

    import tempfile
    from pathlib import Path

    import robot.api.parsing as p
    from robot.utils import normalize

    # Pre-escape leading-# cells BEFORE robot.api parsing, otherwise its lexer
    # swallows them as comments and the args/setup keyword-arg values are lost.
    body_steps = [escape_comment_cells(line) for line in (body_steps or [])]
    declared_variables = declared_variables or {}

    # --- Hoist Import Library/Resource/Variables keyword calls into Settings ---
    import_statements: list = []
    remaining_steps: list[str] = []
    for line in body_steps:
        parsed = _parse_keyword_line(line)
        if parsed is not None and not parsed["assign"]:
            kind = normalize(parsed["name"], ignore="_")
            args = parsed["args"]
            if kind == "importlibrary" and args:
                lib_name, *rest = args
                alias: str | None = None
                lib_args = rest
                for marker in ("WITH NAME", "AS"):
                    if marker in rest:
                        idx = rest.index(marker)
                        lib_args = rest[:idx]
                        if idx + 1 < len(rest):
                            alias = rest[idx + 1]
                        break
                import_statements.append(
                    p.LibraryImport.from_params(lib_name, args=tuple(lib_args), alias=alias)
                )
                continue
            if kind == "importresource" and args:
                import_statements.append(p.ResourceImport.from_params(args[0]))
                continue
            if kind == "importvariables" and args:
                import_statements.append(
                    p.VariablesImport.from_params(args[0], args=tuple(args[1:]))
                )
                continue
        remaining_steps.append(line)

    def _kw_setting(setting_cls, value: str):
        # Same pre-escape as for body steps so a leading-# arg survives the parse.
        parsed = _parse_keyword_line(escape_comment_cells(value)) or {
            "name": value.strip(),
            "args": [],
        }
        return setting_cls.from_params(
            name=parsed["name"],
            args=tuple(_escape_arg_for_cell(a) for a in parsed["args"]),
        )

    # Settings body order: Documentation, explicit imports (from params), hoisted
    # imports (from body steps), then setups/teardowns/tags.
    settings_body: list = []
    if documentation:
        settings_body.append(p.Documentation.from_params(documentation))
    for lib_name in libraries or []:
        settings_body.append(p.LibraryImport.from_params(lib_name))
    for res_path in resources or []:
        settings_body.append(p.ResourceImport.from_params(res_path))
    for vf_path in variable_files or []:
        settings_body.append(p.VariablesImport.from_params(vf_path))
    settings_body.extend(import_statements)
    if suite_setup:
        settings_body.append(_kw_setting(p.SuiteSetup, suite_setup))
    if suite_teardown:
        settings_body.append(_kw_setting(p.SuiteTeardown, suite_teardown))
    if test_setup:
        settings_body.append(_kw_setting(p.TestSetup, test_setup))
    if test_teardown:
        settings_body.append(_kw_setting(p.TestTeardown, test_teardown))
    if test_tags:
        settings_body.append(
            p.TestTags.from_params(tuple(_escape_arg_for_cell(t) for t in test_tags))
        )

    variables_body: list = []
    for name, value in declared_variables.items():
        if name.startswith("@{") and isinstance(value, (list, tuple)):
            variables_body.append(
                p.Variable.from_params(
                    name, value=tuple(_escape_arg_for_cell(str(v)) for v in value)
                )
            )
        elif name.startswith("&{") and isinstance(value, dict):
            variables_body.append(
                p.Variable.from_params(name, value=tuple(f"{k}={v}" for k, v in value.items()))
            )
        else:
            variables_body.append(p.Variable.from_params(name, _escape_arg_for_cell(str(value))))

    case_body: list = []
    if test_case_tags:
        case_body.append(
            p.Tags.from_params(tuple(_escape_arg_for_cell(t) for t in test_case_tags))
        )
    if test_case_setup:
        case_body.append(_kw_setting(p.Setup, test_case_setup))
    if test_case_teardown:
        case_body.append(_kw_setting(p.Teardown, test_case_teardown))
    for step in remaining_steps:
        parsed = _parse_keyword_line(step)
        if parsed is None:
            continue
        case_body.append(
            p.KeywordCall.from_params(
                name=parsed["name"],
                args=tuple(_escape_arg_for_cell(a) for a in parsed["args"]),
                assign=parsed["assign"],
            )
        )

    test_case = p.TestCase(
        header=p.TestCaseName.from_params(test_case_name),
        body=case_body,
    )

    sections: list = []
    if settings_body:
        sections.append(
            p.SettingSection(
                header=p.SectionHeader.from_params(p.Token.SETTING_HEADER),
                body=settings_body,
            )
        )
    if variables_body:
        sections.append(
            p.VariableSection(
                header=p.SectionHeader.from_params(p.Token.VARIABLE_HEADER),
                body=variables_body,
            )
        )
    sections.append(
        p.TestCaseSection(
            header=p.SectionHeader.from_params(p.Token.TESTCASE_HEADER),
            body=[test_case],
        )
    )

    suite_file = p.File(sections=sections)
    with tempfile.NamedTemporaryFile("w", suffix=".robot", delete=False) as handle:
        path = Path(handle.name)
    try:
        suite_file.save(str(path))
        return path.read_text(encoding="utf-8")
    finally:
        path.unlink(missing_ok=True)


def hoist_imports(body_lines: list[str]) -> tuple[list[str], list[str]]:
    """Split body lines into (settings_lines, remaining_body_lines).

    ``Import Library`` / ``Import Resource`` / ``Import Variables`` keyword calls are
    converted into their ``*** Settings ***`` declarations (``Library`` / ``Resource`` /
    ``Variables``) — preserving args/alias — so generated suites declare imports
    idiomatically instead of running them inline in the test body. Keyword-name matching
    and argument splitting are done by robot.api (no text parsing). An assigned import
    call (unusual) is left in the body.
    """

    from robot.utils import normalize

    settings: list[str] = []
    remaining: list[str] = []
    for line in body_lines:
        parsed = _parse_keyword_call(line)
        if parsed is not None:
            has_assign, name, args = parsed
            setting = _IMPORT_SETTING.get(normalize(name, ignore="_"))
            if setting and not has_assign:
                settings.append("    ".join([setting, *args]))
                continue
        remaining.append(line)
    return settings, remaining
