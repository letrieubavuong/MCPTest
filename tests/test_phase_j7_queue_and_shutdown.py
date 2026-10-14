"""
Phase J.7 - Hardening & Release Candidate Tests (J.7.1 & J.7.2).
Tests:
1. Multi-subscriber fan-out when multiple question IDs share an identical thumbnail key.
2. Subscriber cancellation and generation isolation across filter/search changes.
3. 100 identical requests compile exactly once.
4. Fast cache hit bypass without compiling.
5. Safe shutdown while compile subprocess is running, without process leaks.
6. CloseEvent preservation: user clicking Cancel on unsaved changes does not shutdown queue or close app.
"""
import time
from unittest.mock import MagicMock
from pathlib import Path
import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import QMessageBox

from latex_question_studio.preview.queue import (
    ThumbnailRenderQueue,
    RenderPriority,
    Subscriber,
)
from latex_question_studio.preview.compiler import Compiler, CompileResult
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.ui.main_window import MainWindow


# Tests use pytest-qt's standard qapp/qtbot fixtures


def create_dummy_pdf(tmp_path: Path) -> Path:
    import pymupdf
    pdf_path = tmp_path / "dummy_preview.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=300, height=150)
    page.draw_rect(pymupdf.Rect(20, 20, 100, 60), color=(0, 0, 1), fill=(0.8, 0.9, 1))
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def test_j71_two_ids_same_key_pending_both_receive_ready(qapp, tmp_path):
    """J.7.1: Hai ID khác nhau có cùng render key khi pending đều phải nhận được signal ready."""
    pdf_path = create_dummy_pdf(tmp_path)
    mock_compiler = MagicMock()
    mock_compiler.compile.return_value = CompileResult(ok=True, pdf=pdf_path, log="OK")
    mock_thumb_mgr = MagicMock()
    mock_thumb_mgr.get_pixmap.return_value = None

    queue = ThumbnailRenderQueue(mock_compiler, mock_thumb_mgr, max_workers=2)
    queue._paused = True  # Pause to hold both in pending

    received = []
    queue.signals.ready.connect(lambda qid, rev, src, pix, key: received.append((qid, rev, key)))

    # Enqueue Q1 and Q2 with identical key
    queue.enqueue("q1", 1, "source_shared", "key_shared", {}, priority=RenderPriority.BACKGROUND)
    queue.enqueue("q2", 1, "source_shared", "key_shared", {}, priority=RenderPriority.VIEWPORT)

    assert queue.subscriber_count("key_shared") == 2
    # Verify priority was bumped to VIEWPORT
    assert queue._pending["key_shared"].priority == RenderPriority.VIEWPORT

    # Unpause and run event loop
    queue._paused = False
    queue._schedule_next()

    start = time.monotonic()
    while len(received) < 2 and time.monotonic() - start < 5.0:
        QCoreApplication.processEvents()
        time.sleep(0.02)

    assert len(received) == 2
    received_qids = {r[0] for r in received}
    assert received_qids == {"q1", "q2"}
    assert mock_compiler.compile.call_count == 1
    queue.shutdown()


def test_j71_two_ids_same_key_active_fan_out(qapp, tmp_path):
    """J.7.1: ID thứ 2 được enqueue khi job cho key đó ĐANG CHẠY (active) vẫn nhận được signal."""
    pdf_path = create_dummy_pdf(tmp_path)
    
    # Compiler with slight delay to ensure key is active when Q2 arrives
    def delayed_compile(src, assets, cancelled):
        time.sleep(0.1)
        return CompileResult(ok=True, pdf=pdf_path, log="OK")

    mock_compiler = MagicMock()
    mock_compiler.compile.side_effect = delayed_compile
    mock_thumb_mgr = MagicMock()
    mock_thumb_mgr.get_pixmap.return_value = None

    queue = ThumbnailRenderQueue(mock_compiler, mock_thumb_mgr, max_workers=2)

    received = []
    queue.signals.ready.connect(lambda qid, rev, src, pix, key: received.append((qid, rev, key)))

    # Enqueue Q1 -> worker starts immediately
    queue.enqueue("q1", 1, "source_shared", "key_active", {}, priority=RenderPriority.VIEWPORT)
    assert "key_active" in queue._active

    # Enqueue Q2 while key_active is still running
    queue.enqueue("q2", 1, "source_shared", "key_active", {}, priority=RenderPriority.VIEWPORT)
    assert queue.subscriber_count("key_active") == 2

    start = time.monotonic()
    while len(received) < 2 and time.monotonic() - start < 5.0:
        QCoreApplication.processEvents()
        time.sleep(0.02)

    assert len(received) == 2
    received_qids = {r[0] for r in received}
    assert received_qids == {"q1", "q2"}
    assert mock_compiler.compile.call_count == 1
    queue.shutdown()


