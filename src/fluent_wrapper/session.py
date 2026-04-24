from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional


class LaunchMode(str, Enum):
    """Fluent mode to launch.

    Use `SOLVER` when reading existing `.cas` files and extracting solver-side API.
    Use `MESHING` when loading `.wft` workflow definitions and extracting meshing tasks.
    """

    SOLVER = "solver"
    MESHING = "meshing"


class Precision(str, Enum):
    """Floating point precision for launched Fluent sessions."""

    SINGLE = "single"
    DOUBLE = "double"


@dataclass(frozen=True)
class FluentLaunchConfig:
    """Launch options for local Fluent process startup.

    Attributes:
        mode: Fluent operating mode.
        precision: Numeric precision used by Fluent.
        processor_count: Number of local solver/meshing processes.
        start_transcript: Keep False for cleaner automation logs unless debugging.
    """

    mode: LaunchMode
    precision: Precision = Precision.DOUBLE
    processor_count: int = 2
    start_transcript: bool = False


class FluentSessionWrapper:
    """Guard-railed helper around a runtime PyFluent session.

    Why this wrapper exists:
    - Exposes a narrow, explicit API for loading files and handling common failures.
    - Encourages object API usage first, with controlled fallback to TUI-style calls.
    - Provides stable method names and docstrings for local AI assistants.

    Usage pattern:
        wrapper = FluentSessionWrapper()
        solver = wrapper.launch(FluentLaunchConfig(mode=LaunchMode.SOLVER))
        wrapper.load_case(Path(r"S:\\...\\03_PrePost\\example.cas"))
        wrapper.close()
    """

    def __init__(self):
        self.session: Optional[Any] = None

    def launch(self, config: FluentLaunchConfig) -> Any:
        """Launch Fluent and return the session object.

        Raises:
            RuntimeError: If `ansys-fluent-core` is missing or launch fails.
        """

        try:
            import ansys.fluent.core as pyfluent
        except ImportError as exc:
            raise RuntimeError(
                "ansys-fluent-core is not installed in this environment."
            ) from exc

        try:
            self.session = pyfluent.launch_fluent(
                mode=config.mode.value,
                precision=config.precision.value,
                processor_count=config.processor_count,
                start_transcript=config.start_transcript,
            )
            return self.session
        except Exception as exc:
            raise RuntimeError(f"Failed to launch Fluent session: {exc}") from exc

    def load_case(self, case_path: Path) -> None:
        """Load solver case data from disk.

        The wrapper attempts multiple APIs because method names vary by Fluent version.

        Raises:
            RuntimeError: If no supported read-case call succeeds.
        """

        self._ensure_session("load_case")
        case_path = case_path.expanduser().resolve()
        if not case_path.exists():
            raise RuntimeError(f"Case file not found: {case_path}")

        errors: list[str] = []
        for call in (
            lambda: self.session.file.read_case(file_name=str(case_path)),
            lambda: self.session.file.read_case(str(case_path)),
            lambda: self.session.tui.file.read_case(str(case_path)),
        ):
            try:
                call()
                return
            except Exception as exc:
                errors.append(str(exc))

        raise RuntimeError(
            "Failed to load case via known APIs. Errors: " + " | ".join(errors)
        )

    def load_workflow(self, workflow_path: Path) -> None:
        """Load meshing workflow (`.wft`) from disk.

        The wrapper tries both object-API and TUI fallback variants.

        Raises:
            RuntimeError: If workflow loading fails on all known methods.
        """

        self._ensure_session("load_workflow")
        workflow_path = workflow_path.expanduser().resolve()
        if not workflow_path.exists():
            raise RuntimeError(f"Workflow file not found: {workflow_path}")

        errors: list[str] = []
        for call in (
            lambda: self.session.workflow.load_workflow(file_path=str(workflow_path)),
            lambda: self.session.workflow.LoadWorkflow(FilePath=str(workflow_path)),
            lambda: self.session.tui.file.read_workflow(str(workflow_path)),
        ):
            try:
                call()
                return
            except Exception as exc:
                errors.append(str(exc))

        raise RuntimeError(
            "Failed to load workflow via known APIs. Errors: " + " | ".join(errors)
        )

    def close(self) -> None:
        """Best-effort Fluent shutdown without masking previous failures."""

        if self.session is None:
            return
        try:
            self.session.exit()
        except Exception:
            pass
        finally:
            self.session = None

    def _ensure_session(self, operation: str) -> None:
        if self.session is None:
            raise RuntimeError(f"Session is not launched. Cannot run: {operation}")

