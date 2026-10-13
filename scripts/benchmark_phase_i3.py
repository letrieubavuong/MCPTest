import ctypes
from ctypes import wintypes
import json
import os
import sys
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')
import time
from pathlib import Path
from typing import Dict, List, Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import QByteArray, QBuffer, QIODevice

from latex_question_studio.preview.compiler import Compiler, BUILTIN_PREAMBLE
from latex_question_studio.preview.thumbnails import ThumbnailManager


def get_peak_ram_bytes() -> int:
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

    psapi = ctypes.windll.psapi
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.GetCurrentProcess()
    counters = PROCESS_MEMORY_COUNTERS()
    counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    if psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
        return counters.PeakWorkingSetSize
    return 0


def create_sample_assets(target_dir: Path) -> Dict[str, Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    assets = {}
    names = ["diagram.png", "fig_circle.png", "asset_graph.png", "molecule.png", "mach_dien.png"]
    for idx, name in enumerate(names):
        p = target_dir / name
        img = QImage(300, 200, QImage.Format.Format_ARGB32)
        img.fill(0xfff0f0f0)
        buf = QByteArray()
        buffer = QBuffer(buf)
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        img.save(buffer, "PNG")
        p.write_bytes(bytes(buf.data()))
        assets[name] = p
    return assets


def get_benchmark_questions(assets: Dict[str, Path]) -> List[Dict[str, Any]]:
    questions = []

    # 1. Công thức toán thông thường (25 câu)
    math_templates = [
        r"\begin{ex} Tính đạo hàm của $f(x) = \frac{x^2 + 1}{x - 1}$. \loigiai{Ta có $f'(x) = \frac{x^2 - 2x - 1}{(x-1)^2}$.} \end{ex}",
        r"\begin{ex} Tính tích phân $I = \int_0^1 (2x + 1) e^x \,dx$. \loigiai{$I = [(2x-1)e^x]_0^1 = e + 1$.} \end{ex}",
        r"\begin{ex} Tìm nghiệm của phương trình $\log_2(x^2 - 3) = 1$. \loigiai{$x^2 - 3 = 2 \iff x = \pm\sqrt{5}$.} \end{ex}",
        r"\begin{ex} Giải hệ phương trình $\heva{2x + y = 5 \\ x - 3y = -1}$. \loigiai{Nghiệm là $(x;y) = (2;1)$.} \end{ex}",
        r"\begin{ex} Tính giới hạn $L = \lim_{x \to 0} \frac{\sqrt{1+2x} - 1}{x}$. \loigiai{$L = \lim_{x\to 0}\frac{2}{\sqrt{1+2x}+1} = 1$.} \end{ex}",
        r"\begin{ex} Cho số phức $z = 3 - 4i$. Tính môđun $|z|$. \loigiai{$|z| = \sqrt{3^2 + (-4)^2} = 5$.} \end{ex}",
        r"\begin{ex} Tìm nguyên hàm của hàm số $f(x) = \sin 2x + \cos x$. \loigiai{$F(x) = -\frac{1}{2}\cos 2x + \sin x + C$.} \end{ex}",
        r"\begin{ex} Cho cấp số nhân có $u_1 = 3, q = 2$. Tính $u_5$. \loigiai{$u_5 = 3 \cdot 2^4 = 48$.} \end{ex}",
        r"\begin{ex} Trong không gian $Oxyz$, tính khoảng cách từ điểm $M(1;2;3)$ đến mặt phẳng $(P): 2x - 2y + z - 5 = 0$. \loigiai{$d = \frac{|2 - 4 + 3 - 5|}{\sqrt{4+4+1}} = \frac{4}{3}$.} \end{ex}",
        r"\begin{ex} Tính định thức ma trận $A = \begin{pmatrix} 2 & 3 \\ 1 & 4 \end{pmatrix}$. \loigiai{$\det(A) = 8 - 3 = 5$.} \end{ex}",
        r"\begin{ex} Giải bất phương trình $3^{2x-1} > 27$. \loigiai{$2x - 1 > 3 \iff x > 2$.} \end{ex}",
        r"\begin{ex} Tìm giá trị lớn nhất của hàm số $y = \sqrt{4 - x^2}$. \loigiai{$\max y = 2$ tại $x = 0$.} \end{ex}",
        r"\begin{ex} Cho tam giác $ABC$ có $a=7, b=8, c=5$. Tính $\cos A$. \loigiai{$\cos A = \frac{b^2+c^2-a^2}{2bc} = \frac{64+25-49}{80} = \frac{1}{2}$.} \end{ex}",
        r"\begin{ex} Khai triển nhị thức Newton $(x + 2)^4$. \loigiai{$(x+2)^4 = x^4 + 8x^3 + 24x^2 + 32x + 16$.} \end{ex}",
        r"\begin{ex} Tìm tập xác định của $y = \frac{\sqrt{x-1}}{x-3}$. \loigiai{$D = [1; +\infty) \setminus \{3\}$.} \end{ex}",
        r"\begin{ex} Tìm tiệm cận ngang của đồ thị hàm số $y = \frac{3x - 1}{x + 2}$. \loigiai{Tiệm cận ngang $y = 3$.} \end{ex}",
        r"\begin{ex} Tính thể tích khối chóp có đáy diện tích $B = 12\,\text{cm}^2$ và chiều cao $h = 5\,\text{cm}$. \loigiai{$V = \frac{1}{3}Bh = 20\,\text{cm}^3$.} \end{ex}",
        r"\begin{ex} Cho hình lập phương có cạnh bằng $a$. Tính thể tích của nó. \loigiai{$V = a^3$.} \end{ex}",
        r"\begin{ex} Giải phương trình lượng giác $\sin x = \frac{1}{2}$. \loigiai{$x = \frac{\pi}{6} + k2\pi$ hoặc $x = \frac{5\pi}{6} + k2\pi$.} \end{ex}",
        r"\begin{ex} Tính đạo hàm cấp hai của $f(x) = x^4 - 3x^2 + 2$. \loigiai{$f''(x) = 12x^2 - 6$.} \end{ex}",
        r"\begin{ex} Viết phương trình mặt cầu tâm $I(1;-2;3)$ bán kính $R=4$. \loigiai{$(x-1)^2 + (y+2)^2 + (z-3)^2 = 16$.} \end{ex}",
        r"\begin{ex} Tính tích phân $\int_1^e \frac{\ln x}{x}\,dx$. \loigiai{$\int_1^e \ln x\,d(\ln x) = \left[\frac{\ln^2 x}{2}\right]_1^e = \frac{1}{2}$.} \end{ex}",
        r"\begin{ex} Tìm tọa độ giao điểm của $(d): y = 2x - 3$ và $(P): y = x^2 - 3x + 1$. \loigiai{$x^2 - 5x + 4 = 0 \iff x = 1$ hoặc $x = 4$.} \end{ex}",
        r"\begin{ex} Cho $\log_2 3 = a$. Tính $\log_2 18$ theo $a$. \loigiai{$\log_2 18 = 1 + 2\log_2 3 = 1 + 2a$.} \end{ex}",
        r"\begin{ex} Tìm điểm uốn của đồ thị hàm số $y = x^3 - 3x^2 + 2$. \loigiai{$y'' = 6x - 6 = 0 \iff x = 1 \implies U(1; 0)$.} \end{ex}",
    ]
    for idx, src in enumerate(math_templates):
        questions.append({"group": "1_math_formula", "id": f"g1_{idx+1:02d}", "source": src})

    # 2. Câu trắc nghiệm \choice (25 câu)
    for i in range(25):
        src = (
            rf"\begin{{ex}} Câu {i+1}: Trong thí nghiệm Brown, hạt phấn hoa chuyển động hỗn độn vì "
            rf"\choice{{giữa chúng có khoảng cách}}{{chúng là phân tử}}{{\True các phân tử nước va chạm từ mọi phía}}{{chúng là sinh vật sống}} "
            rf"\loigiai{{Phân tử chuyển động nhiệt không ngừng.}} \end{{ex}}"
        )
        questions.append({"group": "2_choice_mcq", "id": f"g2_{i+1:02d}", "source": src})

    # 3. Câu đúng sai \choiceTF (25 câu)
    for i in range(25):
        src = (
            rf"\begin{{ex}} Câu {i+1}: Xét chuyển động thẳng biến đổi đều của một vật có vận tốc ban đầu $v_0 = {i+2}\,\text{{m/s}}$ và gia tốc $a = 2\,\text{{m/s}}^2$. "
            rf"\choiceTF{{\True Vận tốc tăng dần theo thời gian.}}{{Quãng đường đi được tỉ lệ bậc nhất với thời gian.}}{{\True Đồ thị vận tốc là đường thẳng.}}{{Gia tốc thay đổi liên tục.}} "
            rf"\loigiai{{Chuyển động thẳng nhanh dần đều có $a=\text{{const}}$.}} \end{{ex}}"
        )
        questions.append({"group": "3_choice_tf", "id": f"g3_{i+1:02d}", "source": src})

    # 4. Câu trả lời ngắn \shortans (25 câu)
    for i in range(25):
        ans = (i + 1) * 2
        src = (
            rf"\begin{{ex}} Câu {i+1}: Một ô tô chuyển động thẳng đều trên đường thẳng với tốc độ $v = 15\,\text{{m/s}}$. "
            rf"Quãng đường ô tô đi được trong thời gian $t = {i+1}\,\text{{giây}}$ là bao nhiêu mét? "
            rf"\shortans{{{ans}}} "
            rf"\loigiai{{Áp dụng công thức $s = v \cdot t = 15 \cdot {i+1} = {ans}\,\text{{m}}$.}} \end{{ex}}"
        )
        questions.append({"group": "4_short_ans", "id": f"g4_{i+1:02d}", "source": src})

    # 5. Câu có \includegraphics (25 câu)
    asset_keys = list(assets.keys())
    for i in range(25):
        asset_name = asset_keys[i % len(asset_keys)]
        src = (
            rf"\begin{{ex}} Câu {i+1}: Quan sát hình ảnh thực nghiệm và xác định hiện tượng vật lí tương ứng. "
            rf"\begin{{center}}\includegraphics[width=5cm]{{{asset_name}}}\end{{center}} "
            rf"\choice{{Hiện tượng khúc xạ}}{{\True Hiện tượng mao dẫn}}{{Hiện tượng tán sắc}}{{Hiện tượng giao thoa}} "
            rf"\loigiai{{Hình vẽ minh họa hiện tượng mao dẫn chất lỏng trong ống nhỏ.}} \end{{ex}}"
        )
        questions.append({"group": "5_includegraphics", "id": f"g5_{i+1:02d}", "source": src, "assets": {asset_name: assets[asset_name]}})

    # 6. Câu có TikZ hoặc tkz-euclide (25 câu)
    tikz_shapes = [
        r"\draw[blue, thick] (0,0) circle (1.2); \draw[->, red] (0,0) -- (1.2,0) node[midway, above]{$R$};",
        r"\draw[thick] (0,0) -- (2,0) -- (1,1.5) -- cycle; \draw[dashed] (1,0) -- (1,1.5);",
        r"\draw[->] (-2,0) -- (2,0) node[right]{$x$}; \draw[->] (0,-1) -- (0,2) node[above]{$y$}; \draw[red, domain=-1.2:1.2] plot (\x, {\x*\x});",
        r"\draw[fill=yellow!30] (0,0) rectangle (2,1.2); \node at (1,0.6){$m = 2\,\text{kg}$};",
        r"\draw (0,0) grid (3,2); \draw[very thick, blue] (0,0) -- (3,2);",
    ]
    for i in range(25):
        shape = tikz_shapes[i % len(tikz_shapes)]
        src = (
            rf"\begin{{ex}} Câu {i+1}: Cho đồ thị biểu diễn mối liên hệ giữa các đại lượng vật lí như hình vẽ. "
            rf"\begin{{center}}\begin{{tikzpicture}}[scale=0.9] {shape} \end{{tikzpicture}}\end{{center}} "
            rf"\choice{{Đường parabol}}{{\True Đường biểu diễn thực nghiệm}}{{Đường hypebol}}{{Đường elip}} "
            rf"\loigiai{{Căn cứ vào dạng hình học của đồ thị.}} \end{{ex}}"
        )
        questions.append({"group": "6_tikz_diagram", "id": f"g6_{i+1:02d}", "source": src})

    # 7. Câu có bảng biểu (25 câu)
    for i in range(25):
        src = (
            rf"\begin{{ex}} Câu {i+1}: Cho bảng biến thiên của hàm số $y = f(x)$ trên khoảng $(-\infty; +\infty)$ như sau: "
            rf"\begin{{center}}\begin{{tabular}}{{|c|ccccc|}} \hline $x$ & $-\infty$ & & $0$ & & $+\infty$ \\ \hline $y'$ & & $+$ & $0$ & $-$ & \\ \hline $y$ & & $\nearrow$ & $2$ & $\searrow$ & \\ \hline \end{{tabular}}\end{{center}} "
            rf"Hàm số đạt cực đại tại điểm nào? "
            rf"\choice{{$x = -1$}}{{\True $x = 0$}}{{$x = 2$}}{{$x = 1$}} "
            rf"\loigiai{{Từ bảng biến thiên, $y'$ đổi dấu từ dương sang âm qua $x=0$, nên hàm số đạt cực đại tại $x=0$.}} \end{{ex}}"
        )
        questions.append({"group": "7_table_tabular", "id": f"g7_{i+1:02d}", "source": src})

    # 8. Câu sử dụng macro MAPClass (25 câu)
    for i in range(25):
        src = (
            rf"\loai{{Dạng {i+1}: Phân loại chuyên đề}} "
            rf"\begin{{ex}} Câu {i+1}: Tính chu kì dao động điều hòa của con lắc đơn có chiều dài $l = 1\,\text{{m}}$ tại nơi có $g = \pi^2\,\text{{m/s}}^2$. "
            rf"\motcot{{$1\,\text{{s}}$}}{{\True $2\,\text{{s}}$}}{{$3\,\text{{s}}$}}{{$4\,\text{{s}}$}} "
            rf"\loigiai{{Áp dụng $T = 2\pi\sqrt{{\frac{{l}}{{g}}}} = 2\pi\sqrt{{\frac{{1}}{{\pi^2}}}} = 2\,\text{{s}}$.}} "
            rf"\haidong{{2}} \end{{ex}}"
        )
        questions.append({"group": "8_mapclass_macro", "id": f"g8_{i+1:02d}", "source": src})

    return questions


def run_benchmark():
    app = QApplication.instance() or QApplication(sys.argv)
    output_dir = PROJECT_ROOT / "scratch" / "benchmark_run_phase_i3"
    output_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = output_dir / "thumbnails"
    assets_dir = output_dir / "assets"
    assets = create_sample_assets(assets_dir)

    questions = get_benchmark_questions(assets)
    total_q = len(questions)
    print(f"=== KHỞI CHẠY BENCHMARK PHASE I.3 VỚI {total_q} CÂU HỎI LATEX THỰC ===")

    compiler = Compiler(PROJECT_ROOT / "scratch" / "compiler_data")
    mgr = ThumbnailManager(cache_dir, disk_limit=256 * 1024 * 1024, ram_limit=128 * 1024 * 1024)

    group_metrics: Dict[str, Dict[str, Any]] = {}
    compile_success = 0
    compile_failures = []
    
    t_compile_list = []
    t_pdf2img_list = []
    t_webp_list = []
    t_png_list = []
    t_disk_cold_list = []
    t_ram_hot_list = []

    # Import pymupdf for step 2
    import pymupdf

    start_all = time.perf_counter()

    for idx, q_info in enumerate(questions):
        grp = q_info["group"]
        q_id = q_info["id"]
        src = q_info["source"]
        q_assets = q_info.get("assets", {})

        if grp not in group_metrics:
            group_metrics[grp] = {
                "count": 0, "success": 0, "fail": 0,
                "t_compile": [], "t_pdf2img": [], "t_webp": [],
                "t_png": [], "t_disk_cold": [], "t_ram_hot": [],
            }

        # 1. Đo thời gian biên dịch pdfLaTeX
        t0 = time.perf_counter()
        compile_res = compiler.compile(src, assets=q_assets)
        t_compile = (time.perf_counter() - t0) * 1000  # ms

        if not compile_res.ok:
            compile_failures.append({"id": q_id, "group": grp, "log": compile_res.log[-300:]})
            group_metrics[grp]["fail"] += 1
            print(f"[{idx+1}/{total_q}] FAIL: {q_id} ({grp})")
            continue

        compile_success += 1
        group_metrics[grp]["success"] += 1
        t_compile_list.append(t_compile)
        group_metrics[grp]["t_compile"].append(t_compile)

        # 2. Đo thời gian chuyển PDF sang ảnh PNG thô bằng PyMuPDF
        t0 = time.perf_counter()
        with pymupdf.open(compile_res.pdf) as doc:
            page = doc[0]
            rects = [pymupdf.Rect(b[:4]) for b in page.get_text("blocks")] + [d["rect"] for d in page.get_drawings()]
            clip = None
            for r in rects:
                clip = r if clip is None else clip | r
            if clip is not None:
                clip = (clip + (-10, -10, 10, 10)) & page.rect
            pixmap = page.get_pixmap(matrix=pymupdf.Matrix(1.2, 1.2), clip=clip)
            raw_png = pixmap.tobytes("png")
        t_pdf2img = (time.perf_counter() - t0) * 1000
        t_pdf2img_list.append(t_pdf2img)
        group_metrics[grp]["t_pdf2img"].append(t_pdf2img)

        # 3. Đo thời gian mã hóa WebP và lưu đĩa
        key_webp = f"{q_id}_webp"
        t0 = time.perf_counter()
        path_webp, fmt_webp = mgr.save(key_webp, raw_png, prefer_webp=True, quality=92)
        t_webp = (time.perf_counter() - t0) * 1000
        t_webp_list.append(t_webp)
        group_metrics[grp]["t_webp"].append(t_webp)

        # 4. Đo thời gian mã hóa PNG fallback
        key_png = f"{q_id}_png"
        t0 = time.perf_counter()
        path_png, fmt_png = mgr.save(key_png, raw_png, prefer_webp=False)
        t_png = (time.perf_counter() - t0) * 1000
        t_png_list.append(t_png)
        group_metrics[grp]["t_png"].append(t_png)

        # 5. Đo thời gian đọc cold disk cache (xóa RAM cache trước)
        mgr._ram_cache.clear()
        mgr._ram_usage = 0
        t0 = time.perf_counter()
        res_disk = mgr.get(key_webp)
        t_disk_cold = (time.perf_counter() - t0) * 1000
        t_disk_cold_list.append(t_disk_cold)
        group_metrics[grp]["t_disk_cold"].append(t_disk_cold)

        # 6. Đo thời gian đọc hot RAM cache (gọi get_pixmap lần 2)
        pix1 = mgr.get_pixmap(key_webp)  # warm into RAM
        t0 = time.perf_counter()
        pix2 = mgr.get_pixmap(key_webp)  # hot read
        t_ram_hot = (time.perf_counter() - t0) * 1000
        t_ram_hot_list.append(t_ram_hot)
        group_metrics[grp]["t_ram_hot"].append(t_ram_hot)

        group_metrics[grp]["count"] += 1
        if (idx + 1) % 25 == 0:
            print(f"  -> Đã xử lý {idx+1}/{total_q} câu...")

    total_duration = time.perf_counter() - start_all

    # 7. Đo thông lượng hiển thị theo batch: 20, 50, 100 câu
    def measure_display_batch(n_items: int) -> float:
        subset_keys = [f"{questions[i]['id']}_webp" for i in range(min(n_items, compile_success))]
        t0 = time.perf_counter()
        for k in subset_keys:
            pix = mgr.get_pixmap(k)
            assert pix is not None and not pix.isNull()
        return (time.perf_counter() - t0) * 1000  # ms

    time_display_20 = measure_display_batch(20)
    time_display_50 = measure_display_batch(50)
    time_display_100 = measure_display_batch(100)

    # 8. Đo dung lượng cache thực tế và Peak RAM
    webp_files = list(cache_dir.glob("*.webp"))
    png_files = list(cache_dir.glob("*.png"))
    total_webp_bytes = sum(f.stat().st_size for f in webp_files)
    total_png_bytes = sum(f.stat().st_size for f in png_files)
    avg_webp_size = total_webp_bytes / max(1, len(webp_files))
    avg_png_size = total_png_bytes / max(1, len(png_files))

    peak_ram_bytes = get_peak_ram_bytes()
    peak_ram_mb = peak_ram_bytes / (1024 * 1024)

    results = {
        "summary": {
            "total_questions": total_q,
            "compile_success": compile_success,
            "compile_failures": len(compile_failures),
            "success_rate": f"{(compile_success / total_q) * 100:.1f}%",
            "total_duration_sec": round(total_duration, 2),
            "peak_ram_mb": round(peak_ram_mb, 2),
            "current_mgr_ram_mb": round(mgr.ram_usage() / (1024 * 1024), 2),
            "mgr_cached_items": mgr.ram_count(),
            "mgr_decoded_pixmaps": mgr.pixmap_count(),
        },
        "timings_ms": {
            "compile_pdflatex": {
                "avg": round(sum(t_compile_list) / len(t_compile_list), 2),
                "min": round(min(t_compile_list), 2),
                "max": round(max(t_compile_list), 2),
            },
            "pdf_to_img": {
                "avg": round(sum(t_pdf2img_list) / len(t_pdf2img_list), 2),
                "min": round(min(t_pdf2img_list), 2),
                "max": round(max(t_pdf2img_list), 2),
            },
            "encode_webp": {
                "avg": round(sum(t_webp_list) / len(t_webp_list), 2),
                "min": round(min(t_webp_list), 2),
                "max": round(max(t_webp_list), 2),
            },
            "encode_png": {
                "avg": round(sum(t_png_list) / len(t_png_list), 2),
                "min": round(min(t_png_list), 2),
                "max": round(max(t_png_list), 2),
            },
            "disk_cold_read": {
                "avg": round(sum(t_disk_cold_list) / len(t_disk_cold_list), 3),
                "min": round(min(t_disk_cold_list), 3),
                "max": round(max(t_disk_cold_list), 3),
            },
            "ram_hot_read": {
                "avg": round(sum(t_ram_hot_list) / len(t_ram_hot_list), 4),
                "min": round(min(t_ram_hot_list), 4),
                "max": round(max(t_ram_hot_list), 4),
            },
        },
        "display_throughput_ms": {
            "display_20_questions": round(time_display_20, 2),
            "display_50_questions": round(time_display_50, 2),
            "display_100_questions": round(time_display_100, 2),
        },
        "cache_storage": {
            "webp_count": len(webp_files),
            "webp_total_bytes": total_webp_bytes,
            "webp_avg_bytes": round(avg_webp_size, 1),
            "png_count": len(png_files),
            "png_total_bytes": total_png_bytes,
            "png_avg_bytes": round(avg_png_size, 1),
            "storage_saved_percent": round((1 - total_webp_bytes / max(1, total_png_bytes)) * 100, 1),
        },
        "groups": {},
        "failures": compile_failures,
    }

    for grp, m in group_metrics.items():
        results["groups"][grp] = {
            "count": m["count"],
            "success": m["success"],
            "fail": m["fail"],
            "t_compile_avg": round(sum(m["t_compile"]) / max(1, len(m["t_compile"])), 2),
            "t_pdf2img_avg": round(sum(m["t_pdf2img"]) / max(1, len(m["t_pdf2img"])), 2),
            "t_webp_avg": round(sum(m["t_webp"]) / max(1, len(m["t_webp"])), 2),
            "t_disk_cold_avg": round(sum(m["t_disk_cold"]) / max(1, len(m["t_disk_cold"])), 3),
            "t_ram_hot_avg": round(sum(m["t_ram_hot"]) / max(1, len(m["t_ram_hot"])), 4),
        }

    # Write JSON results
    json_path = PROJECT_ROOT / "scratch" / "benchmark_phase_i3.json"
    json_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[OK] Đã ghi kết quả JSON vào: {json_path}")
    print(f"Tổng kết: {compile_success}/{total_q} thành công ({results['summary']['success_rate']})")
    print(f"Thời gian trung bình biên dịch pdfLaTeX: {results['timings_ms']['compile_pdflatex']['avg']} ms")
    print(f"Thời gian trung bình chuyển PDF sang ảnh: {results['timings_ms']['pdf_to_img']['avg']} ms")
    print(f"Thời gian trung bình mã hóa WebP: {results['timings_ms']['encode_webp']['avg']} ms")
    print(f"Thời gian đọc Cold Disk Cache: {results['timings_ms']['disk_cold_read']['avg']} ms")
    print(f"Thời gian đọc Hot RAM Cache: {results['timings_ms']['ram_hot_read']['avg']} ms")
    print(f"Hiển thị 20 câu: {time_display_20:.1f} ms, 50 câu: {time_display_50:.1f} ms, 100 câu: {time_display_100:.1f} ms")
    print(f"Dung lượng WebP trung bình: {avg_webp_size:.0f} bytes vs PNG: {avg_png_size:.0f} bytes (tiết kiệm {results['cache_storage']['storage_saved_percent']}%)")
    print(f"Peak RAM ứng dụng: {peak_ram_mb:.1f} MB")

    return results


if __name__ == "__main__":
    run_benchmark()
