r"""Benchmark tests for Phase K6.

Measures:
1. Card selection latency (p50, p95, max) with 100 questions in card mode.
2. 4-variant exam generation time for 40 questions (160 question instances across 4 sections).
3. MAPClass 4-part serializer speed (12 documents).
"""
import time
import statistics
import pytest
from PySide6.QtWidgets import QApplication
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.exams import ExamService
from latex_question_studio.ui.main_window import MainWindow


def test_phase_k_card_selection_latency_benchmark(qtbot, tmp_path):
    app = QApplication.instance() or QApplication([])
    services = create_services(AppConfig.load(tmp_path / 'app'))

    # Create 100 questions in the database
    for i in range(100):
        services.questions.create(f"\\begin{{ex}}Câu {i}?\\choice{{A}}{{B}}{{C}}{{\\True D}}\\end{{ex}}", 'mcq')

    win = MainWindow(services)
    qtbot.addWidget(win)
    win.show()

    lib_ui = win.library_ui
    lib_ui.mode.setCurrentIndex(1)  # Card mode
    lib_ui.sync_cards()
    assert lib_ui.cards.count() == 100

    latencies_ms = []
    # Measure 50 in-place selection toggles
    for i in range(50):
        target_idx = (i * 7) % 100
        t0 = time.perf_counter()
        item = lib_ui.cards.item(target_idx)
        item.setSelected(not item.isSelected())
        lib_ui.sync_cards()
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        latencies_ms.append(elapsed_ms)

    latencies_ms.sort()
    p50 = statistics.median(latencies_ms)
    p95 = latencies_ms[int(len(latencies_ms) * 0.95)]
    max_lat = max(latencies_ms)

    print(f"\n[BENCHMARK] sync_cards In-place Selection Latency (100 cards):")
    print(f"  - p50: {p50:.3f} ms")
    print(f"  - p95: {p95:.3f} ms")
    print(f"  - max: {max_lat:.3f} ms")

    assert p50 < 10.0, f"p50 too high: {p50}ms"
    assert p95 < 25.0, f"p95 too high: {p95}ms"


def test_phase_k_multi_variant_generation_benchmark(tmp_path):
    services = create_services(AppConfig.load(tmp_path / 'app'))
    exam = ExamService(services)

    # 40 questions total across all 4 parts:
    # 20 MCQ, 10 True/False, 5 Short Answer, 5 Essay
    q_ids = []
    for i in range(20):
        q = services.questions.create(f"\\begin{{ex}}Câu trắc nghiệm {i}?\\choice{{A}}{{\\True B}}{{C}}{{D}}\\loigiai{{LG {i}}}\\end{{ex}}", 'mcq')
        q_ids.append(q.id)
    for i in range(10):
        q = services.questions.create(f"\\begin{{ex}}Câu đúng sai {i}?\\choiceTF{{\\True A}}{{B}}{{\\True C}}{{D}}\\loigiai{{LG {i}}}\\end{{ex}}", 'true_false')
        q_ids.append(q.id)
    for i in range(5):
        q = services.questions.create(f"\\begin{{ex}}Câu ngắn {i}?\\shortans{{{i*2}}}\\loigiai{{LG {i}}}\\end{{ex}}", 'short_answer')
        q_ids.append(q.id)
    for i in range(5):
        q = services.questions.create(f"\\begin{{ex}}Câu tự luận {i}?\\loigiai{{LG {i}}}\\end{{ex}}", 'essay')
        q_ids.append(q.id)

    # Benchmark 4 variants generation
    t_start = time.perf_counter()
    snapshots = []
    for v in range(1, 5):
        code = f"De{v:02d}"
        _, snap = exam.generate(
            f"ĐỀ KHẢO SÁT CHẤT LƯỢNG MÔN TOÁN - MÃ {code}",
            manual_ids=q_ids,
            seed=500 + v,
            exam_code=code
        )
        snapshots.append(snap)
    gen_duration = time.perf_counter() - t_start

    print(f"\n[BENCHMARK] 4 Variants Generation (40 questions each = 160 question instances):")
    print(f"  - Total Time: {gen_duration*1000.0:.2f} ms ({gen_duration:.4f} s)")
    print(f"  - Average per Variant: {gen_duration/4.0*1000.0:.2f} ms")

    # Benchmark serialization of 12 documents (4 student, 4 teacher, 4 answers)
    t_ser = time.perf_counter()
    for snap in snapshots:
        _ = exam.content(snap, solutions=False)
        _ = exam.content(snap, solutions=True)
        _ = exam.content(snap, answer_only=True)
    ser_duration = time.perf_counter() - t_ser

    print(f"[BENCHMARK] 12 Documents Serialization (4-Part MAPClass Contract):")
    print(f"  - Total Time: {ser_duration*1000.0:.2f} ms ({ser_duration:.4f} s)")
    print(f"  - Average per Document: {ser_duration/12.0*1000.0:.2f} ms")

    assert gen_duration < 15.0, f"Generation took too long: {gen_duration}s"
    assert ser_duration < 0.5, f"Serialization took too long: {ser_duration}s"
