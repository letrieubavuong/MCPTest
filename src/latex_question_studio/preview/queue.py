"""
Priority-based Thumbnail Render Queue for LaTeX Question Studio (Phase J.1 & J.7).
- Viewport cards are compiled first (VIEWPORT > SELECTED > PREFETCH > BACKGROUND).
- Multi-subscriber fan-out: multiple questions sharing an identical key are compiled once and all receive the thumbnail.
- Fast cache check: instantly emits cached pixmap without spawning background jobs.
- Safe lifecycle: cancellation tokens, generation tracking, and robust shutdown with subprocess killing.
- GUI safety: strictly avoids creating QPixmap outside the main GUI thread.
"""
from enum import IntEnum
import hashlib
import time
from typing import Dict, Optional, Callable, Any, Set
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot, QThreadPool, QTimer
from PySide6.QtGui import QPixmap

from latex_question_studio.ui.jobs import Job
from latex_question_studio.preview.compiler import Compiler, CompileResult
from latex_question_studio.preview.crop import render_page
from latex_question_studio.preview.thumbnails import ThumbnailManager


class RenderPriority(IntEnum):
    BACKGROUND = 0
    PREFETCH = 10
    SELECTED = 20
    VIEWPORT = 30


@dataclass
class Subscriber:
    question_id: str
    revision: int
    source: str
    generation: int
    priority: RenderPriority = RenderPriority.VIEWPORT
    cancelled: bool = False


@dataclass
class RenderRequest:
    key: str
    source: str
    config: Dict[str, Any]
    assets: Dict[str, Path]
    priority: RenderPriority = RenderPriority.BACKGROUND
    requested_at: float = field(default_factory=time.monotonic)


class RenderQueueSignals(QObject):
    ready = Signal(str, int, str, object, str)  # question_id, revision, source, pixmap, key
    failed = Signal(str, str, str)              # question_id, error_message, key
    queue_changed = Signal(int, int)            # pending_count, active_count


