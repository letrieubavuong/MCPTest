"""
Priority-based Thumbnail Render Queue for LaTeX Question Studio (Phase J.1).
Prioritizes visible viewport items > selected item > prefetch > background.
Guarantees deduplication, concurrency limits, and non-blocking UI.
"""
from enum import IntEnum
import hashlib
import time
from typing import Dict, Optional, Callable, Any, Set
from dataclasses import dataclass, field
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot, QThreadPool
from PySide6.QtGui import QPixmap, QImage

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
class RenderRequest:
    question_id: str
    revision: int
    source: str
    key: str
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
    Manages asynchronous rendering of LaTeX question thumbnails with strict priority.
    - Viewport cards are compiled first.
    - Deduplicates identical requests via deterministic SHA-256 key.
    - Limits concurrency to prevent CPU/RAM/TeX thrashing (default 2 workers).
    - Cancels stale/pending requests when navigation or filters change.
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
        
        self._pending: Dict[str, RenderRequest] = {}
        self._active: Dict[str, Job] = {}
        self._paused: bool = False

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
        Submits or upgrades a render request. If already running, avoids duplicate work.
        If already queued, promotes to higher priority if needed.
        """
        assets = assets or {}
        
        # 1. If already active, do not spawn another identical compile job
        if key in self._active:
            return

        # 2. If already pending in queue, bump priority if new request has higher priority
        if key in self._pending:
            if priority > self._pending[key].priority:
                self._pending[key].priority = priority
            return

        req = RenderRequest(
            question_id=question_id,
            revision=revision,
            source=source,
            key=key,
            config=config,
            assets=assets,
            priority=priority,
        )
        self._pending[key] = req
        self.signals.queue_changed.emit(len(self._pending), len(self._active))
        self._schedule_next()

    def update_priority(self, keys: Set[str], priority: RenderPriority):
        """Promotes or adjusts priority for a set of keys (e.g. as user scrolls into viewport)."""
        changed = False
        for k in keys:
            if k in self._pending and self._pending[k].priority != priority:
                self._pending[k].priority = priority
                changed = True
        if changed:
            self._schedule_next()

    def cancel_all_pending(self):
        """Discards all unstarted render requests (e.g. when filters or search text change)."""
        self._pending.clear()
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

    def shutdown(self):
        """Cancels all pending and active jobs and waits briefly for workers to terminate."""
        self._paused = True
        self.cancel_all_pending()
        self.cancel_active()
        self._thread_pool.waitForDone(1000)

    def _schedule_next(self):
        if self._paused:
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
                return (req, CompileResult(False, None, "Tác vụ đã bị hủy.", cancelled=True), None)
            try:
                # 1. Compile source to PDF
                result = self.compiler.compile(req.source, req.assets, cancelled)
                if not result.ok or cancelled():
                    return (req, result, None)

                # 2. Render tight cropped thumbnail bytes
                import pymupdf
                with pymupdf.open(result.pdf) as doc:
                    if len(doc) == 0:
                        return (req, CompileResult(False, None, "Tài liệu PDF rỗng."), None)
                    target = doc[0]
                    raw_png = render_page(target, scale=1.5, crop=True)

                return (req, result, raw_png)
            except Exception as e:
                return (req, CompileResult(False, None, f"Lỗi: {e}"), None)

        job = Job(work)
        self._active[req.key] = job

        def on_completed(payload):
            req, result, raw_png = payload
            self._active.pop(req.key, None)
            
            if result and result.ok and raw_png:
                # Save into ThumbnailManager (WebP with fallback to PNG)
                self.thumbnail_manager.save(req.key, raw_png, prefer_webp=True)
                
                # Create QPixmap on Qt GUI thread
                pix = QPixmap()
                pix.loadFromData(raw_png)
                self.signals.ready.emit(req.question_id, req.revision, req.source, pix, req.key)
            else:
                err_msg = ""
                if result and result.log and result.log.strip():
                    err_msg = result.log.strip().splitlines()[-1]
                else:
                    err_msg = "Lỗi biên dịch LaTeX"
                self.signals.failed.emit(req.question_id, err_msg, req.key)
                
            self.signals.queue_changed.emit(len(self._pending), len(self._active))
            self._schedule_next()

        def on_failed(error_str):
            self._active.pop(req.key, None)
            self.signals.failed.emit(req.question_id, error_str, req.key)
            self.signals.queue_changed.emit(len(self._pending), len(self._active))
            self._schedule_next()

        job.signals.completed.connect(on_completed)
        job.signals.failed.connect(on_failed)
        self._thread_pool.start(job)
