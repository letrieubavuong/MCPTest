from threading import Event
from PySide6.QtCore import QObject, QRunnable, Signal, Slot

class JobSignals(QObject):
    completed = Signal(object)
    failed = Signal(str)
    progress = Signal(int, int)

class Job(QRunnable):
    def __init__(self, function):
        super().__init__()
        self.function = function
        self.signals = JobSignals()
        self.cancelled = Event()
        self.finished = Event()

    @Slot()
    def run(self):
        try:
            result = self.function(self.cancelled.is_set, self.signals.progress.emit)
            from shiboken6 import isValid
            if isValid(self.signals):self.signals.completed.emit(result)
        except Exception as error:
            from shiboken6 import isValid
            if isValid(self.signals):self.signals.failed.emit(str(error))
        finally:
            self.finished.set()