class ThumbnailRenderQueue(QObject):
    """
    Manages asynchronous rendering of LaTeX question thumbnails with strict priority and multi-subscriber fan-out.
    """

    def __init__(
        self,
        compiler: Compiler,
        thumbnail_manager: ThumbnailManager,
        max_workers: int = 2,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.compiler = compiler
        self.thumbnail_manager = thumbnail_manager
        self.max_workers = max_workers
        self.signals = RenderQueueSignals()
        
        self._thread_pool = QThreadPool(self)
        self._thread_pool.setMaxThreadCount(max_workers)
        
        # Subscriber registry: key -> {question_id: Subscriber}
        self._subscribers: Dict[str, Dict[str, Subscriber]] = {}
        # Reverse lookup: question_id -> current key
        self._question_key: Dict[str, str] = {}
        
        # Pending requests: key -> RenderRequest
        self._pending: Dict[str, RenderRequest] = {}
        # Active jobs: key -> Job
        self._active: Dict[str, Job] = {}
        
        self._generation: int = 0
        self._paused: bool = False
        self._is_shutdown: bool = False

    def enqueue(
        self,
        question_id: str,
        revision: int,
        source: str,
        key: str,
        config: Dict[str, Any],
        assets: Optional[Dict[str, Path]] = None,
        priority: RenderPriority = RenderPriority.VIEWPORT,
    ):
        """
        Submits or upgrades a render request.
        If cache hit: immediately emits ready signal without queueing.
        If already active or pending: registers subscriber and boosts priority if needed.
        If new: enqueues request and starts worker if concurrency allows.
        """
        if self._is_shutdown:
            return

        assets = assets or {}

        # 1. Fast cache hit check (Requirement J.7.1 #5)
        if self.thumbnail_manager is not None:
            cached_pix = self.thumbnail_manager.get_pixmap(key)
            if cached_pix is not None and not cached_pix.isNull():
                self.signals.ready.emit(question_id, revision, source, cached_pix, key)
                return

        # 2. If question was previously subscribed to a different key, unsubscribe it
        old_key = self._question_key.get(question_id)
        if old_key and old_key != key and old_key in self._subscribers:
            self._subscribers[old_key].pop(question_id, None)
            if not self._subscribers[old_key]:
                self._subscribers.pop(old_key, None)
                if old_key in self._pending:
                    self._pending.pop(old_key, None)

        # 3. Register subscriber for this key
        sub = Subscriber(
            question_id=question_id,
            revision=revision,
            source=source,
            generation=self._generation,
            priority=priority,
        )
        if key not in self._subscribers:
            self._subscribers[key] = {}
        self._subscribers[key][question_id] = sub
        self._question_key[question_id] = key

        # 4. If key is already actively compiling, don't spawn another job
        if key in self._active:
            return

        # 5. If key is already pending, upgrade priority if higher
        if key in self._pending:
            if priority > self._pending[key].priority:
                self._pending[key].priority = priority
            return

        # 6. New request
        req = RenderRequest(
            key=key,
            source=source,
            config=config,
            assets=assets,
            priority=priority,
        )
        self._pending[key] = req
        self.signals.queue_changed.emit(len(self._pending), len(self._active))
        self._schedule_next()

    def update_priority(self, keys: Set[str], priority: RenderPriority):
        """Promotes or adjusts priority for a set of keys (e.g. as user scrolls into viewport)."""
        if self._is_shutdown:
            return
        changed = False
        for k in keys:
            if k in self._pending and self._pending[k].priority != priority:
                self._pending[k].priority = priority
                changed = True
            # Also update subscriber priorities
            if k in self._subscribers:
                for sub in self._subscribers[k].values():
                    if priority > sub.priority:
                        sub.priority = priority
        if changed:
            self._schedule_next()

    def cancel_question(self, question_id: str):
        """Cancels render subscription for a specific question."""
        key = self._question_key.pop(question_id, None)
        if key and key in self._subscribers:
            self._subscribers[key].pop(question_id, None)
            if not self._subscribers[key]:
                self._subscribers.pop(key, None)
                if key in self._pending:
                    self._pending.pop(key, None)
                    self.signals.queue_changed.emit(len(self._pending), len(self._active))
                elif key in self._active:
                    self._active[key].cancelled.set()

    def cancel_all_pending(self):
        """Discards all unstarted render requests (e.g. when filters or search text change)."""
        self._generation += 1
        for key in list(self._pending.keys()):
            self._subscribers.pop(key, None)
        self._pending.clear()
        
        # Clear question mapping for non-active items
        for qid, k in list(self._question_key.items()):
            if k not in self._active:
                self._question_key.pop(qid, None)

        self.signals.queue_changed.emit(len(self._pending), len(self._active))

    def cancel_active(self):
        """Signals active compiling jobs to abort immediately."""
        for job in list(self._active.values()):
            job.cancelled.set()

    def is_busy(self) -> bool:
        return bool(self._pending or self._active)

    def pending_count(self) -> int:
        return len(self._pending)

    def active_count(self) -> int:
        return len(self._active)

    def subscriber_count(self, key: Optional[str] = None) -> int:
        if key is not None:
            return len(self._subscribers.get(key, {}))
        return sum(len(subs) for subs in self._subscribers.values())

    def shutdown(self, timeout_ms: int = 3000):
        """
        Gracefully cancels all pending & active jobs, aborts subprocesses,
        and waits up to timeout_ms for thread pool workers to finish.
        """
        self._is_shutdown = True
        self._paused = True
        self.cancel_all_pending()
        self.cancel_active()
        
        if hasattr(self.compiler, 'kill_all_active'):
            self.compiler.kill_all_active()

        # Disconnect signals to prevent dead-receiver callbacks
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for sig in (self.signals.ready, self.signals.failed, self.signals.queue_changed):
                try:
                    sig.disconnect()
                except Exception:
                    pass

        self._thread_pool.waitForDone(timeout_ms)
        self._subscribers.clear()
        self._question_key.clear()
        self._active.clear()

    def _schedule_next(self):
        if self._paused or self._is_shutdown:
            return
            
        while len(self._active) < self.max_workers and self._pending:
            # Pick highest priority item, then oldest requested
            best_key = max(
                self._pending.keys(),
                key=lambda k: (self._pending[k].priority, -self._pending[k].requested_at)
            )
            req = self._pending.pop(best_key)
            self._start_worker(req)
            self.signals.queue_changed.emit(len(self._pending), len(self._active))

    def _start_worker(self, req: RenderRequest):
        def work(cancelled, progress):
            if cancelled():
                return (req.key, CompileResult(False, None, "Tác vụ đã bị hủy.", cancelled=True), None)
            try:
                # 1. Compile source to PDF
                result = self.compiler.compile(req.source, req.assets, cancelled)
                if not result.ok or cancelled():
                    return (req.key, result, None)

                # 2. Render tight cropped thumbnail raw bytes (No QPixmap created in worker thread!)
                import pymupdf
                with pymupdf.open(result.pdf) as doc:
                    if len(doc) == 0:
                        return (req.key, CompileResult(False, None, "Tài liệu PDF rỗng."), None)
                    target = doc[0]
                    raw_png = render_page(target, scale=1.5, crop=True)

                return (req.key, result, raw_png)
            except Exception as e:
                return (req.key, CompileResult(False, None, f"Lỗi: {e}"), None)

        job = Job(work)
        self._active[req.key] = job

        def on_completed(payload):
            key, result, raw_png = payload
            self._active.pop(key, None)
            
            if self._is_shutdown:
                return

            subs_dict = self._subscribers.pop(key, {})

            if result and result.ok and raw_png:
                # Save into ThumbnailManager on disk/RAM
                self.thumbnail_manager.save(key, raw_png, prefer_webp=True)
                
                # Create QPixmap strictly on GUI thread
                pix = QPixmap()
                pix.loadFromData(raw_png)
                
                # Fan out to all valid subscribers
                for sub in list(subs_dict.values()):
                    self._question_key.pop(sub.question_id, None)
                    if not sub.cancelled and sub.generation == self._generation:
                        self.signals.ready.emit(sub.question_id, sub.revision, sub.source, pix, key)
            else:
                err_msg = ""
                if result and result.log and result.log.strip():
                    err_msg = result.log.strip().splitlines()[-1]
                else:
                    err_msg = "Lỗi biên dịch LaTeX"
                    
                # Fan out failure to all valid subscribers
                for sub in list(subs_dict.values()):
                    self._question_key.pop(sub.question_id, None)
                    if not sub.cancelled and sub.generation == self._generation:
                        self.signals.failed.emit(sub.question_id, err_msg, key)
                
            self.signals.queue_changed.emit(len(self._pending), len(self._active))
            self._schedule_next()

        def on_failed(error_str):
            key = req.key
            self._active.pop(key, None)
            
            if self._is_shutdown:
                return

            subs_dict = self._subscribers.pop(key, {})
            for sub in list(subs_dict.values()):
                self._question_key.pop(sub.question_id, None)
                if not sub.cancelled and sub.generation == self._generation:
                    self.signals.failed.emit(sub.question_id, error_str, key)
                    
            self.signals.queue_changed.emit(len(self._pending), len(self._active))
            self._schedule_next()

        job.signals.completed.connect(on_completed)
        job.signals.failed.connect(on_failed)
        self._thread_pool.start(job)