def test_j71_failure_fan_out_to_all_subscribers(qapp, tmp_path):
    """J.7.1: Khi biên dịch lỗi, tín hiệu failed được gửi đến tất cả subscriber của key."""
    mock_compiler = MagicMock()
    mock_compiler.compile.return_value = CompileResult(ok=False, pdf=None, log="! Package error: syntax error")
    mock_thumb_mgr = MagicMock()
    mock_thumb_mgr.get_pixmap.return_value = None

    queue = ThumbnailRenderQueue(mock_compiler, mock_thumb_mgr, max_workers=2)

    failed_received = []
    queue.signals.failed.connect(lambda qid, err, key: failed_received.append((qid, err, key)))

    queue.enqueue("q_fail1", 1, "bad_tex", "key_fail", {})
    queue.enqueue("q_fail2", 1, "bad_tex", "key_fail", {})

    start = time.monotonic()
    while len(failed_received) < 2 and time.monotonic() - start < 5.0:
        QCoreApplication.processEvents()
        time.sleep(0.02)

    assert len(failed_received) == 2
    failed_qids = {f[0] for f in failed_received}
    assert failed_qids == {"q_fail1", "q_fail2"}
    assert "syntax error" in failed_received[0][1]
    queue.shutdown()


def test_j71_subscriber_cancellation(qapp, tmp_path):
    """J.7.1: Một subscriber bị hủy thì subscriber còn lại vẫn nhận kết quả, không nhận dư."""
    pdf_path = create_dummy_pdf(tmp_path)
    mock_compiler = MagicMock()
    mock_compiler.compile.return_value = CompileResult(ok=True, pdf=pdf_path, log="OK")
    mock_thumb_mgr = MagicMock()
    mock_thumb_mgr.get_pixmap.return_value = None

    queue = ThumbnailRenderQueue(mock_compiler, mock_thumb_mgr, max_workers=2)
    queue._paused = True

    received = []
    queue.signals.ready.connect(lambda qid, rev, src, pix, key: received.append((qid, rev, key)))

    queue.enqueue("q_stay", 1, "tex", "key_cancel", {})
    queue.enqueue("q_leave", 1, "tex", "key_cancel", {})

    # Cancel q_leave
    queue.cancel_question("q_leave")
    assert queue.subscriber_count("key_cancel") == 1

    queue._paused = False
    queue._schedule_next()

    start = time.monotonic()
    while not received and time.monotonic() - start < 5.0:
        QCoreApplication.processEvents()
        time.sleep(0.02)

    # Allow loop to settle
    for _ in range(5):
        QCoreApplication.processEvents()
        time.sleep(0.01)

    assert len(received) == 1
    assert received[0][0] == "q_stay"
    queue.shutdown()


def test_j71_generation_filter_change_isolation(qapp, tmp_path):
    """J.7.1: Khi đổi bộ lọc (cancel_all_pending), subscriber cũ bị loại bỏ an toàn."""
    pdf_path = create_dummy_pdf(tmp_path)
    
    def delayed_compile(src, assets, cancelled):
        time.sleep(0.1)
        return CompileResult(ok=True, pdf=pdf_path, log="OK")

    mock_compiler = MagicMock()
    mock_compiler.compile.side_effect = delayed_compile
    mock_thumb_mgr = MagicMock()
    mock_thumb_mgr.get_pixmap.return_value = None

    queue = ThumbnailRenderQueue(mock_compiler, mock_thumb_mgr, max_workers=2)

    received = []
    queue.signals.ready.connect(lambda qid, rev, src, pix, key: received.append((qid, rev, key)))

    # Start Q1
    queue.enqueue("q_old_filter", 1, "tex", "key_gen", {})
    # User immediately types in search filter -> cancel pending & bump generation
    queue.cancel_all_pending()

    # Now in new filter, user expands Q2 with same key
    queue.enqueue("q_new_filter", 1, "tex", "key_gen", {})

    start = time.monotonic()
    while not received and time.monotonic() - start < 5.0:
        QCoreApplication.processEvents()
        time.sleep(0.02)

    # Q_old_filter was discarded due to generation change, Q_new_filter received result
    assert len(received) == 1
    assert received[0][0] == "q_new_filter"
    queue.shutdown()


