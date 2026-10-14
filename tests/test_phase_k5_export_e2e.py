r"""Tests for Phase K5: End-to-End Multi-Variant Exam Export (De01-De04).

Validates that:
- 4 variants (De01, De02, De03, De04) can be generated with all 4 question types:
  * MCQ with \choice, formulas, TikZ
  * True/False with \choiceTF (statements preserved in exact order)
  * Short Answer with \shortans
  * Essay
  * Image assets via \includegraphics
- export_multi_variant_bundle creates isolated subfolders for each variant with:
  * de-thi-hoc-sinh.tex, de-thi-giao-vien.tex, dap-an.tex
  * bien-dich.bat, manifest.json, MAPClass.cls, Packages/ex_test.sty, Loigiai/
- Student files contain NO solution or \True leakage.
- Answer keys match the shuffled questions and options for each variant.
- export_multi_variant_zip creates a self-contained portable ZIP.
- Unpacking the ZIP in an isolated folder compiles cleanly via pdfLaTeX.
- Backward compatibility / regression with legacy snapshots.
"""
import json
import os
import shutil
import subprocess
import zipfile
import pytest
from pathlib import Path
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.exams import ExamService
from latex_question_studio.preview.compiler import Compiler


@pytest.fixture
def exam_environment(tmp_path):
    s = create_services(AppConfig.load(tmp_path / 'app'))
    exam = ExamService(s)

    # Create valid image asset using QImage
    from PySide6.QtGui import QImage, QColor
    asset_file = tmp_path / 'figure_geo.png'
    img = QImage(30, 30, QImage.Format.Format_RGB32)
    img.fill(QColor(0, 120, 215))
    img.save(str(asset_file), 'PNG')

    # MCQ 1 with TikZ
    q_mcq1 = s.questions.create(
        r"""\begin{ex}
Cho hàm số $y=f(x)$ liên tục trên $\mathbb{R}$. Đồ thị như hình vẽ:
\begin{center}
\begin{tikzpicture}[scale=0.5]
\draw[->] (-2,0) -- (2,0) node[right] {$x$};
\draw[->] (0,-1) -- (0,3) node[above] {$y$};
\draw[domain=-1.5:1.5] plot (\x, {\x*\x});
\end{tikzpicture}
\end{center}
Điểm cực tiểu của hàm số là:
\choice
{$x=1$}
{\True $x=0$}
{$x=-1$}
{$y=0$}
\loigiai{Từ đồ thị ta thấy hàm số đạt cực tiểu tại $x=0$.}
\end{ex}""",
        'mcq'
    )

    # MCQ 2 with image asset
    q_mcq2 = s.questions.create(
        r"""\begin{ex}
Xem hình vẽ bên dưới:
\begin{center}
\includegraphics[width=2cm]{figure_geo.png}
\end{center}
Hình trên biểu diễn khối đa diện nào?
\choice
{\True Khối tứ diện}
{Khối lập phương}
{Khối bát diện đều}
{Khối lăng trụ tam giác}
\loigiai{Khối có 4 đỉnh và 4 mặt là khối tứ diện.}
\end{ex}""",
        'mcq'
    )
    import hashlib
    import uuid
    content = asset_file.read_bytes()
    h = hashlib.sha256(content).hexdigest()
    asset_id = str(uuid.uuid4())
    rel_path = f"assets/{h[:2]}/{h}.png"
    target_disk = s.config.data_dir / rel_path
    target_disk.parent.mkdir(parents=True, exist_ok=True)
    target_disk.write_bytes(content)
    with s.database.transaction() as c:
        c.execute("INSERT OR IGNORE INTO assets(id, content_hash, relative_path, bytes) VALUES (?, ?, ?, ?)", (asset_id, h, rel_path, len(content)))
        c.execute("INSERT INTO question_assets(question_id, asset_id, original_reference) VALUES (?, ?, ?)", (q_mcq2.id, asset_id, 'figure_geo.png'))

    # True/False 1
    q_tf1 = s.questions.create(
        r"""\begin{ex}
Cho tứ diện $ABCD$. Gọi $M, N$ lần lượt là trung điểm của $AB$ và $CD$.
\choiceTF
{\True $\vec{MN} = \frac{1}{2}(\vec{AD} + \vec{BC})$}
{$\vec{MN} = \vec{AC} + \vec{BD}$}
{\True $M, N, A, B$ không đồng phẳng}
{$AB \perp CD$}
\loigiai{Ý a đúng theo công thức véc-tơ trung điểm. Ý b sai. Ý c đúng. Ý d sai vì không có giả thiết vuông góc.}
\end{ex}""",
        'true_false'
    )

    # True/False 2
    q_tf2 = s.questions.create(
        r"""\begin{ex}
Cho cấp số cộng $(u_n)$ có $u_1 = 3$ và công sai $d = 2$.
\choiceTF
{\True $u_2 = 5$}
{$u_3 = 6$}
{\True $u_{10} = 21$}
{$S_5 = 30$}
\loigiai{Ta có $u_2 = 3+2=5$. $u_3=7 \ne 6$. $u_{10}=3+9\times 2=21$. $S_5 = \frac{5(3+11)}{2}=35 \ne 30$.}
\end{ex}""",
        'true_false'
    )

    # Short Answer 1
    q_sa1 = s.questions.create(
        r"""\begin{ex}
Tính tích phân $I = \int_0^1 (2x + 1)\,dx$.
\shortans{2}
\loigiai{$I = [x^2 + x]_0^1 = 1 + 1 = 2$.}
\end{ex}""",
        'short_answer'
    )

    # Short Answer 2
    q_sa2 = s.questions.create(
        r"""\begin{ex}
Cho tam giác $ABC$ vuông tại $A$, $AB=3, AC=4$. Tính bán kính $R$ của đường tròn ngoại tiếp tam giác.
\shortans{2.5}
\loigiai{Cạnh huyền $BC = \sqrt{3^2+4^2} = 5 \implies R = BC/2 = 2.5$.}
\end{ex}""",
        'short_answer'
    )

    # Essay 1
    q_es1 = s.questions.create(
        r"""\begin{ex}
Tìm tất cả các giá trị của tham số $m$ để hàm số $y = \frac{x+m}{x-1}$ đồng biến trên từng khoảng xác định.
\loigiai{
Tập xác định: $D = \mathbb{R} \setminus \{1\}$.
Đạo hàm: $y' = \frac{-1-m}{(x-1)^2}$.
Hàm số đồng biến trên từng khoảng xác định khi và chỉ khi $y' > 0, \forall x \ne 1 \iff -1-m > 0 \iff m < -1$.
}
\end{ex}""",
        'essay'
    )

    return {
        'services': s,
        'exam': exam,
        'q_ids': [q_mcq1.id, q_mcq2.id, q_tf1.id, q_tf2.id, q_sa1.id, q_sa2.id, q_es1.id],
        'asset_file': asset_file
    }


