import os
import shutil
import time
from pathlib import Path
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import QByteArray, QBuffer, QIODevice

from latex_question_studio.preview.thumbnails import ThumbnailManager, ThumbnailResult
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.ui.main_window import MainWindow


def test_thumbnail_manager_disk_and_key(qapp, tmp_path):
    cache_dir = tmp_path / "cache" / "thumbnails"
    mgr = ThumbnailManager(cache_dir, disk_limit=10 * 1024 * 1024, ram_limit=2 * 1024 * 1024)

    # 1. Compute deterministic key
    source = r"\begin{ex} Cho hàm số $y=f(x)$. Tìm cực trị. \choice{A}{B}{\True C}{D} \end{ex}"
    key1 = mgr.compute_key(source=source, preamble=r"\documentclass{article}")
    key2 = mgr.compute_key(source=source, preamble=r"\documentclass{article}")
    assert key1 == key2
    assert len(key1) == 64  # SHA-256

    # 2. Key changes when source or dependencies change
    key_diff = mgr.compute_key(source=source + " ", preamble=r"\documentclass{article}")
    assert key1 != key_diff

    # 3. Create a test image
    img = QImage(120, 80, QImage.Format.Format_RGB32)
    img.fill(0xffffff)
    buf = QByteArray()
    buffer = QBuffer(buf)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buffer, "PNG")
    png_bytes = bytes(buf.data())

    # 4. Save and verify standalone disk file (no Base64 in SQLite)
    file_path, fmt = mgr.save(key1, png_bytes, prefer_webp=True)
    assert file_path.is_file()
    assert file_path.suffix in (".webp", ".png")
    assert file_path.parent == cache_dir

    # 5. Retrieve from cache
    res = mgr.get(key1)
    assert res is not None
    data, returned_fmt, returned_path = res
    assert returned_path == file_path
    assert returned_fmt == fmt
    assert len(data) > 0

    # 6. Retrieve as QPixmap
    pix = mgr.get_pixmap(key1)
    assert pix is not None
    assert not pix.isNull()
    assert pix.width() == 120
    assert pix.height() == 80


def test_webp_encoding_and_fallback(qapp, tmp_path):
    cache_dir = tmp_path / "thumbnails"
    mgr = ThumbnailManager(cache_dir)

    img = QImage(160, 90, QImage.Format.Format_ARGB32)
    img.fill(0xffffff)
    buf = QByteArray()
    buffer = QBuffer(buf)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buffer, "PNG")
    png_bytes = bytes(buf.data())

    # WebP preferred
    path_webp, fmt_webp = mgr.save("key_webp", png_bytes, prefer_webp=True, quality=90)
    assert fmt_webp == "webp"
    assert path_webp.suffix == ".webp"
    assert path_webp.stat().st_size > 0

    # Fallback / PNG preferred
    path_png, fmt_png = mgr.save("key_png", png_bytes, prefer_webp=False)
    assert fmt_png == "png"
    assert path_png.suffix == ".png"
    assert path_png.stat().st_size > 0


def test_lru_limits_and_safe_clear(qapp, tmp_path):
    cache_dir = tmp_path / "thumbnails"
    # Small limits: 50 KB disk, 10 KB RAM to test eviction
    mgr = ThumbnailManager(cache_dir, disk_limit=50 * 1024, ram_limit=10 * 1024)

    # Assets folder to verify pristine isolation
    assets_dir = tmp_path / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    orig_asset = assets_dir / "diagram.png"
    orig_asset.write_bytes(b"ORIGINAL_ASSET_DO_NOT_DELETE")

    # Generate test image ~2 KB
    img = QImage(100, 100, QImage.Format.Format_RGB32)
    img.fill(0x123456)
    buf = QByteArray()
    buffer = QBuffer(buf)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buffer, "PNG")
    raw_bytes = bytes(buf.data())

    # Add 40 items to trigger both RAM and disk LRU eviction
    for i in range(40):
        mgr.save(f"thumb_{i:03d}", raw_bytes, prefer_webp=False)

    # Disk usage must be under or around limit
    disk_size = mgr.disk_usage()
    assert disk_size <= 55 * 1024, f"Disk size {disk_size} exceeded limit"

    # RAM usage must be under or around limit
    ram_size = mgr.ram_usage()
    assert ram_size <= 15 * 1024, f"RAM size {ram_size} exceeded limit"

    # Test safe clear cache
    cleared = mgr.clear_cache(preserve_assets=True)
    assert cleared > 0
    assert mgr.disk_usage() == 0
    assert mgr.ram_usage() == 0

    # VERIFY: Original assets remain intact!
    assert orig_asset.is_file()
    assert orig_asset.read_bytes() == b"ORIGINAL_ASSET_DO_NOT_DELETE"


