"""Tests for Phase M: Lesson Workspace Redesign (Phases M0–M6).
Verifies:
- Teacher-centric pedagogical workflows: Create lesson -> Draft theory -> Add method bundle -> Insert bank questions -> Side-by-side preview -> Export package
- 3 Realistic subject lessons: KHTN 9, Toan 8, Vat li 10
- Legacy TeX import preserving theory outside exercises
- Student export confidentiality (teacher notes and solutions stripped)
- File manifest integrity (LyThuyet/, DangToan/, BTVD/, main.tex)
"""

import json
from pathlib import Path
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from latex_question_studio.application.lessons import LessonService
from latex_question_studio.application.legacy_lesson_importer import LegacyLessonImporter
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.preview.compiler import Compiler
from latex_question_studio.ui.main_window import MainWindow
from latex_question_studio.ui.lesson_page import LessonPage


def setup_services(tmp_path):
    cfg = AppConfig.load(tmp_path / 'data')
    services = create_services(cfg)
    return services, cfg


def test_phase_m_complete_pedagogical_workflow(qtbot, tmp_path):
    """Test full workflow: Create -> Draft theory -> Method bundle -> Bank insert -> Preview -> Export."""
    services, cfg = setup_services(tmp_path)
    
    # 1. Seed bank with sample questions
    q1 = services.questions.create(
        r"""\begin{ex}
Một tia sáng truyền từ không khí vào nước với góc tới $i = 45^\circ$. Biết chiết suất của nước là $n = \frac{4}{3}$. Góc khúc xạ $r$ gần giá trị nào nhất?
\choice
{\True $32^\circ$}
{$40^\circ$}
{$25^\circ$}
{$50^\circ$}
\loigiai{
Áp dụng định luật khúc xạ ánh sáng: $\sin i = n \sin r \Rightarrow \sin r = \frac{\sin 45^\circ}{4/3} \approx 0.5303 \Rightarrow r \approx 32^\circ$.
}
\end{ex}""",
        question_type='mcq'
    )
    q2 = services.questions.create(
        r"""\begin{ex}
Hiện tượng khúc xạ ánh sáng là hiện tượng tia sáng bị gãy khúc tại mặt phân cách giữa hai môi trường trong suốt.
\loigiai{Khẳng định đúng theo định nghĩa SGK.}
\end{ex}""",
        question_type='essay'
    )
    with services.database.connect() as c:
        c.execute("INSERT OR REPLACE INTO question_metadata (question_id, data_json) VALUES (?, ?)", (q1.id, json.dumps({'subject': 'KHTN', 'grade': '9', 'topic': 'Khúc xạ ánh sáng', 'cognitive_level': 'TH'})))
        c.execute("INSERT OR REPLACE INTO question_metadata (question_id, data_json) VALUES (?, ?)", (q2.id, json.dumps({'subject': 'KHTN', 'grade': '9', 'topic': 'Khúc xạ ánh sáng', 'cognitive_level': 'NB'})))

    # 2. Launch UI and switch to Lesson Workspace
    window = MainWindow(services)
    qtbot.addWidget(window)
    window.show()
    window.show_page(4)
    page: LessonPage = window.lesson_page

    # Create new lesson with dialog or method bundle
    page.new_lesson(interactive=False)
    page.title.setText("Bài 13: Hiện tượng khúc xạ ánh sáng")
    page.changed()

    # Verify first theory block
    assert len(page.doc['blocks']) >= 1
    page.block_title.setText("I. Hiện tượng khúc xạ")
    page.editor.setPlainText(
        r"""Định nghĩa: Khúc xạ ánh sáng là hiện tượng tia sáng tới bị gãy khúc khi truyền xiên góc qua mặt phân cách giữa hai môi trường trong suốt khác nhau.

Định luật khúc xạ ánh sáng:
\[
n_1 \sin i = n_2 \sin r
\]"""
    )
    page.notes.setPlainText("Nhấn mạnh cho học sinh: Tia sáng truyền vuông góc với mặt phân cách thì không bị khúc xạ.")
    page.changed()

    # 3. Add Method Bundle (Dạng toán + Ví dụ + Bài tập)
    page.add_method_bundle()
    assert any(b['kind'] == 'method' for b in page.doc['blocks'])
    method_block = next(b for b in page.doc['blocks'] if b['kind'] == 'method')
    assert "Dạng" in method_block['title']

    # 4. Search and insert questions from Bank
    page.query.setText("Khúc xạ")
    page.search_bank()
    assert page.bank.rowCount() >= 2

    # Select both questions
    page.bank.item(0, 0).setCheckState(Qt.CheckState.Checked)
    page.bank.item(1, 0).setCheckState(Qt.CheckState.Checked)
    page.insert_selected()

    # Verify blocks updated
    assert len(page.doc['blocks']) >= 4
    inserted_q_ids = [b['question']['id'] for b in page.doc['blocks'] if b.get('question')]
    assert q1.id in inserted_q_ids or q2.id in inserted_q_ids

    # 5. Save and check persistence
    assert page.save()
    assert not page.dirty
    lesson_srv = LessonService(services)
    saved_doc = lesson_srv.get(page.doc['id'])
    assert saved_doc['title'] == "Bài 13: Hiện tượng khúc xạ ánh sáng"
    assert len(saved_doc['blocks']) == len(page.doc['blocks'])

    # 6. Verify 3-Folder File Manifest
    manifest = lesson_srv.file_manifest(saved_doc)
    assert len(manifest) >= 3
    folders = {m['folder'] for m in manifest}
    assert 'LyThuyet' in folders
    assert 'DangToan' in folders
    assert 'BTVD' in folders

    # 7. Test Export Package to directory
    export_dir = tmp_path / "export_khtn9"
    export_dir.mkdir(parents=True, exist_ok=True)
    res_dir = lesson_srv.export(saved_doc, str(export_dir), audience='teacher', worksheet=False)

    assert (Path(res_dir) / 'main.tex').exists()
    assert (Path(res_dir) / 'LyThuyet').is_dir()
    assert (Path(res_dir) / 'DangToan').is_dir()
    assert (Path(res_dir) / 'BTVD').is_dir()
    assert (Path(res_dir) / 'bai-giang.pdf').exists()

    main_tex = (Path(res_dir) / 'main.tex').read_text(encoding='utf-8')
    assert r'\input{LyThuyet/' in main_tex
    assert r'\input{DangToan/' in main_tex

    window.close()


