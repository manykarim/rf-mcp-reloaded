"""Canonical skill definitions and fallback mappings."""

from rfmcp_skills.definitions import (
    BrowserLibraryRepairDefinition,
    BrowserLibraryRepairWorkflowResult,
    browser_library_repair_definition,
    run_browser_library_flagship_repair,
)
from rfmcp_skills.fallbacks import (
    BROWSER_LIBRARY_FLAGSHIP_REPAIR_ID,
    FALLBACK_COMMANDS_BY_SKILL_ID,
    fallback_commands_for,
    render_fallback_commands,
)

__all__ = [
    "BROWSER_LIBRARY_FLAGSHIP_REPAIR_ID",
    "BrowserLibraryRepairDefinition",
    "BrowserLibraryRepairWorkflowResult",
    "FALLBACK_COMMANDS_BY_SKILL_ID",
    "browser_library_repair_definition",
    "fallback_commands_for",
    "render_fallback_commands",
    "run_browser_library_flagship_repair",
]
