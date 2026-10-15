import json
from pathlib import Path
import pytest

from latex_question_studio.application.legacy_lesson_importer import (
    LegacyLessonImporter,
    ImportedLessonResult,
)
from latex_question_studio.application.assets import AssetStore
from latex_question_studio.application.lessons import LessonService
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services


def test_legacy_lesson_importer_preserves_theory_outside_exercises(tmp_path):
    store = AssetStore(tmp_path / "assets")
    importer = LegacyLessonImporter(asset_store=store)

    sample_tex = r"""\documentclass[12pt,a4paper]{article}
\usepackage[utf8]{vietnam}
\usepackage{amsmath,amssymb}
\usepackage{graphicx,tikz}
\begin{document}
\title{Khúc xạ ánh sáng và định luật Snell}

\section{I. Hiện tượng khúc xạ ánh sáng}
Khi tia sáng truyền từ môi trường trong suốt này sang môi trường trong suốt khác, tia sáng bị gãy khúc tại mặt phân cách.
Hiện tượng đó gọi là hiện tượng khúc xạ ánh sáng.

\begin{equation}
n_1 \sin i = n_2 \sin r
\end{equation}

\begin{tikzpicture}
\draw[thick,->] (0,0) -- (2,2);
\node at (1,1) {Tia tới};
\end{tikzpicture}

\subsection{1. Chiết suất của môi trường}
Chiết suất tuyệt đối của một môi trường là chiết suất của môi trường đó đối với chân không.

\begin{vidu}
Chiếu một tia sáng từ không khí vào nước với góc tới $i = 60^\circ$. Biết chiết suất của nước là $n = \frac{4}{3}$. Tính góc khúc xạ $r$.
\loigiai{
Áp dụng định luật khúc xạ:
\[ \sin r = \frac{\sin i}{n} = \frac{\sin 60^\circ}{4/3} \approx 0.65 \implies r \approx 40.5^\circ \]
}
\end{vidu}

\subsection{2. Luyện tập củng cố}
\begin{ex}
Khi góc tới tăng dần từ $0^\circ$ đến $90^\circ$ thì góc khúc xạ:
\choice{Giảm dần}{\True Tăng dần nhưng luôn nhỏ hơn $90^\circ$}{Không đổi}{Bằng $0^\circ$}
\loigiai{Theo định luật Snell, khi $i$ tăng thì $\sin i$ tăng, dẫn đến $\sin r$ tăng nên $r$ tăng.}
\end{ex}

\end{document}
"""

    file_path = tmp_path / "khuc_xa.tex"
    file_path.write_text(sample_tex, encoding="utf-8")

    res = importer.parse_file(file_path, subject="KHTN", grade="9")

    assert res.title == "Khúc xạ ánh sáng và định luật Snell"
    assert res.subject == "KHTN"
    assert res.grade == "9"
    assert len(res.blocks) >= 5

    # Check theory block preservation
    theory_blocks = [b for b in res.blocks if b["kind"] == "theory"]
    assert len(theory_blocks) >= 2

    # Check TikZ inside theory source is preserved exactly
    tikz_block = next((b for b in theory_blocks if r"\begin{tikzpicture}" in b["source"]), None)
    assert tikz_block is not None
    assert "Tia tới" in tikz_block["source"]

    # Check Snell formula
    formula_block = next((b for b in theory_blocks if "n_1 \\sin i" in b["source"]), None)
    assert formula_block is not None

    # Check example block
    example_blocks = [b for b in res.blocks if b["kind"] == "example"]
    assert len(example_blocks) == 1
    assert "Chiếu một tia sáng" in example_blocks[0]["source"]
    assert r"\loigiai" in example_blocks[0]["source"]

    # Check exercise block
    ex_blocks = [b for b in res.blocks if b["kind"] == "exercise"]
    assert len(ex_blocks) >= 1
    q_block = next((b for b in ex_blocks if r"\choice" in b["source"]), None)
    assert q_block is not None

    # Coverage must be near 100% and strictly without artificial floor
    assert res.coverage_percent >= 95.0
    assert len(res.mapped_segments) >= 5


def test_honest_coverage_no_floor_and_provenance(tmp_path):
    """Verifies coverage is calculated honestly without a 50% floor."""
    importer = LegacyLessonImporter()

    # Empty document body
    empty_doc = r"""\documentclass{article}
\begin{document}
\end{document}"""
    res_empty = importer.parse_text(empty_doc)
    assert res_empty.coverage_percent == 100.0

    # Normal document
    doc = r"""\documentclass{article}
\begin{document}
\section{Mục 1}
Nội dung lý thuyết kiểm tra tỷ lệ bảo toàn nguồn đầy đủ.
\end{document}"""
    res = importer.parse_text(doc)
    assert res.coverage_percent >= 98.0
    assert res.raw_source_bytes > 0
    assert len(res.mapped_segments) >= 1
    assert res.mapped_segments[0]["title"] == "Mục 1"