def test_three_realistic_subject_lessons(tmp_path):
    """Test creating and compiling 3 realistic lessons: Toán 8, KHTN 9 (TikZ), Vật lí 10."""
    services, cfg = setup_services(tmp_path)
    lesson_srv = LessonService(services)
    compiler = Compiler(services.config.data_dir, engine='pdflatex')

    # --- LESSON 1: TOÁN 8 (Những hằng đẳng thức đáng nhớ) ---
    doc_math = lesson_srv.create(
        title="Toán 8 - Bài 3: Những hằng đẳng thức đáng nhớ",
        subject="Toán",
        grade="8",
        blocks=[
            {
                'id': 'b_sec1',
                'kind': 'section',
                'title': 'A. Lý thuyết trọng tâm',
                'source': r"""\begin{itemize}
\item Bình phương của một tổng: $(A + B)^2 = A^2 + 2AB + B^2$
\item Bình phương của một hiệu: $(A - B)^2 = A^2 - 2AB + B^2$
\item Hiệu hai bình phương: $A^2 - B^2 = (A - B)(A + B)$
\end{itemize}""",
                'policy': 'full',
                'parent': None,
                'teacher_notes': 'Cho học sinh ghi nhớ bằng nhịp điệu.'
            },
            {
                'id': 'b_meth1',
                'kind': 'method',
                'title': 'Dạng 1: Khai triển biểu thức',
                'source': r"""Phương pháp: Xác định đúng hai biểu thức $A$ và $B$, sau đó áp dụng công thức hằng đẳng thức phù hợp.""",
                'policy': 'full',
                'parent': None,
                'teacher_notes': ''
            },
            {
                'id': 'b_ex1',
                'kind': 'example',
                'title': 'Ví dụ 1',
                'source': r"""\begin{ex}
Khai triển biểu thức $(2x + 3y)^2$.
\loigiai{
Áp dụng $(A + B)^2$ với $A = 2x, B = 3y$:
\[
(2x + 3y)^2 = (2x)^2 + 2 \cdot (2x) \cdot (3y) + (3y)^2 = 4x^2 + 12xy + 9y^2
\]
}
\end{ex}""",
                'policy': 'full',
                'parent': 'b_meth1',
                'teacher_notes': ''
            }
        ]
    )
    src_math, extra_math, _ = lesson_srv.master_bundle(doc_math, 'teacher', False)
    res_math = compiler.compile(src_math, {}, extra_files=extra_math)
    assert res_math.ok, f"Toan 8 compile failed: {res_math.log[-800:]}"
    assert Path(res_math.pdf).exists()

    # --- LESSON 2: KHTN 9 (Khúc xạ ánh sáng with TikZ) ---
    doc_khtn = lesson_srv.create(
        title="KHTN 9 - Hiện tượng khúc xạ ánh sáng",
        subject="KHTN",
        grade="9",
        blocks=[
            {
                'id': 'k_sec1',
                'kind': 'section',
                'title': 'I. Hiện tượng khúc xạ ánh sáng',
                'source': r"""Khúc xạ ánh sáng là hiện tượng tia sáng bị đổi hướng khi truyền xiên góc qua mặt phân cách giữa hai môi trường trong suốt.
\begin{center}
\begin{tikzpicture}[scale=0.8,>=stealth]
  \draw[fill=cyan!10] (-4,-3) rectangle (4,0);
  \node[above left] at (-2,0.3) {Không khí ($n_1$)};
  \node[below left] at (-2,-0.3) {Nước ($n_2$)};
  \draw[thick] (-4,0) -- (4,0);
  \draw[dashed] (0,-3) -- (0,3) node[above] {$N'$};
  \draw[->,very thick,red] (-3,2.5) -- (0,0);
  \draw[->,very thick,red] (0,0) -- (2,-2.2);
  \node[above left] at (-1.5,1.2) {Tia tới $SI$};
  \node[below right] at (1,-1.1) {Tia khúc xạ $IK$};
\end{tikzpicture}
\end{center}""",
                'policy': 'full',
                'parent': None,
                'teacher_notes': 'Sử dụng hình vẽ TikZ mô phỏng tia tới và tia khúc xạ.'
            }
        ]
    )
    src_khtn, extra_khtn, _ = lesson_srv.master_bundle(doc_khtn, 'teacher', False)
    res_khtn = compiler.compile(src_khtn, {}, extra_files=extra_khtn)
    assert res_khtn.ok, f"KHTN 9 TikZ compile failed: {res_khtn.log[-800:]}"
    assert Path(res_khtn.pdf).exists()

    # --- LESSON 3: VẬT LÍ 10 (Chuyển động thẳng biến đổi đều) ---
    doc_phys = lesson_srv.create(
        title="Vật lí 10 - Chuyển động thẳng biến đổi đều",
        subject="Vật lí",
        grade="10",
        blocks=[
            {
                'id': 'p_sec1',
                'kind': 'section',
                'title': '1. Gia tốc của chuyển động thẳng biến đổi đều',
                'source': r"""Định nghĩa gia tốc: $a = \frac{\Delta v}{\Delta t} = \frac{v - v_0}{t - t_0} = \text{const}$.
Công thức vận tốc: $v = v_0 + at$.
Công thức độ dịch chuyển: $d = v_0 t + \frac{1}{2} a t^2$.
Hệ thức độc lập thời gian: $v^2 - v_0^2 = 2ad$.""",
                'policy': 'full',
                'parent': None,
                'teacher_notes': 'Lưu ý dấu của vận tốc và gia tốc trong chuyển động nhanh dần/chậm dần đều.'
            }
        ]
    )
    src_phys, extra_phys, _ = lesson_srv.master_bundle(doc_phys, 'teacher', False)
    res_phys = compiler.compile(src_phys, {}, extra_files=extra_phys)
    assert res_phys.ok, f"Vat li 10 compile failed: {res_phys.log[-800:]}"
    assert Path(res_phys.pdf).exists()