def test_200_questions_benchmark(qapp, tmp_path):
    """
    Benchmark thumbnail generation, key computation, LRU caching,
    and cache hit latency with 200 diverse questions.
    """
    cache_dir = tmp_path / "benchmark_cache"
    mgr = ThumbnailManager(cache_dir, disk_limit=100 * 1024 * 1024, ram_limit=20 * 1024 * 1024)

    # 1. Synthesize 200 questions across 5 typical categories
    categories = [
        "inline_math",
        "display_math_matrix",
        "table_tabular",
        "tikz_diagram",
        "mapclass_long_problem",
    ]
    questions = []
    for i in range(200):
        cat = categories[i % len(categories)]
        if cat == "inline_math":
            source = rf"\begin{{ex}} Câu {i+1}: Cho cấp số cộng có $u_1={i}$, công sai $d=3$. Tìm $u_{{10}}$. \choice{{${i+27}$}}{{\True ${i+30}$}}{{${i+33}$}}{{${i+36}$}} \loigiai{{Áp dụng $u_n=u_1+(n-1)d$.}} \end{{ex}}"
        elif cat == "display_math_matrix":
            source = rf"\begin{{ex}} Câu {i+1}: Tính định thức ma trận $A = \begin{{pmatrix}} 1 & {i} \\ 2 & {i*2} \end{{pmatrix}}$. \choice{{0}}{{\True 1}}{{2}}{{3}} \end{{ex}}"
        elif cat == "table_tabular":
            source = rf"\begin{{ex}} Câu {i+1}: Cho bảng biến thiên sau: \begin{{tabular}}{{|c|cc|}} \hline $x$ & $-\infty$ & $+\infty$ \\ \hline $y'$ & + & - \\ \hline \end{{tabular}} \choice{{A}}{{B}}{{\True C}}{{D}} \end{{ex}}"
        elif cat == "tikz_diagram":
            source = rf"\begin{{ex}} Câu {i+1}: Cho hình vẽ \begin{{tikzpicture}} \draw (0,0) -- ({i % 5}, {i % 4}); \end{{tikzpicture}} \shortans{{{i}}} \end{{ex}}"
        else:
            source = rf"\begin{{vidu}} Ví dụ {i+1}: [MAPClass GV1] Giải phương trình bậc hai $x^2 - {i}x + {i-1} = 0$. \loigiai{{Nghiệm là $x=1$ hoặc $x={i-1}$.}} \end{{vidu}}"
        questions.append((f"q_{i:03d}", source))

    # Base image for benchmark mock renders
    img = QImage(140, 70, QImage.Format.Format_RGB32)
    img.fill(0xfafafa)
    buf = QByteArray()
    buffer = QBuffer(buf)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buffer, "PNG")
    raw_img = bytes(buf.data())

    # 2. Measure first write & key calculation for 200 questions
    start_time = time.perf_counter()
    keys = []
    webp_sizes = []
    for qid, src in questions:
        key = mgr.compute_key(src, preamble=r"\documentclass{article}")
        keys.append(key)
        path, fmt = mgr.save(key, raw_img, prefer_webp=True, quality=90)
        webp_sizes.append(path.stat().st_size)
    duration_cold = time.perf_counter() - start_time

    assert len(keys) == 200
    avg_cold_time = (duration_cold / 200) * 1000
    print(f"\n[BENCHMARK] 200 questions cold cache write + key compute: {duration_cold:.3f}s ({avg_cold_time:.2f}ms/câu)")

    # 3. Measure hot cache lookup for 200 questions
    start_hot = time.perf_counter()
    hits = 0
    for key in keys:
        res = mgr.get(key)
        if res is not None:
            hits += 1
    duration_hot = time.perf_counter() - start_hot
    avg_hot_time = (duration_hot / 200) * 1000
    print(f"[BENCHMARK] 200 questions hot cache lookup: {duration_hot:.4f}s ({avg_hot_time:.3f}ms/câu) - Cache Hit Rate: {hits/200*100:.1f}%")

    assert hits == 200, "All 200 items must be cache hits"
    assert avg_hot_time < 5.0, f"Hot cache lookup must be < 5ms per item, got {avg_hot_time:.3f}ms"

    # 4. Compare disk size: WebP vs PNG
    total_webp = sum(webp_sizes)
    # Save 10 as PNG to measure ratio
    png_sizes = []
    for i in range(10):
        p, _ = mgr.save(f"png_cmp_{i}", raw_img, prefer_webp=False)
        png_sizes.append(p.stat().st_size)
    avg_png = sum(png_sizes) / len(png_sizes)
    avg_webp = sum(webp_sizes) / len(webp_sizes)
    print(f"[BENCHMARK] Average File Size: WebP: {avg_webp:.0f} bytes, PNG: {avg_png:.0f} bytes (WebP savings: {(1 - avg_webp/avg_png)*100:.1f}%)")


def test_library_cards_load_cached_thumbnail(qtbot, tmp_path):
    services = create_services(AppConfig.load(tmp_path))
    q = services.questions.create(r"\begin{ex} Cho tam giác $ABC$. \choice{A}{B}{\True C}{D} \end{ex}")

    window = MainWindow(services)
    qtbot.addWidget(window)
    window.refresh_status()

    # Pre-populate thumbnail in thumbnail_manager
    config = window.compiler_config()
    k = window.library_ui.key(q, q.latex_source, config)
    import hashlib
    thumb_key = hashlib.sha256(str(k).encode("utf-8")).hexdigest()

    img = QImage(100, 50, QImage.Format.Format_RGB32)
    img.fill(0xffffff)
    buf = QByteArray()
    buffer = QBuffer(buf)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buffer, "PNG")
    png_bytes = bytes(buf.data())

    window.thumbnail_manager.save(thumb_key, png_bytes, prefer_webp=True)

    # Check that library_ui.cached retrieves it directly without running pdflatex
    cached_val = window.library_ui.cached(q, q.latex_source, config)
    assert cached_val is not None
    result, data, pages = cached_val
    assert result.ok is True
    assert result.cache_hit is True
    assert len(data) > 0

    # Switch to card view and verify sync_cards loads the thumbnail
    window.library_ui.mode.setCurrentIndex(1)
    window.library_ui.toggle_expand(q.id)

    # Check that the image was registered in library_ui.images
    assert q.id in window.library_ui.images
    rev, src, pix = window.library_ui.images[q.id]
    assert not pix.isNull()
    assert pix.width() == 100

    window.close()