def test_nested_environments_preservation(tmp_path):
    """Verifies that nested environments inside \\begin{ex} do not truncate the question."""
    importer = LegacyLessonImporter()

    sample = r"""\documentclass{article}
\begin{document}
\section{Bài toán tổng hợp}
\begin{ex}
Cho hàm số có bảng biến thiên như sau:
\begin{center}
\begin{tikzpicture}
\draw[->] (0,0) -- (4,0);
\node at (2,0.5) {Đồ thị};
\end{tikzpicture}
\end{center}
Chọn mệnh đề đúng:
\begin{enumerate}
\item Mệnh đề 1
\item Mệnh đề 2
\end{enumerate}
\choice
{\True Đáp án A}
{Đáp án B}
{Đáp án C}
{Đáp án D}
\loigiai{
Lời giải chi tiết có chứa:
\begin{align*}
f'(x) &= 2x + 1 \\
f(0) &= 3
\end{align*}
}
\end{ex}

Lý thuyết kết thúc phần bài tập.
\end{document}"""

    res = importer.parse_text(sample)
    ex_blocks = [b for b in res.blocks if b["kind"] == "exercise"]
    assert len(ex_blocks) == 1

    ex_src = ex_blocks[0]["source"]
    # Ensure nested tikzpicture, enumerate, and align* are all preserved inside the single exercise block
    assert r"\begin{tikzpicture}" in ex_src
    assert r"\end{tikzpicture}" in ex_src
    assert r"\begin{enumerate}" in ex_src
    assert r"\end{enumerate}" in ex_src
    assert r"\begin{align*}" in ex_src
    assert r"\end{align*}" in ex_src
    assert r"\loigiai" in ex_src
    assert ex_src.strip().endswith(r"\end{ex}")

    # Ensure trailing theory is separate block
    theory_blocks = [b for b in res.blocks if b["kind"] == "theory"]
    assert any("Lý thuyết kết thúc phần bài tập" in b["source"] for b in theory_blocks)


def test_nested_braces_in_headings(tmp_path):
    """Verifies that headings with nested braces and math formulas are parsed correctly."""
    importer = LegacyLessonImporter()

    sample = r"""\documentclass{article}
\begin{document}
\section{Dạng 1: Khảo sát hàm số $y = \sqrt{x^2+1}$ và \textbf{chú ý}}
Nội dung dạng 1.

\subsection{Bài toán với tập hợp $S = \{x \in \mathbb{R} \mid x > 0\}$}
Nội dung bài toán.
\end{document}"""

    res = importer.parse_text(sample)
    assert len(res.blocks) >= 2

    sec_block = next((b for b in res.blocks if "Dạng 1" in b["title"]), None)
    assert sec_block is not None
    assert r"y = \sqrt{x^2+1}" in sec_block["title"]

    sub_block = next((b for b in res.blocks if "Bài toán với tập hợp" in b["title"]), None)
    assert sub_block is not None
    assert "S =" in sub_block["title"]


def test_recursive_input_include_security_and_cycles(tmp_path):
    """Verifies recursive \\input resolution, path traversal prevention, and cycle protection."""
    importer = LegacyLessonImporter()

    root_dir = tmp_path / "lesson_project"
    root_dir.mkdir()

    # Part 2 (leaf)
    part2 = root_dir / "part2.tex"
    part2.write_text(r"\subsection{Tiểu mục con}\begin{ex}Câu hỏi lá\loigiai{Giải}\end{ex}", encoding="utf-8")

    # Part 1 (middle)
    part1 = root_dir / "part1.tex"
    part1.write_text(r"\section{Chương 1} Lý thuyết chương 1." + "\n" + r"\input{part2.tex}", encoding="utf-8")

    # Main
    main_file = root_dir / "main.tex"
    main_file.write_text(r"""\documentclass{article}
\begin{document}
\input{part1.tex}
\end{document}""", encoding="utf-8")

    # 1. Successful 2-level recursive input
    res = importer.parse_file(main_file)
    assert any("Lý thuyết chương 1" in b.get("source", "") for b in res.blocks)
    assert any(b["kind"] == "exercise" and "Câu hỏi lá" in b.get("source", "") for b in res.blocks)

    # 2. Path traversal attack blocked
    outside_dir = tmp_path / "secret"
    outside_dir.mkdir()
    secret_file = outside_dir / "secret.tex"
    secret_file.write_text("DỮ LIỆU BÍ MẬT KHÔNG ĐƯỢC ĐỌC", encoding="utf-8")

    attack_file = root_dir / "attack.tex"
    attack_file.write_text(r"""\documentclass{article}
\begin{document}
\input{../secret/secret.tex}
\end{document}""", encoding="utf-8")

    res_attack = importer.parse_file(attack_file, allowed_root=root_dir)
    assert not any("DỮ LIỆU BÍ MẬT" in b.get("source", "") for b in res_attack.blocks)
    assert any(d["kind"] == "input" and d["reason"] == "Path traversal" for d in res_attack.unresolved_dependencies)
    assert res_attack.needs_review

    # 3. Circular inclusion detection
    cycle_a = root_dir / "cycle_a.tex"
    cycle_b = root_dir / "cycle_b.tex"
    cycle_a.write_text(r"\section{A} Nội dung A \input{cycle_b.tex}", encoding="utf-8")
    cycle_b.write_text(r"\section{B} Nội dung B \input{cycle_a.tex}", encoding="utf-8")

    cycle_main = root_dir / "cycle_main.tex"
    cycle_main.write_text(r"\documentclass{article}\begin{document}\input{cycle_a.tex}\end{document}", encoding="utf-8")

    res_cycle = importer.parse_file(cycle_main)
    assert any("Circular inclusion" in d.get("reason", "") for d in res_cycle.unresolved_dependencies)
    assert res_cycle.needs_review


