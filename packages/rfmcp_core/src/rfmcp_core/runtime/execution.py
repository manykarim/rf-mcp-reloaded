"""In-process Robot Framework execution engine for live sessions.

Holds a persistent Robot Framework execution context per session so keywords run
for real (real pass/fail, real variables, live library instances) and state carries
across steps. This is the engine FR-2 requires; the MCP tools and the stepper drive
it, while the session store owns lifecycle/accounting.
"""

from __future__ import annotations

import os
import sys
import tempfile
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

# Robot Framework's EXECUTION_CONTEXTS and sys.stdout/sys.stderr are process-global.
# This lock serializes context creation and keyword execution across sessions/threads
# so concurrent callers cannot corrupt the shared context stack or the stdout swap
# (fd 1 is the MCP stdio JSON-RPC channel).
_CONTEXT_LOCK = threading.RLock()

# Default libraries every live session can rely on.
DEFAULT_LIBRARIES: tuple[str, ...] = ("BuiltIn", "Collections")


@dataclass
class StepExecution:
    """Outcome of running a single keyword in the live context."""

    ok: bool
    keyword: str
    return_value: Any = None
    assigned: str | None = None
    error_message: str | None = None
    error_type: str | None = None


@contextmanager
def _suppress_streams() -> Iterator[None]:
    """Redirect stdout/stderr to os.devnull.

    Robot Framework writes console/log output to stdout; on the MCP ``stdio``
    transport fd 1 is the JSON-RPC channel, so RF console output would corrupt it.
    """

    with _CONTEXT_LOCK:
        devnull = open(os.devnull, "w")
        saved_out, saved_err = sys.stdout, sys.stderr
        try:
            sys.stdout = devnull
            sys.stderr = devnull
            yield
        finally:
            sys.stdout = saved_out
            sys.stderr = saved_err
            devnull.close()


def _json_safe(value: Any) -> Any:
    """Coerce a value to something the contract payload can JSON-serialize."""

    import json

    if isinstance(value, (bytes, bytearray)):
        import base64

        return base64.b64encode(bytes(value)).decode("ascii")
    try:
        json.dumps(value, allow_nan=False)
        return value
    except (TypeError, ValueError):
        return repr(value)


def _parse_instruction(instruction: str) -> tuple[str | None, str, list[str]]:
    """Split an RF step line into (assign_to, keyword, args) using robot.api.

    Parsing goes through Robot Framework's own data parser (``TestSuite.from_string``)
    so cell separators, assignment syntax, and escaping are handled exactly as Robot
    does — no hand-rolled text splitting. ``assign_to`` is the full variable form
    (e.g. ``${result}``) or ``None``. A line that is not a single keyword call
    (blank, or a control structure such as IF/FOR) yields an empty keyword.
    """

    text = instruction.strip()
    if not text:
        return None, "", []

    from robot.api import TestSuite
    from robot.variables.search import search_variable

    try:
        with _suppress_streams():
            suite = TestSuite.from_string(f"*** Test Cases ***\n_\n    {text}\n")
    except Exception:
        return None, "", []

    body = list(suite.tests[0].body) if suite.tests else []
    if not body:
        return None, "", []
    call = body[0]
    keyword = getattr(call, "name", None)
    if not keyword:  # control structure (IF/FOR/TRY/...) or unparseable line
        return None, "", []

    assign_to: str | None = None
    assign = getattr(call, "assign", ())
    if assign:
        assign_to = search_variable(assign[0]).name or None
    return assign_to, keyword, list(call.args)