def test_j71_hundred_enqueues_same_key_compiles_exactly_once(qapp, tmp_path):
    """J.7.1: 100 lần enqueue cùng key chỉ compile đúng 1 lần và phát đủ 100 signals."""
    pdf_path = create_dummy_pdf(tmp_path)
    mock_compiler = MagicMock()
    mock_compiler.compile.return_value = CompileResult(ok=True, pdf=pdf_path, log="OK")
    mock_thumb_mgr = MagicMock()
    mock_thumb_mgr.get_pixmap.return_value = None

    queue = ThumbnailRenderQueue(mock_compiler, mock_thumb_mgr, max_workers=2)
    queue._paused = True

    received = []
    queue.signals.ready.connect(lambda qid, rev, src, pix, key: received.append((qid, rev, key)))

    for i in range(100):
        queue.enqueue(f"q_{i}", 1, "shared_latex", "key_100", {}, priority=RenderPriority.VIEWPORT)

    assert queue.subscriber_count("key_100") == 100
    assert len(queue._pending) == 1

    queue._paused = False
    queue._schedule_next()

    start = time.monotonic()
    while len(received) < 100 and time.monotonic() - start < 5.0:
        QCoreApplication.processEvents()
        time.sleep(0.02)

    assert len(received) == 100
    assert mock_compiler.compile.call_count == 1
    queue.shutdown()


def test_j71_fast_cache_hit_bypasses_compiler(qapp, tmp_path):
    """J.7.1: Nếu cache đã có sẵn ảnh, trả kết quả tức thì không gọi compiler."""
    mock_compiler = MagicMock()
    mock_thumb_mgr = MagicMock()
    cached_pixmap = QPixmap(50, 50)
    mock_thumb_mgr.get_pixmap.return_value = cached_pixmap

    queue = ThumbnailRenderQueue(mock_compiler, mock_thumb_mgr, max_workers=2)

    received = []
    queue.signals.ready.connect(lambda qid, rev, src, pix, key: received.append((qid, rev, key)))

    queue.enqueue("q_cached", 2, "tex", "key_cached", {})

    assert len(received) == 1
    assert received[0][0] == "q_cached"
    assert received[0][1] == 2
    assert not mock_compiler.compile.called
    assert queue.pending_count() == 0
    assert queue.active_count() == 0
    queue.shutdown()


def test_j72_shutdown_while_active_kills_subprocesses_and_aborts(qapp, tmp_path):
    """J.7.2: Shutdown khi compiler đang chạy gọi kill_all_active và thoát sạch."""
    mock_compiler = MagicMock()
    
    def long_compile(src, assets, cancelled):
        for _ in range(50):
            if cancelled():
                return CompileResult(False, None, "Cancelled", cancelled=True)
            time.sleep(0.05)
        return CompileResult(True, tmp_path / "never.pdf", "Done")

    mock_compiler.compile.side_effect = long_compile
    mock_thumb_mgr = MagicMock()
    mock_thumb_mgr.get_pixmap.return_value = None

    queue = ThumbnailRenderQueue(mock_compiler, mock_thumb_mgr, max_workers=2)

    # Start long compile
    queue.enqueue("q_long", 1, "tex", "key_long", {})
    assert "key_long" in queue._active

    # Immediately shutdown
    t0 = time.monotonic()
    queue.shutdown(timeout_ms=2000)
    duration = time.monotonic() - t0

    assert duration < 2.5
    assert mock_compiler.kill_all_active.called
    assert queue.pending_count() == 0
    assert queue.active_count() == 0
    assert queue.subscriber_count() == 0


def test_j72_main_window_close_event_cancel_preserves_queue_and_open_editor(qtbot, tmp_path, monkeypatch):
    """J.7.2: Khi có tab chưa lưu và người dùng chọn Cancel, MainWindow không đóng và không shutdown queue."""
    config = AppConfig(data_dir=tmp_path / "data")
    services = create_services(config)
    q = services.questions.create(r"\begin{ex}BanDau\end{ex}")

    window = MainWindow(services)
    qtbot.addWidget(window)
    editor = window.open_question(q.id)
    editor.insertPlainText("ThayDoiNhungChuaLuu ")
    assert editor.document().isModified()

    # User clicks Cancel in QMessageBox
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Cancel)

    # Attempt to close window
    closed = window.close()
    assert not closed  # Window close must be cancelled

    # Verify queue is NOT shutdown and can still accept jobs
    assert hasattr(window, "render_queue")
    assert not window.render_queue._is_shutdown

    # Now simulate user choosing Discard to close cleanly
    monkeypatch.setattr(QMessageBox, "question", lambda *args: QMessageBox.StandardButton.Discard)
    closed = window.close()
    assert closed