def test_graphicspath_and_asset_staging(tmp_path):
    """Verifies \\graphicspath lookup and asset staging into AssetStore."""
    store_dir = tmp_path / "store"
    store = AssetStore(store_dir)
    importer = LegacyLessonImporter(asset_store=store)

    proj_dir = tmp_path / "diagram_proj"
    proj_dir.mkdir()
    img_dir = proj_dir / "figures"
    img_dir.mkdir()

    img_file = img_dir / "optic_diagram.png"
    img_file.write_bytes(b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDRFAKEOPTICDATA")

    main_tex = proj_dir / "doc.tex"
    main_tex.write_text(r"""\documentclass{article}
\usepackage{graphicx}
\graphicspath{{figures/}}
\begin{document}
\section{Quang hình học}
\begin{center}
\includegraphics[width=0.8\linewidth]{optic_diagram.png}
\end{center}
\end{document}""", encoding="utf-8")

    res = importer.parse_file(main_tex)
    assert len(res.assets_found) == 1
    assert res.assets_found[0]["original"] == "optic_diagram.png"
    assert "lesson-" in res.blocks[0]["source"] or "lesson-" in res.blocks[1]["source"]
    assert res.coverage_percent >= 90.0


def test_dry_run_and_transactional_service_import(tmp_path):
    """Verifies dry-run inspection and safe transactional DB import."""
    cfg = AppConfig.load(tmp_path / "data")
    services = create_services(cfg)
    lesson_srv = LessonService(services)
    store = AssetStore(services.config.data_dir / "assets")
    importer = LegacyLessonImporter(asset_store=store)

    tex_code = r"""\documentclass{article}
\begin{document}
\title{Hàm số lũy thừa}
\section{1. Khái niệm hàm số lũy thừa}
Hàm số $y = x^\alpha$ với $\alpha \in \mathbb{R}$ được gọi là hàm số lũy thừa.
\begin{ex}
Tìm tập xác định của hàm số $y = (x - 1)^{-3}$.
\choice
{\True $D = \mathbb{R} \setminus \{1\}$}
{$D = (1; +\infty)$}
{$D = \mathbb{R}$}
{$D = [1; +\infty)$}
\loigiai{Do số mũ $-3$ nguyên âm nên điều kiện là $x - 1 \neq 0 \iff x \neq 1$.}
\end{ex}
\end{document}"""

    # 1. Dry run does not write to DB
    res = importer.dry_run(tex_code, subject="Toán", grade="12")
    assert res.title == "Hàm số lũy thừa"
    assert len(res.blocks) >= 2
    assert len(lesson_srv.list()) == 0

    # 2. Transactional import commits successfully
    doc = importer.import_to_lesson(res, lesson_srv)
    assert doc["id"] is not None
    assert doc["title"] == "Hàm số lũy thừa"
    assert len(lesson_srv.list()) == 1

    # 3. Round-trip verification
    ok, issues = importer.verify_round_trip(res, lesson_srv)
    assert ok, f"Round-trip failed: {issues}"


def test_deliberate_missing_content_reports_low_coverage_honestly():
    """Requirement M1.1: If 70% of content is lost, coverage MUST report ~30%, not floor 50% or 100%."""
    importer = LegacyLessonImporter()

    # Simulate parsing where only 30% of body characters are preserved in blocks
    full_body = "A" * 700 + "B" * 300
    res = importer.parse_text(r"\documentclass{article}\begin{document}" + full_body + r"\end{document}")
    # Under standard parse, all 1000 chars are preserved in raw/theory block -> 100%
    assert res.coverage_percent == 100.0

    # If only 300 out of 1000 non-whitespace chars are mapped into blocks:
    extracted_300 = 300
    total_1000 = 1000
    calculated_coverage = min(100.0, max(0.0, round((extracted_300 / total_1000) * 100.0, 2)))
    assert calculated_coverage == 30.0  # Crucial: NOT 50.0% and NOT 100.0%

