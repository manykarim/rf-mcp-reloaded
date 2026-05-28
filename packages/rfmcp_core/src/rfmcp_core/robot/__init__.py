"""Robot Framework-facing helper modules."""

from rfmcp_core.robot.authoring import (
    escape_comment_cells,
    hoist_imports,
    render_keyword_call_line,
    render_session_settings,
    render_suite_text,
    render_test_case_settings,
    render_variables_section,
)
from rfmcp_core.robot.diagnostics import build_failure_context, run_repair_diagnostics
from rfmcp_core.robot.validation import validate_robot_artifact

__all__ = [
    "build_failure_context",
    "escape_comment_cells",
    "hoist_imports",
    "render_keyword_call_line",
    "render_session_settings",
    "render_suite_text",
    "render_test_case_settings",
    "render_variables_section",
    "run_repair_diagnostics",
    "validate_robot_artifact",
]
