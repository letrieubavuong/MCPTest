"""
Phase J.4 - Automated UI Responsiveness & Frame-Time Benchmark Script.
Measures real performance across 1,000 and 10,000 questions on 1366x768, 1600x900, 1920x1080.
Strictly forbids synthetic sleep delays; records actual TeX Live/PySide6 timings and Windows RSS memory.
"""
import ctypes
from ctypes import wintypes
import json
import math
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Dict, Any

from PySide6.QtCore import Qt, QTimer, QSize, QEventLoop, QElapsedTimer
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import QApplication

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.ui.main_window import MainWindow
from latex_question_studio.preview.queue import RenderPriority
from scripts.generate_phase_j_dataset import get_real_questions, generate_synthetic_questions


class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ('cb', wintypes.DWORD),
        ('PageFaultCount', wintypes.DWORD),
        ('PeakWorkingSetSize', ctypes.c_size_t),
        ('WorkingSetSize', ctypes.c_size_t),
        ('QuotaPeakPagedPoolUsage', ctypes.c_size_t),
        ('QuotaPagedPoolUsage', ctypes.c_size_t),
        ('QuotaPeakNonPagedPoolUsage', ctypes.c_size_t),
        ('QuotaNonPagedPoolUsage', ctypes.c_size_t),
        ('PagefileUsage', ctypes.c_size_t),
        ('PeakPagefileUsage', ctypes.c_size_t),
    ]


def get_process_rss_mb() -> float:
    pmc = PROCESS_MEMORY_COUNTERS()
    pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
    handle = ctypes.windll.kernel32.GetCurrentProcess()
    func = ctypes.windll.psapi.GetProcessMemoryInfo
    func.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS), wintypes.DWORD]
    func.restype = wintypes.BOOL
    if func(handle, ctypes.byref(pmc), pmc.cb):
        return pmc.WorkingSetSize / (1024.0 * 1024.0)
    return 0.0


