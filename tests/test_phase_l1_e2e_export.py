"""E2E Integration Test for Phase L.1 (L4):
From HTML scraping -> staging -> edit & moderation -> DB commit ->
Phase K exam creation (4 variants: De01..De04) -> multi-variant ZIP export ->
unpacking into isolated directory -> compiling with real pdfLaTeX.
"""
import zipfile
from pathlib import Path
import pytest
from PySide6.QtGui import QImage, QColor

from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.exams import ExamService
from latex_question_studio.application.web_import import WebScraperService, QuestionDraft
from latex_question_studio.preview.compiler import Compiler


def test_e2e_html_to_moderation_to_db_to_phase_k_multi_variant_compilation(tmp_path):
    """L4.4 E2E:
    1. Parse HTML containing MCQ, TF, Short Answer, Essay, and an incomplete question.
    2. Staging & moderation: verify valid questions, reject or skip faulty ones.
    3. Commit verified questions into SQLite database.
    4. Verify DB questions integrity.
    5. Build Phase K exam with 4 variants (De01, De02, De03, De04).
    6. Export multi-variant ZIP bundle.
    7. Unpack ZIP in a fresh isolated folder and compile each variant using real pdfLaTeX.
    8. Verify student version has no \\True or solution leaks.
    """
    compiler = Compiler(str(tmp_path))
    if not compiler.engine_path():
        pytest.skip("pdfLaTeX not installed on system")

    # 1. Setup isolated services and asset store
    services = create_services(AppConfig.load(tmp_path / "app"))
    exam_service = ExamService(services)
    web_service = WebScraperService()

    # Create dummy local asset for test
    asset_file = tmp_path / "graph_fig.png"
    img = QImage(32, 32, QImage.Format.Format_RGB32)
    img.fill(QColor(40, 167, 69))
    img.save(str(asset_file), "PNG")

    # 2. Simulate extracted drafts from HTML
    mcq_draft = QuestionDraft(
        id="draft_mcq_1",
        source_url="http://test.local/math12",
        title="Câu 1: Hàm số đồng biến",
        question_type="mcq",
        prompt_latex="Cho hàm số $y = x^3 - 3x^2 + 2$. Khẳng định nào sau đây là đúng?",
        options_latex=[
            "Hàm số đồng biến trên $(-\\infty; 0)$ và $(2; +\\infty)$",
            "Hàm số đồng biến trên $(0; 2)$",
            "Hàm số nghịch biến trên $(2; +\\infty)$",
            "Hàm số đồng biến trên $\\mathbb{R}$",
        ],
        correct_choice=0,
        solution_latex="Ta có $y' = 3x^2 - 6x = 3x(x - 2)$. $y' > 0 \\Leftrightarrow x \\in (-\\infty; 0) \\cup (2; +\\infty)$.",
        status="verified",
    )

    tf_draft = QuestionDraft(
        id="draft_tf_1",
        source_url="http://test.local/math12",
        title="Câu 2: Hình học không gian",
        question_type="true_false",
        prompt_latex="Cho tứ diện đều $ABCD$ cạnh $a$. Các mệnh đề sau đúng hay sai?",
        options_latex=[
            "Góc giữa hai đường thẳng $AB$ và $CD$ bằng $90^\\circ$.",
            "Thể tích khối tứ diện bằng $\\frac{a^3\\sqrt{2}}{12}$.",
            "Khoảng cách giữa hai đường thẳng chéo nhau $AB$ và $CD$ bằng $\\frac{a\\sqrt{2}}{2}$.",
            "Tâm mặt cầu ngoại tiếp tứ diện trùng với trọng tâm của tứ diện.",
        ],
        choice_tf_answers=[True, True, True, True],
        solution_latex="Tứ diện đều có các cặp cạnh đối vuông góc và khoảng cách bằng $a/\\sqrt{2}$.",
        status="verified",
    )

    sa_draft = QuestionDraft(
        id="draft_sa_1",
        source_url="http://test.local/math12",
        title="Câu 3: Tích phân",
        question_type="short_answer",
        prompt_latex="Tính tích phân $I = \\int_{0}^{1} (2x + 1)dx$.",
        short_answer_key="2",
        solution_latex="$I = [x^2 + x]_0^1 = 1 + 1 = 2$.",
        status="verified",
    )

    essay_draft = QuestionDraft(
        id="draft_es_1",
        source_url="http://test.local/math12",
        title="Câu 4: Tự luận tổ hợp",
        question_type="essay",
        prompt_latex="Một hộp chứa 5 viên bi đỏ và 4 viên bi xanh. Lấy ngẫu nhiên 3 viên bi. Tính xác suất lấy được ít nhất 2 viên bi đỏ.",
        solution_latex="Số cách chọn 3 viên từ 9 viên là $C_9^3 = 84$. Số cách lấy ít nhất 2 bi đỏ là $C_5^2 C_4^1 + C_5^3 = 10 \\times 4 + 10 = 50$. Xác suất $P = 50/84 = 25/42$.",
        status="verified",
    )

    # Incomplete faulty draft that MUST NOT be committed
    faulty_draft = QuestionDraft(
        id="draft_faulty",
        source_url="http://test.local/math12",
        title="Câu lỗi thiếu ảnh",
        question_type="mcq",
        prompt_latex="Xem hình sau đây: % [THIẾU ẢNH]",
        options_latex=["A", "B"],
        correct_choice=None,
        has_missing_images=True,
        status="needs_review",
    )

    # 3. Moderation check: only verified drafts commit
    all_drafts = [mcq_draft, tf_draft, sa_draft, essay_draft, faulty_draft]
    res_commit = web_service.commit_drafts_to_db(all_drafts, services, asset_store=None)
    assert res_commit["ok"]
    assert res_commit["committed_count"] == 4, f"Mong đợi 4 câu được lưu, kết quả: {res_commit['committed_count']}"

    # Verify questions in SQLite database
    db_questions = services.questions.list_page(limit=10, offset=0)
    assert len(db_questions) == 4
    q_ids = [q.id for q in db_questions]

    # 4. Generate 4 Phase K Exam snapshots (De01, De02, De03, De04) from these DB questions
    snapshots = []
    for i in range(1, 5):
        code = f"De{i:02d}"
        _, snap = exam_service.generate(
            f"KỲ THI THỬ TỐT NGHIỆP - MÃ {code}",
            manual_ids=q_ids,
            seed=2026 + i,
            exam_code=code,
        )
        snapshots.append(snap)
    assert len(snapshots) == 4

    # 5. Export Phase K multi-variant bundle (De01..De04) to ZIP
    zip_export_dir = tmp_path / "exam_export"
    zip_export_dir.mkdir(parents=True, exist_ok=True)
    zip_path = zip_export_dir / "de_thi_toan12_variants.zip"

    export_res = exam_service.export_multi_variant_zip(
        snapshots,
        zip_path,
        compile_pdf=False,
    )
    assert zip_path.is_file()
    assert zip_path.stat().st_size > 5000

    # 6. Unpack ZIP in a completely separate isolated directory
    isolated_unpack_dir = tmp_path / "isolated_unpack"
    isolated_unpack_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(isolated_unpack_dir)

    # Verify directory structure inside unpacked bundle
    # Should contain folders for De01, De02, De03, De04
    variant_dirs = [d for d in isolated_unpack_dir.iterdir() if d.is_dir() and d.name.startswith("De0")]
    assert len(variant_dirs) == 4, f"Cần 4 mã đề trong file ZIP, tìm thấy: {[d.name for d in variant_dirs]}"

    # 7. Compile each variant (student version and teacher version) using real pdfLaTeX
    for vdir in variant_dirs:
        student_tex = vdir / "de-thi-hoc-sinh.tex"
        teacher_tex = vdir / "de-thi-giao-vien.tex"
        answer_tex = vdir / "dap-an.tex"

        assert student_tex.is_file(), f"Thiếu file {student_tex}"
        assert teacher_tex.is_file(), f"Thiếu file {teacher_tex}"
        assert answer_tex.is_file(), f"Thiếu file {answer_tex}"

        # Check safety: student file MUST NOT contain \True or \loigiai
        student_content = student_tex.read_text(encoding="utf-8")
        assert "\\True " not in student_content, f"Lỗi rò rỉ \\True trong đề học sinh: {vdir.name}"
        assert "\\loigiai{" not in student_content, f"Lỗi rò rỉ lời giải trong đề học sinh: {vdir.name}"

        import subprocess

        # Compile student version inside isolated unpacked folder
        res_stud = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "de-thi-hoc-sinh.tex"],
            cwd=str(vdir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert res_stud.returncode == 0, f"Compile đề học sinh {vdir.name} thất bại:\n{res_stud.stdout[-600:]}"
        assert (vdir / "de-thi-hoc-sinh.pdf").is_file()

        # Compile teacher version inside isolated unpacked folder
        res_teach = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "de-thi-giao-vien.tex"],
            cwd=str(vdir),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        assert res_teach.returncode == 0, f"Compile đề giáo viên {vdir.name} thất bại:\n{res_teach.stdout[-600:]}"
        assert (vdir / "de-thi-giao-vien.pdf").is_file()