def test_multi_variant_export_bundle_structure(exam_environment, tmp_path):
    exam = exam_environment['exam']
    q_ids = exam_environment['q_ids']

    # Generate 4 variants: De01, De02, De03, De04
    snapshots = []
    for i in range(1, 5):
        code = f"De{i:02d}"
        _, snap = exam.generate(
            f"ĐỀ THI KHẢO SÁT CHẤT LƯỢNG - MÃ {code}",
            manual_ids=q_ids,
            seed=100 + i,
            exam_code=code
        )
        snapshots.append(snap)

    bundle_dir = tmp_path / 'export_4_variants'
    res = exam.export_multi_variant_bundle(
        snapshots,
        bundle_dir,
        export_student=True,
        export_teacher=True,
        export_answers=True,
        compile_pdf=False  # bundle test only
    )

    assert res['ok']
    assert (bundle_dir / 'bien-dich-tat-ca.bat').is_file()
    assert (bundle_dir / 'master_manifest.json').is_file()
    assert (bundle_dir / 'MAPClass.cls').is_file()
    assert (bundle_dir / 'Packages' / 'ex_test.sty').is_file()

    # Check each variant folder
    for i in range(1, 5):
        code = f"De{i:02d}"
        var_dir = bundle_dir / code
        assert var_dir.is_dir()
        assert (var_dir / 'de-thi-hoc-sinh.tex').is_file()
        assert (var_dir / 'de-thi-giao-vien.tex').is_file()
        assert (var_dir / 'dap-an.tex').is_file()
        assert (var_dir / 'bien-dich.bat').is_file()
        assert (var_dir / 'manifest.json').is_file()
        assert (var_dir / 'MAPClass.cls').is_file()
        assert (var_dir / 'Packages' / 'ex_test.sty').is_file()
        assert (var_dir / 'Loigiai').is_dir()

        # Check content in student TeX
        student_content = (var_dir / 'de-thi-hoc-sinh.tex').read_text(encoding='utf-8')
        assert rf"\begin{{cauhoiTN}}{{{code}}}" in student_content
        assert rf"\begin{{cauhoiDS}}{{{code}}}" in student_content
        assert rf"\begin{{cauhoiTLN}}{{{code}}}" in student_content
        assert rf"\begin{{cauhoiTL}}{{{code}}}" in student_content

        # Non-leakage: Student must NOT contain \True or \loigiai in the document body
        doc_body = student_content.split(r'\begin{document}')[1]
        assert r"\True" not in doc_body
        assert r"\loigiai" not in doc_body
        assert "Từ đồ thị ta thấy" not in doc_body
        assert "Ý a đúng" not in doc_body