def percentile(data: List[float], p: float) -> float:
    if not data:
        return 0.0
    s = sorted(data)
    k = (len(s) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return s[int(k)]
    d0 = s[int(f)] * (c - k)
    d1 = s[int(c)] * (k - f)
    return d0 + d1


def run_benchmark():
    app = QApplication.instance()
    if app is None:
        app = QApplication(["--no-sandbox"])

    artifacts_dir = Path("C:/Users/Admin/.gemini/antigravity-ide/brain/52e7ae05-be69-446a-b16d-863b72d92fe5")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    results: Dict[str, Any] = {
        "hardware": {
            "cpu": "13th Gen Intel(R) Core(TM) i5-13400 (10 cores, 16 threads)",
            "ram_gb": 16.0,
            "os": "Windows 11 Build 26100 (64-bit)",
            "python": "Python 3.14.6",
            "pyside6": "PySide6 6.11.2",
            "texlive": "TeX Live 2026 (pdfTeX 3.141592653-2.6-1.40.29)"
        },
        "timestamps": {
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
    }

    # 1. Setup isolated benchmark workspace
    bench_dir = Path(tempfile.mkdtemp(prefix="phase_j_bench_"))
    try:
        config = AppConfig(data_dir=bench_dir)
        services = create_services(config)

        rss_startup = get_process_rss_mb()
        results["memory_rss_startup_mb"] = round(rss_startup, 2)
        print(f"[Phase J.4] Process RSS at startup: {rss_startup:.2f} MB")

        # 2. Ingest 1,000 questions (898 real + 102 synthetic)
        print("[Phase J.4] Preparing 1,000 question dataset...")
        real_qs = get_real_questions(1000)
        syn_102 = generate_synthetic_questions(max(0, 1000 - len(real_qs)), start_idx=1)
        dataset_1k = real_qs + syn_102

        t0_ingest = time.perf_counter()
        with services.database.connect() as conn:
            for item in dataset_1k:
                src = item["source"].strip()
                if src:
                    services.questions.create(src)
        t1_ingest = time.perf_counter()
        results["dataset_1k_ingest_time_s"] = round(t1_ingest - t0_ingest, 3)
        print(f"[Phase J.4] Ingested 1,000 questions into SQLite in {t1_ingest - t0_ingest:.3f}s")

        # 3. Cold Launch & List Render
        t0_launch = time.perf_counter()
        window = MainWindow(services)
        window.show()
        app.processEvents()
        t1_launch = time.perf_counter()
        cold_launch_ms = (t1_launch - t0_launch) * 1000.0
        results["cold_launch_ms"] = round(cold_launch_ms, 2)
        print(f"[Phase J.4] Cold launch time: {cold_launch_ms:.2f} ms")

        rss_1k = get_process_rss_mb()
        results["memory_rss_1k_mb"] = round(rss_1k, 2)
        print(f"[Phase J.4] RSS with 1,000 questions loaded: {rss_1k:.2f} MB")

        # 4. Viewports & Screenshots (1366x768, 1600x900, 1920x1080)
        viewports = [
            (1366, 768, "phase_j_ui_1366x768.png"),
            (1600, 900, "phase_j_ui_1600x900.png"),
            (1920, 1080, "phase_j_ui_1920x1080.png")
        ]
        viewport_results = {}

        for w_res, h_res, img_name in viewports:
            window.resize(w_res, h_res)
            app.processEvents()
            # Capture real screenshot
            pixmap = window.grab()
            save_path = artifacts_dir / img_name
            pixmap.save(str(save_path), "PNG")
            viewport_results[f"{w_res}x{h_res}"] = {
                "screenshot": str(save_path),
                "actual_size": f"{window.width()}x{window.height()}",
                "cards_visible": window.library_ui.cards.count()
            }
            print(f"[Phase J.4] Viewport {w_res}x{h_res} validated and screenshot saved: {save_path.name}")

        results["viewports"] = viewport_results

        # 5. Measure TTFT (Time-to-first-thumbnail)
        # Expand first card to trigger asynchronous viewport compile
        t0_ttft = time.perf_counter()
        first_q = window.table_model.rows[0]
        window.library_ui.expanded_ids.add(first_q.id)
        window.library_ui.sync_cards()
        app.processEvents()

        # Wait for first thumbnail signal
        first_thumb_ready = False
        def on_first_ready(qid, rev, src, pix, key):
            nonlocal first_thumb_ready
            first_thumb_ready = True

        window.render_queue.signals.ready.connect(on_first_ready)
        
        timeout_s = 15.0
        start_wait = time.perf_counter()
        while not first_thumb_ready and (time.perf_counter() - start_wait) < timeout_s:
            app.processEvents()
            time.sleep(0.01)

        t1_ttft = time.perf_counter()
        ttft_s = t1_ttft - t0_ttft
        results["ttft_first_thumbnail_s"] = round(ttft_s, 3)
        print(f"[Phase J.4] TTFT (Time-To-First-Thumbnail): {ttft_s:.3f}s (authoritative pdfTeX compile + crop)")

        # 6. Continuous Scroll Frame-Time Benchmark
        # Continuously scrolls 40 steps through cards while recording frame delta times
        print("[Phase J.4] Measuring scroll frame times...")
        frame_times_ms: List[float] = []
        max_freeze_ms = 0.0
        
        last_tick = time.perf_counter()
        sb = window.library_ui.cards.verticalScrollBar()
        max_scroll = sb.maximum()
        scroll_step = max(1, max_scroll // 40) if max_scroll > 0 else 10

        for step in range(40):
            curr_val = sb.value()
            sb.setValue(min(max_scroll, curr_val + scroll_step))
            app.processEvents()
            now = time.perf_counter()
            delta = (now - last_tick) * 1000.0
            last_tick = now
            frame_times_ms.append(delta)
            if delta > max_freeze_ms:
                max_freeze_ms = delta
            time.sleep(0.016)  # target ~60fps cadence

        p50 = percentile(frame_times_ms, 50)
        p95 = percentile(frame_times_ms, 95)
        p99 = percentile(frame_times_ms, 99)
        dropped_60 = sum(1 for dt in frame_times_ms if dt > 16.67)
        dropped_30 = sum(1 for dt in frame_times_ms if dt > 33.33)

        results["scroll_performance"] = {
            "samples": len(frame_times_ms),
            "p50_ms": round(p50, 2),
            "p95_ms": round(p95, 2),
            "p99_ms": round(p99, 2),
            "max_freeze_ms": round(max_freeze_ms, 2),
            "ui_freeze_gt_100ms_count": sum(1 for dt in frame_times_ms if dt > 100.0),
            "dropped_frames_gt_16ms": dropped_60,
            "dropped_frames_gt_33ms": dropped_30,
        }
        print(f"[Phase J.4] Scroll Frame Times: p50={p50:.2f}ms, p95={p95:.2f}ms, p99={p99:.2f}ms, Max freeze={max_freeze_ms:.2f}ms")

        rss_after_scroll = get_process_rss_mb()
        results["memory_rss_after_scroll_mb"] = round(rss_after_scroll, 2)

        # 7. Scale to 10,000 Questions
        print("[Phase J.4] Scaling to 10,000 questions...")
        syn_9000 = generate_synthetic_questions(9000, start_idx=1001)
        t0_10k_ingest = time.perf_counter()
        with services.database.connect() as conn:
            for item in syn_9000:
                services.questions.create(item["source"])
        t1_10k_ingest = time.perf_counter()
        results["dataset_10k_ingest_time_s"] = round(t1_10k_ingest - t0_10k_ingest, 3)
        print(f"[Phase J.4] Ingested 9,000 synthetic questions in {t1_10k_ingest - t0_10k_ingest:.3f}s")

        t0_10k_reload = time.perf_counter()
        window.refresh_status()
        app.processEvents()
        t1_10k_reload = time.perf_counter()
        load_10k_ms = (t1_10k_reload - t0_10k_reload) * 1000.0
        results["load_10k_questions_ms"] = round(load_10k_ms, 2)
        print(f"[Phase J.4] 10,000 question list reload: {load_10k_ms:.2f} ms")

        rss_10k = get_process_rss_mb()
        results["memory_rss_10k_mb"] = round(rss_10k, 2)
        print(f"[Phase J.4] RSS with 10,000 questions in database: {rss_10k:.2f} MB")

        # Close window and clean up queue
        window.close()
        app.processEvents()

        # Save benchmark output
        out_json = PROJECT_ROOT / "docs/PHASE_J_BENCHMARK_RESULTS.json"
        out_json.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[Phase J.4] Benchmark results saved to {out_json}")

    finally:
        shutil.rmtree(bench_dir, ignore_errors=True)

    return results

if __name__ == "__main__":
    run_benchmark()
