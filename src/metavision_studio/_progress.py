"""Progress reporting and cancellation shared by all long-running core functions.

Core functions take an optional ``progress`` callback, ``progress(done, total, message)``.
To cancel, the callback raises :class:`Cancelled` (the GUI does this when the user clicks
Cancel). Core code calls :func:`report` at safe points, so cancelling never leaves
half-written outputs behind.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator

ProgressFn = Callable[[int, int, str], None]


class Cancelled(Exception):
    """Raised from a progress callback to stop a running job."""


def report(progress: ProgressFn | None, done: int, total: int, message: str = "") -> None:
    if progress is not None:
        progress(done, total, message)


def track[T](
    items: Iterable[T],
    progress: ProgressFn | None,
    total: int,
    message: str = "",
) -> Iterator[T]:
    """Yield ``items`` and report ``i/total`` before each one (e.g. "Aligning 14/79")."""
    for i, item in enumerate(items):
        report(progress, i, total, f"{message} {i + 1}/{total}".strip())
        yield item
    report(progress, total, total, message)