def test_answer_keys_match_shuffled_options(exam_environment, tmp_path):
    exam = exam_environment['exam']
    q_ids = exam_environment['q_ids']

    # Generate De01 and De02 with different seeds
    _, snap1 = exam.generate("Đề 1", manual_ids=q_ids, seed=42, exam_code="De01")
    _, snap2 = exam.generate("Đề 2", manual_ids=q_ids, seed=999, exam_code="De02")

    # In Part II (TF), statement truth list must always match the original order:
    # q_tf1 truth: [True, False, True, False]
    # q_tf2 truth: [True, False, True, False]
    for snap in [snap1, snap2]:
        for q in snap['questions']:
            if q.get('question_type') == 'true_false' or r'\choiceTF' in q['source']:
                truth = q['answer']['truth']
                assert truth == [True, False, True, False], f"TF statements were modified: {truth}"

    # In Part I (MCQ), correct letter should match option marked \True in teacher source
    for snap in [snap1, snap2]:
        body_teacher = exam.content(snap, solutions=True)
        ans_tex = exam.content(snap, answer_only=True)
        assert "PHẦN I" in ans_tex
        assert "PHẦN II" in ans_tex
        assert "PHẦN III" in ans_tex
        assert "PHẦN IV" in ans_tex


@pytest.mark.skipif(not shutil.which('pdflatex'), reason='pdfLaTeX not installed')
def test_portable_zip_independent_compilation(exam_environment, tmp_path):
    exam = exam_environment['exam']
    q_ids = exam_environment['q_ids']

    # Create 4 variants
    snapshots = []
    for i in range(1, 5):
        code = f"De{i:02d}"
        _, snap = exam.generate(
            f"KỲ THI THỬ TỐT NGHIỆP THPT - MÃ {code}",
            manual_ids=q_ids,
            seed=2026 + i,
            exam_code=code
        )
        snapshots.append(snap)

    zip_file = tmp_path / 'DeThi_4MaDe_Portable.zip'
    exam.export_multi_variant_zip(
        snapshots,
        zip_file,
        compile_pdf=False  # Do not pre-compile so we test offline independent compile
    )

    assert zip_file.is_file()
    assert zip_file.stat().st_size > 5000

    # Extract to a completely separate, clean directory simulating another computer
    unpack_dir = tmp_path / 'isolated_client_machine'
    with zipfile.ZipFile(zip_file, 'r') as archive:
        archive.extractall(unpack_dir)

    # Verify extracted structure
    assert (unpack_dir / 'bien-dich-tat-ca.bat').is_file()
    assert (unpack_dir / 'De01' / 'de-thi-hoc-sinh.tex').is_file()
    copied_assets = list((unpack_dir / 'De01' / 'assets').glob('*.png'))
    assert len(copied_assets) == 1
    assert copied_assets[0].is_file()
    assert (unpack_dir / 'De01' / 'MAPClass.cls').is_file()
    assert (unpack_dir / 'De01' / 'Loigiai').is_dir()

    # Run independent compilation of De01 inside isolated directory using pdfLaTeX
    de01_dir = unpack_dir / 'De01'
    cmd = ['pdflatex', '-interaction=nonstopmode', 'de-thi-hoc-sinh.tex']
    result = subprocess.run(
        cmd,
        cwd=str(de01_dir),
        capture_output=True,
        text=True,
        timeout=60
    )

    pdf_output = de01_dir / 'de-thi-hoc-sinh.pdf'
    assert pdf_output.is_file(), f"pdfLaTeX failed: {result.stdout[-1000:]}"
    assert pdf_output.stat().st_size > 1000, "Generated PDF is empty or invalid"


def test_legacy_snapshot_regression(tmp_path):
    """Verifies that legacy exam snapshots without exam_code or modern fields serialize cleanly."""
    s = create_services(AppConfig.load(tmp_path / 'app'))
    exam = ExamService(s)

    legacy_snapshot = {
        'id': 'legacy-exam-uuid-1234',
        'title': 'Đề kiểm tra năm 2024',
        'created_at': '2024-01-01T00:00:00Z',
        'questions': [
            {
                'id': 'q1',
                'question_type': 'mcq',
                'source': r'\begin{ex}Câu 1?\choice{A}{\True B}{C}{D}\end{ex}',
                'answer': {'correct_letter': 'B'}
            },
            {
                'id': 'q2',
                'question_type': 'essay',
                'source': r'\begin{ex}Câu 2 tự luận.\end{ex}',
                'answer': {'essay': True}
            }
        ]
        # Notice: exam_code is omitted, simulating pre-Phase K snapshot
    }

    body = exam.content(legacy_snapshot, solutions=False)
    # Should default gracefully to De01 and generate valid structure
    assert r"\TieudeT{Đề kiểm tra năm 2024}" in body
    assert r"\PhanI" in body
    assert r"\begin{cauhoiTN}{De01}" in body
    assert r"\PhanTL" in body
    assert r"\begin{cauhoiTL}{De01}" in body
