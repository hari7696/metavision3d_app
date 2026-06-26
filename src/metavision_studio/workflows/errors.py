"""Turn exceptions into messages a lab scientist can act on.

Every failure shown in the GUI has three parts: what went wrong in plain language, a
suggested fix, and the full technical details for the "Copy report" button.
"""

from __future__ import annotations

import platform
import traceback
from dataclasses import dataclass

from metavision_studio import __version__

__all__ = ["StepError", "StepLocked", "explain"]


class StepLocked(RuntimeError):
    """A step was run before the steps it depends on."""


@dataclass
class StepError(Exception):
    """A step failed. ``message`` and ``hint`` are user-facing; ``details`` is the traceback."""

    step: str
    message: str
    hint: str
    details: str

    def __str__(self) -> str:
        return f"{self.message} {self.hint}".strip()

    def report(self) -> str:
        """Text for the clipboard: enough for someone else to diagnose the problem."""
        return (
            f"MetaVision Studio {__version__} · Python {platform.python_version()} · "
            f"{platform.platform()}\nStep: {self.step}\n\n{self.message}\n{self.hint}\n\n"
            f"{self.details}"
        )


def explain(step: str, exc: BaseException) -> StepError:
    """Map an exception to a :class:`StepError` with a plain-language message and fix."""
    details = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    name = type(exc).__name__
    text = str(exc).strip() or name

    if isinstance(exc, StepError):
        return exc
    if isinstance(exc, StepLocked):
        msg, hint = text, ""
    elif isinstance(exc, MemoryError):
        msg = "Ran out of memory."
        hint = "Close other programs, exclude some sections, or drop rare features in Normalise."
    elif isinstance(exc, FileNotFoundError):
        msg = f"A file is missing: {text}"
        hint = "If you moved the data or project folder, re-run Load data."
    elif isinstance(exc, KeyError):
        msg = f"Not found: {text.strip(chr(39))}"
        hint = "Check the molecule or section name. It may have been excluded or filtered out."
    elif name == "RNotFoundError":
        msg = "Pathway enrichment needs R, which wasn't found."
        hint = text
    elif name == "RScriptError":
        msg = "The R pathway analysis failed."
        hint = "Run `metavision-studio doctor` to check R. Details below."
    elif isinstance(exc, ImportError):
        missing = getattr(exc, "name", None) or text
        msg = f"A required package is missing: {missing}"
        hint = (
            'Install it with: pip install "metavision-studio[harmony]"'
            if "harmony" in str(missing).lower()
            else "Reinstall MetaVision Studio or run `metavision-studio doctor`."
        )
    elif isinstance(exc, ValueError):
        msg, hint = text, ""
    else:
        msg = f"Something went wrong ({name}): {text}"
        hint = "Use “Copy report” and share it with the developers."
    return StepError(step=step, message=msg, hint=hint, details=details)
