from __future__ import annotations

from typing import Any, Callable

from PyQt6.QtCore import QObject, QThread, pyqtSignal


class Worker(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(Exception)
    progress = pyqtSignal(int)

    def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self) -> None:
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(exc)


class WorkerRunner:
    def __init__(self) -> None:
        self._threads: list[QThread] = []

    def start(self, fn: Callable[..., Any], on_finish: Callable[[Any], None], on_error: Callable[[Exception], None], *args: Any, **kwargs: Any) -> None:
        thread = QThread()
        worker = Worker(fn, *args, **kwargs)
        worker.moveToThread(thread)
        worker.finished.connect(on_finish)
        worker.failed.connect(on_error)
        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        self._threads.append(thread)
        thread.start()
