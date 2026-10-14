import time
from unittest.mock import MagicMock
import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QGuiApplication, QPixmap

from latex_question_studio.preview.queue import (
    ThumbnailRenderQueue,
    RenderPriority,
    RenderRequest,
)
from latex_question_studio.preview.compiler import CompileResult


@pytest.fixture(scope="session")
def qapp():
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication([])
    return app


def test_render_priority_ordering():
    assert RenderPriority.VIEWPORT > RenderPriority.SELECTED
    assert RenderPriority.SELECTED > RenderPriority.PREFETCH
    assert RenderPriority.PREFETCH > RenderPriority.BACKGROUND


def test_queue_priority_and_deduplication(qapp, tmp_path):
    mock_compiler = MagicMock()
    mock_thumb_mgr = MagicMock()
    
    queue = ThumbnailRenderQueue(mock_compiler, mock_thumb_mgr, max_workers=2)
    # Pause queue to inspect pending items without immediate dispatch
    queue._paused = True

    # Enqueue background item
    queue.enqueue("q1", 1, "\\begin{ex}A\\end{ex}", "key1", {}, priority=RenderPriority.BACKGROUND)
    assert "key1" in queue._pending
    assert queue._pending["key1"].priority == RenderPriority.BACKGROUND

    # Upgrade priority of key1 to VIEWPORT
    queue.enqueue("q1", 1, "\\begin{ex}A\\end{ex}", "key1", {}, priority=RenderPriority.VIEWPORT)
    assert queue._pending["key1"].priority == RenderPriority.VIEWPORT

    # Enqueue PREFETCH item
    queue.enqueue("q2", 1, "\\begin{ex}B\\end{ex}", "key2", {}, priority=RenderPriority.PREFETCH)
    # Enqueue SELECTED item
    queue.enqueue("q3", 1, "\\begin{ex}C\\end{ex}", "key3", {}, priority=RenderPriority.SELECTED)

    assert queue.pending_count() == 3

    # Update key2 priority to VIEWPORT
    queue.update_priority({"key2"}, RenderPriority.VIEWPORT)
    assert queue._pending["key2"].priority == RenderPriority.VIEWPORT

    # Cancel pending
    queue.cancel_all_pending()
    assert queue.pending_count() == 0


def test_queue_concurrency_and_execution(qapp, tmp_path):
    # Setup mock compiler returning a valid pdf
    import pymupdf
    pdf_path = tmp_path / "test.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=200, height=100)
    page.draw_rect(pymupdf.Rect(10, 10, 80, 50), color=(1, 0, 0), fill=(0, 0, 1))
    doc.save(str(pdf_path))
    doc.close()

    mock_compiler = MagicMock()
    mock_compiler.compile.return_value = CompileResult(ok=True, pdf=pdf_path, log="Compiled OK")

    mock_thumb_mgr = MagicMock()

    queue = ThumbnailRenderQueue(mock_compiler, mock_thumb_mgr, max_workers=2)

    ready_results = []
    def on_ready(qid, rev, src, pix, key):
        ready_results.append((qid, rev, key, pix))

    queue.signals.ready.connect(on_ready)

    queue.enqueue("q100", 1, "\\begin{ex}Hello\\end{ex}", "key100", {}, priority=RenderPriority.VIEWPORT)

    # Wait for completion in Qt event loop
    start = time.monotonic()
    while not ready_results and time.monotonic() - start < 5.0:
        QCoreApplication.processEvents()
        time.sleep(0.02)

    assert len(ready_results) == 1
    qid, rev, key, pix = ready_results[0]
    assert qid == "q100"
    assert rev == 1
    assert key == "key100"
    assert isinstance(pix, QPixmap)
    assert not pix.isNull()
    assert mock_thumb_mgr.save.called

    queue.shutdown()
