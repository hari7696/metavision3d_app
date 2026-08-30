"""Run work in a background thread and deliver results on the Qt main thread.

The worker never touches Qt. It calls the progress callback, which emits a Qt signal. Signals
connected to methods of this QObject (which lives on the main thread) are delivered through
Qt's event queue, so every user callback runs on the main thread.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from qtpy.QtCore import QObject, Signal

from metavision_studio._progress import Cancelled

__all__ = ["JobRunner"]


class JobRunner(QObject):
    progressed = Signal(int, int, str)
    started = Signal(str)
    stopped = Signal()

    _done = Signal(int, object)
    _failed = Signal(int, object)
    _cancelled = Signal(int)
    _progress = Signal(int, int, int, str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._job = 0
        self._busy = False
        self._cancel = threading.Event()
        self._callbacks: dict[int, tuple[Callable, Callable, Callable | None]] = {}
        self._done.connect(self._on_done)
        self._failed.connect(self._on_failed)
        self._cancelled.connect(self._on_cancelled)
        self._progress.connect(self._on_progress)

    @property
    def busy(self) -> bool:
        return self._busy

    def start(
        self,
        fn: Callable[[Callable[[int, int, str], None]], Any],
        *,
        label: str = "",
        on_done: Callable[[Any], None],
        on_error: Callable[[BaseException], None],
        on_cancel: Callable[[], None] | None = None,
        exclusive: bool = True,
    ) -> bool:
        """Run ``fn(progress)`` in a thread.

        With ``exclusive``, refuse (return False) while another job runs. Without it, the
        previous job's result is discarded and the latest job wins, which suits view refreshes.
        """
        if exclusive and self._busy:
            return False
        if not exclusive and self._busy:
            self._cancel.set()  # let the stale job stop at its next progress point
        self._job += 1
        job = self._job
        cancel = threading.Event()
        self._cancel = cancel
        self._busy = True
        self._callbacks[job] = (on_done, on_error, on_cancel)

        def progress(done: int, total: int, message: str = "") -> None:
            if cancel.is_set():
                raise Cancelled()
            self._progress.emit(job, int(done), int(total), str(message))

        def target() -> None:
            try:
                result = fn(progress)
            except Cancelled:
                self._cancelled.emit(job)
            except BaseException as exc:
                self._failed.emit(job, exc)
            else:
                # The work finished (and, for steps, was recorded in project.json): report it
                # as done even if Cancel was pressed too late to stop it, so the UI never says
                # "Cancelled" for a result that exists. Stale jobs are ignored in _on_done.
                self._done.emit(job, result)

        self.started.emit(label)
        threading.Thread(target=target, name=f"metavision-job-{job}", daemon=True).start()
        return True

    def cancel(self) -> None:
        self._cancel.set()

    # ------------------------------------------------------------------ main thread
    def _finish(self, job: int) -> tuple[Callable, Callable, Callable | None] | None:
        cbs = self._callbacks.pop(job, None)
        if job == self._job:
            self._busy = False
            self.stopped.emit()
        return cbs

    def _on_progress(self, job: int, done: int, total: int, message: str) -> None:
        if job == self._job:
            self.progressed.emit(done, total, message)

    def _on_done(self, job: int, result: object) -> None:
        cbs = self._finish(job)
        if cbs and job == self._job:
            cbs[0](result)

    def _on_failed(self, job: int, exc: object) -> None:
        cbs = self._finish(job)
        if cbs and job == self._job:
            cbs[1](exc)  # type: ignore[arg-type]

    def _on_cancelled(self, job: int) -> None:
        cbs = self._finish(job)
        if cbs and cbs[2] is not None and job == self._job:
            cbs[2]()