class LiveExecutionContext:
    """A persistent Robot Framework execution context for one session."""

    def __init__(self, session_id: str, libraries: list[str] | None = None) -> None:
        self._session_id = session_id
        self._libraries = list(libraries) if libraries else list(DEFAULT_LIBRARIES)
        self._tempdir: str | None = None
        self._ctx: Any = None
        self._namespace: Any = None
        self._variables: Any = None
        self._started = False
        # Variables set/assigned via this engine. RF resolves them in keyword
        # execution, but RF's as_dict() does not always enumerate writes made
        # through __setitem__, so we track them here for deterministic reads.
        self._assigned: dict[str, Any] = {}

    @property
    def started(self) -> bool:
        return self._started

    @property
    def variables(self) -> Any:
        return self._variables

    @property
    def libraries(self) -> list[str]:
        return list(self._libraries)

    def get_library_instance(self, name: str) -> Any:
        """Return the live imported library instance, or None if unavailable."""

        if self._namespace is None:
            return None
        try:
            return self._namespace.get_library_instance(name)
        except Exception:
            return None

    def get_variables(self, keys: list[str] | None = None) -> dict[str, Any]:
        """Return live Robot Framework variables (JSON-coerced), optionally filtered."""

        if not self._started:
            self.start()
        with _CONTEXT_LOCK:
            if keys:
                # Resolve each requested key directly: __getitem__ reflects the
                # live value across scopes even when as_dict() does not enumerate it.
                out: dict[str, Any] = {}
                for key in keys:
                    try:
                        out[key] = self._variables[key]
                    except Exception:
                        if key in self._assigned:
                            out[key] = self._assigned[key]
                return {name: _json_safe(value) for name, value in out.items()}
            try:
                raw = dict(self._variables.as_dict())
            except Exception:
                raw = {}
            # Prefer the live namespace where it enumerates a key; fall back to
            # engine-tracked assignments for keys as_dict() omits.
            merged = {**self._assigned, **raw}
            return {name: _json_safe(value) for name, value in merged.items()}

    def set_variable(self, name: str, value: Any) -> None:
        """Write a variable into the live namespace (RF name form, e.g. ``${X}``)."""

        if not self._started:
            self.start()
        with _CONTEXT_LOCK:
            self._variables[name] = value
            self._assigned[name] = value

    def imported_libraries(self) -> list[str]:
        """Return the names of libraries actually imported in the live namespace."""

        if not self._started:
            self.start()
        try:
            return [lib.name for lib in self._namespace.libraries]
        except Exception:
            return list(self._libraries)

    def start(self) -> None:
        """Build and register the persistent RF execution context (idempotent)."""

        if self._started:
            return

        from robot.conf.languages import Languages
        from robot.conf.settings import RobotSettings
        from robot.output import Output
        from robot.running.context import EXECUTION_CONTEXTS
        from robot.running.model import TestSuite
        from robot.running.namespace import Namespace
        from robot.running.resourcemodel import ResourceFile
        from robot.variables.scopes import VariableScopes

        try:
            with _suppress_streams():
                # Double-checked: another thread may have started while we waited
                # on the lock; do not register a second context for this session.
                if self._started:
                    return

                # RF's global LOGGER can write console output straight to the
                # original fd 1 (the MCP stdio JSON-RPC channel), bypassing the
                # sys.stdout swap; unregister its console logger.
                try:
                    from robot.output.logger import LOGGER

                    LOGGER.unregister_console_logger()
                except Exception:
                    pass

                self._tempdir = tempfile.mkdtemp(prefix="rfmcp_session_")

                variables = VariableScopes(RobotSettings())
                suite = TestSuite(name=f"RFMCP_Session_{self._session_id}")
                suite.source = Path(self._tempdir) / f"{suite.name}.robot"
                suite.resource = ResourceFile(source=suite.source)

                namespace = Namespace(variables, suite, suite.resource, Languages())

                settings = RobotSettings(outputdir=self._tempdir, output=None, console="none")
                output = Output(settings)
                try:
                    output.library_listeners.new_suite_scope()
                except Exception:
                    pass

                variables["${OUTPUTDIR}"] = self._tempdir
                variables["${LOGFILE}"] = os.path.join(self._tempdir, "log.html")
                variables["${OUTPUT}"] = os.path.join(self._tempdir, "output.xml")

                ctx = EXECUTION_CONTEXTS.start_suite(suite, namespace, output, dry_run=False)
                try:
                    setattr(ctx, "_rfmcp_session", self._session_id)
                except Exception:
                    pass
                try:
                    namespace.start_suite()
                except Exception:
                    pass

                for library in self._libraries:
                    try:
                        namespace.import_library(library)
                    except Exception:
                        pass

                self._ctx = ctx
                self._namespace = namespace
                self._variables = variables
                self._started = True
        except Exception:
            # Context creation failed partway — drop the orphaned temp dir.
            if self._tempdir and os.path.isdir(self._tempdir):
                import shutil

                shutil.rmtree(self._tempdir, ignore_errors=True)
            self._tempdir = None
            raise

    def execute(self, instruction: str) -> StepExecution:
        """Run one keyword in the live context and return a typed outcome."""

        if not self._started:
            self.start()

        assign_to, keyword, args = _parse_instruction(instruction)
        if not keyword:
            return StepExecution(
                ok=False,
                keyword="",
                error_message="No keyword was provided to execute.",
                error_type="EmptyInstruction",
            )

        try:
            with _suppress_streams():
                return_value = self._run_keyword(keyword, args)
                if assign_to is not None:
                    self._variables[assign_to] = return_value
                    self._assigned[assign_to] = return_value
        except InterruptedError:
            # Surface interruption to the stepper's structured interrupt path.
            raise
        except Exception as exc:  # real RF keyword failure
            return StepExecution(
                ok=False,
                keyword=keyword,
                error_message=str(exc) or exc.__class__.__name__,
                error_type=exc.__class__.__name__,
            )

        return StepExecution(
            ok=True,
            keyword=keyword,
            return_value=return_value,
            assigned=assign_to,
        )

    def query(self, keyword: str, args: list[str] | None = None) -> Any:
        """Run a keyword for its return value WITHOUT recording a step.

        Used by inspection snapshots to pull live application state (e.g. DOM,
        screenshots) from the real loaded library. Raises on not-found/failure.
        """

        if not self._started:
            self.start()
        with _suppress_streams():
            return self._run_keyword(keyword, list(args or []))

    def _run_keyword(self, keyword: str, args: list[str]) -> Any:
        """Execute a keyword via the RF 7 native runner (args resolved by RF)."""

        if not hasattr(self._namespace, "get_runner"):
            raise RuntimeError(
                "Robot Framework namespace does not expose get_runner(); unsupported RF version."
            )
        from robot.result.model import Keyword as ResultKeyword
        from robot.running.model import Keyword as RunKeyword

        # get_runner returns an InvalidKeywordRunner for an unknown keyword, whose
        # .run() raises — so a missing keyword surfaces as a normal failure. No
        # BuiltIn().run_keyword fallback: it would execute against the process-global
        # EXECUTION_CONTEXTS.current (possibly another session), not self._ctx.
        runner = self._namespace.get_runner(keyword)
        data_kw = RunKeyword(name=keyword, args=tuple(args))
        res_kw = ResultKeyword(name=keyword, args=tuple(args))
        return runner.run(data_kw, res_kw, self._ctx)

    def close(self) -> None:
        """Tear down the RF context and remove the temp output dir (idempotent)."""

        if not self._started:
            return
        from robot.running.context import EXECUTION_CONTEXTS

        with _suppress_streams():
            try:
                if self._namespace is not None:
                    self._namespace.end_suite()
            except Exception:
                pass
            try:
                if EXECUTION_CONTEXTS.current is self._ctx:
                    EXECUTION_CONTEXTS.end_suite(self._ctx.suite)
            except Exception:
                # Defensive fallback for RF 7.4.x: end_suite() failed, so pop this
                # context off the private stack directly. Relies on RF internals
                # (_contexts list, _context pointer); revisit on RF major upgrades.
                try:
                    if self._ctx in EXECUTION_CONTEXTS._contexts:
                        EXECUTION_CONTEXTS._contexts.remove(self._ctx)
                        EXECUTION_CONTEXTS._context = (
                            EXECUTION_CONTEXTS._contexts[-1]
                            if EXECUTION_CONTEXTS._contexts
                            else None
                        )
                except Exception:
                    pass

        if self._tempdir and os.path.isdir(self._tempdir):
            import shutil

            shutil.rmtree(self._tempdir, ignore_errors=True)

        self._ctx = None
        self._namespace = None
        self._variables = None
        self._assigned = {}
        self._started = False