def test_legacy_importer_and_student_privacy(tmp_path):
    """Test Legacy TeX import integration and verify student privacy policy."""
    services, cfg = setup_services(tmp_path)
    from latex_question_studio.application.assets import AssetStore
    store = AssetStore(services.config.data_dir / 'assets')
    importer = LegacyLessonImporter(asset_store=store)

    tex_content = r"""\documentclass{article}
\usepackage{amsmath,amssymb}
\usepackage{tikz}
\begin{document}
\section{Đại số tuyến tính: Ma trận và Định thức}
Ma trận vuông cấp $n$ là một bảng gồm $n \times n$ số được sắp xếp thành $n$ hàng và $n$ cột.

Định thức cấp 2 được tính theo công thức:
\[
\det \begin{pmatrix} a & b \\ c & d \end{pmatrix} = ad - bc
\]

\subsection{Dạng 1: Tính định thức ma trận}
Phương pháp giải: Sử dụng các phép biến đổi sơ cấp theo hàng để đưa ma trận về dạng tam giác.

\begin{ex}
Tính định thức của ma trận $A = \begin{pmatrix} 2 & 3 \\ 1 & 5 \end{pmatrix}$.
\choice
{\True $7$}
{$13$}
{$-7$}
{$10$}
\loigiai{
Ta có $\det(A) = 2 \cdot 5 - 3 \cdot 1 = 10 - 3 = 7$.
}
\end{ex}
\end{document}
"""
    tex_path = tmp_path / "legacy_matrix.tex"
    tex_path.write_text(tex_content, encoding='utf-8')

    res = importer.parse_file(tex_path, subject="Toán")
    assert res.title == "Đại số tuyến tính: Ma trận và Định thức"
    assert len(res.blocks) >= 3
    assert res.coverage_percent >= 85.0

    # Ensure theory paragraph outside exercises was fully preserved
    theory_sources = [b['source'] for b in res.blocks if b['kind'] in ('section', 'theory', 'method')]
    all_theory = " ".join(theory_sources)
    assert "Ma trận vuông cấp" in all_theory
    assert "ad - bc" in all_theory
    assert "Phương pháp giải" in all_theory

    # Create lesson document from imported blocks
    lesson_srv = LessonService(services)
    doc = lesson_srv.create(
        title=res.title,
        subject=res.subject,
        grade=res.grade,
        blocks=res.blocks
    )
    # Add teacher notes
    doc['blocks'][0]['teacher_notes'] = "BÍ MẬT GIÁO VIÊN: Không tiết lộ đề kiểm tra tuần sau."
    doc = lesson_srv.save(doc)

    # Export as Student: teacher_notes must not appear, \loigiai must be stripped
    student_body, _ = lesson_srv.body(doc, audience='student', worksheet=False)
    assert "BÍ MẬT GIÁO VIÊN" not in student_body
    assert "10 - 3 = 7" not in student_body

    # Export as Teacher: teacher_notes and \loigiai must both be present
    teacher_body, _ = lesson_srv.body(doc, audience='teacher', worksheet=False)
    assert "BÍ MẬT GIÁO VIÊN" in teacher_body
    assert "10 - 3 = 7" in teacher_body
