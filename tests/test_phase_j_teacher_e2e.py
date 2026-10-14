"""
Phase J.5 - End-to-End Teacher Acceptance & Resilience Test Suite.
Tests full teacher workflow on real data:
1. Import -> Classify -> Search -> Edit -> Preview with content-aware crop.
2. Exam Creation -> Portable Zip Export -> Clean Extraction -> Independent pdfLaTeX Compilation.
3. Resilience: Syntax errors, duplicate detection, backup/restore, Unicode/spaces paths.
"""
from dataclasses import replace
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
import pytest

from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.importing import ImportService
from latex_question_studio.application.library import LibraryService
from latex_question_studio.application.search import SearchService
from latex_question_studio.application.exams import ExamService
from latex_question_studio.preview.compiler import Compiler


VALID_PNG = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff\x89\x99=\x1d\x00\x00\x00\x00IEND\xaeB`\x82'


def test_scenario_1_teacher_import_classify_search_edit_preview(tmp_path):
    r"""Kịch bản 1: Import -> Phân loại -> Tìm kiếm -> Sửa câu -> Preview."""
    config = AppConfig(data_dir=tmp_path / "data")
    services = create_services(config)
    import_svc = ImportService(services)
    lib_svc = LibraryService(services)
    search_svc = SearchService(services)

    # 1. Chuẩn bị file TeX thực tế và ảnh
    img_path = tmp_path / "hinh_dao_dong.png"
    img_path.write_bytes(VALID_PNG)

    sample_tex = (
        r"\begin{ex}" "\n"
        r"Một con lắc lò xo dao động điều hòa theo phương trình $x = 5\cos(2\pi t)$ cm." "\n"
        r"\begin{center}" "\n"
        r"\includegraphics[width=0.4\textwidth]{hinh_dao_dong.png}" "\n"
        r"\end{center}" "\n"
        r"\choice{\True Biên độ là $5$ cm}" "\n"
        r"{Biên độ là $10$ cm}" "\n"
        r"{Pha ban đầu là $\pi$ rad}" "\n"
        r"{Tần số góc là $4\pi$ rad/s}" "\n"
        r"\loigiai{Từ phương trình ta có $A = 5$ cm.}" "\n"
        r"\end{ex}"
    )
    tex_file = tmp_path / "physics_exercises.tex"
    tex_file.write_text(sample_tex, encoding="utf-8")

    batch, staged = import_svc.stage([tex_file])
    assert len(staged) == 1
    import_count = import_svc.commit(batch)
    assert import_count == 1
    imported_q = services.questions.list_page()[0]

    # 2. Phân loại theo cây CSDL (Vật lí -> Dao động cơ -> Con lắc lò xo)
    node_id = lib_svc.add_taxonomy(
        name="Con lắc lò xo",
        kind="topic",
        parent_id=None
    )
    lib_svc.save_metadata(
        imported_q.id,
        {
            "taxonomy_id": node_id,
            "cognitive_level": "TH",
            "question_type": "mcq",
            "tags": ["vat_ly_12", "dao_dong"]
        }
    )

    # 3. Tìm kiếm câu hỏi
    found = search_svc.find(text="dao động điều hòa")
    assert any(q.id == imported_q.id for q in found)

    # 4. Sửa câu hỏi (bảo toàn revision)
    fresh_q = services.questions.get(imported_q.id)
    updated_source = fresh_q.latex_source.replace(r"x = 5\cos(2\pi t)", r"x = 8\cos(4\pi t)")
    updated_q = replace(fresh_q, latex_source=updated_source)
    services.questions.update(updated_q)

    reloaded_q = services.questions.get(imported_q.id)
    assert reloaded_q.revision == fresh_q.revision + 1
    assert r"x = 8\cos(4\pi t)" in reloaded_q.latex_source

    # 5. Preview và kiểm tra crop sát
    compiler = Compiler(services.config.data_dir)
    res = compiler.compile(reloaded_q.latex_source, {"hinh_dao_dong.png": img_path})
    assert res.ok
    assert res.pdf is not None and res.pdf.exists()

    cropped_png, pages = Compiler.render(res.pdf, crop=True)
    assert pages >= 1
    assert cropped_png is not None and len(cropped_png) > 100


def test_scenario_2_exam_creation_portable_export_independent_compile(tmp_path):
    r"""Kịch bản 2: Tạo đề thi -> Xuất portable -> Biên dịch độc lập (Giáo viên vs Học sinh)."""
    unicode_dir = tmp_path / "Đề thi Học kỳ 1 2026"
    unicode_dir.mkdir(parents=True, exist_ok=True)

    config = AppConfig(data_dir=unicode_dir / "data")
    services = create_services(config)
    exam_svc = ExamService(services)

    # 1. Tạo 4 dạng câu: MCQ, True/False, Short Answer, Essay
    q_mcq = services.questions.create(
        r"\begin{ex}" "\n"
        r"Phương trình dao động là $x = 4\cos(10t)$ cm. Pha dao động tại $t = 1$ s là:" "\n"
        r"\choice{\True $10$ rad}" "\n"
        r"{$4$ rad}" "\n"
        r"{$40$ rad}" "\n"
        r"{$0$ rad}" "\n"
        r"\loigiai{Pha dao động là $\Phi = 10t = 10$ rad.}" "\n"
        r"\end{ex}"
    )
    q_tf = services.questions.create(
        r"\begin{ex}" "\n"
        r"Xét tính đúng sai của các phát biểu về sóng cơ:" "\n"
        r"\choiceTF{\True a) Sóng cơ không truyền được trong chân không.}" "\n"
        r"{b) Sóng ngang truyền được trong chất khí.}" "\n"
        r"{\True c) Sóng dọc truyền được trong chất rắn, lỏng, khí.}" "\n"
        r"{d) Tốc độ truyền sóng phụ thuộc vào tần số sóng.}" "\n"
        r"\loigiai{Sóng ngang chỉ truyền trong chất rắn và bề mặt chất lỏng.}" "\n"
        r"\end{ex}"
    )
    q_sa = services.questions.create(
        r"\begin{ex}" "\n"
        r"Một sóng có bước sóng $\lambda = 2$ m, chu kì $T = 0.5$ s. Tốc độ truyền sóng là bao nhiêu m/s?" "\n"
        r"\dapsoTL{4}" "\n"
        r"\shortans{4}" "\n"
        r"\loigiai{Tốc độ truyền sóng là $v = \lambda / T = 2 / 0.5 = 4$ m/s.}" "\n"
        r"\end{ex}"
    )
    q_essay = services.questions.create(
        r"\begin{ex}" "\n"
        r"Hãy nêu định nghĩa và viết hệ thức của định luật Ôm đối với toàn mạch." "\n"
        r"\loigiai{Cường độ dòng điện chạy trong mạch kín tỉ lệ thuận với suất điện động.}" "\n"
        r"\end{ex}"
    )

    # 2. Tạo đề thi
    version, snapshot = exam_svc.generate(
        title="ĐỀ KIỂM TRA HỌC KỲ I - VẬT LÍ 12",
        manual_ids=[q_mcq.id, q_tf.id, q_sa.id, q_essay.id],
        seed=20261014,
        shuffle_questions=False,
        subject="VẬT LÍ",
        school="TRƯỜNG THPT CHUYÊN"
    )
    assert len(snapshot['questions']) == 4

    # 3. Xuất gói portable ZIP
    zip_path = unicode_dir / "De_Thi_Vat_Li_12_Portable.zip"
    exam_svc.export_zip(
        snapshot,
        zip_path,
        export_student=True,
        export_teacher=True,
        export_answers=True,
        compile_pdf=False
    )
    assert zip_path.is_file() and zip_path.stat().st_size > 1000

    # 4. Giải nén sang một thư mục hoàn toàn độc lập bên ngoài workspace
    isolated_extract_dir = tmp_path / "ThuMucDocLapGiaoVien"
    isolated_extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(isolated_extract_dir)

    teacher_tex_file = isolated_extract_dir / "de-thi-giao-vien.tex"
    student_tex_file = isolated_extract_dir / "de-thi-hoc-sinh.tex"
    assert teacher_tex_file.is_file()
    assert student_tex_file.is_file()

    # 5. Kiểm tra an toàn đề học sinh
    student_content = student_tex_file.read_text(encoding="utf-8")
    teacher_content = teacher_tex_file.read_text(encoding="utf-8")

    # Bản học sinh không được chứa đáp án đúng hoặc lời giải trong phần thân đề
    assert r"\begin{document}" in student_content
    student_body = student_content.split(r"\begin{document}")[1]
    assert r"\True" not in student_body
    assert r"\loigiai" not in student_body
    assert r"\shortans" not in student_body
    assert r"\dapsoTL" not in student_body
    assert "Pha dao động là" not in student_body

    # Bản giáo viên đầy đủ lời giải
    assert r"\loigiai" in teacher_content
    assert "Pha dao động là" in teacher_content

    # 6. Biên dịch độc lập cả 2 bản qua pdfLaTeX
    compiler = Compiler(isolated_extract_dir)
    res_teacher = compiler.compile(teacher_content, {})
    assert res_teacher.ok, f"Teacher PDF compile failed: {res_teacher.log}"
    assert res_teacher.pdf.exists()

    res_student = compiler.compile(student_content, {})
    assert res_student.ok, f"Student PDF compile failed: {res_student.log}"
    assert res_student.pdf.exists()


def test_scenario_3_resilience_and_edge_cases(tmp_path):
    r"""Kịch bản 3: Độ bền & Xử lý lỗi (Lỗi cú pháp, thiếu asset, trùng lặp, backup/restore)."""
    unicode_space_dir = tmp_path / "CSDL Thử Nghiệm 2026"
    unicode_space_dir.mkdir(parents=True, exist_ok=True)

    config = AppConfig(data_dir=unicode_space_dir / "data")
    services = create_services(config)
    import_svc = ImportService(services)
    lib_svc = LibraryService(services)

    # 1. Import file lỗi cú pháp -> App không crash, ghi nhận chẩn đoán
    bad_tex = (
        r"\begin{ex}" "\n"
        r"Câu hỏi có ngoặc mở mà không có ngoặc đóng: \textbf{unclosed" "\n"
        # Không có \end{ex}
    )
    bad_file = unicode_space_dir / "bad.tex"
    bad_file.write_text(bad_tex, encoding="utf-8")
    batch, staged = import_svc.stage([bad_file])
    # Parsed without crash; flagged with diagnostics
    assert len(staged) == 0 or len(staged[0].get("errors", [])) > 0

    # 2. Phát hiện câu trùng lặp (Deduplication)
    valid_q = (
        r"\begin{ex}" "\n"
        r"Cho hàm số $y = x^3 - 3x$. Tìm số điểm cực trị của hàm số." "\n"
        r"\choice{\True $2$}{$1$}{$0$}{$3$}" "\n"
        r"\loigiai{Ta có $y' = 3x^2 - 3 = 0 \Leftrightarrow x = \pm 1$. Hàm số có 2 điểm cực trị.}" "\n"
        r"\end{ex}"
    )
    f1 = unicode_space_dir / "f1.tex"
    f1.write_text(valid_q, encoding="utf-8")
    b1, s1 = import_svc.stage([f1])
    assert not any(item.get("duplicate") for item in s1)
    import_svc.commit(b1)

    f2 = unicode_space_dir / "f2.tex"
    f2.write_text(valid_q, encoding="utf-8")
    b2, s2 = import_svc.stage([f2])
    # Câu đã tồn tại phải được phát hiện duplicate
    assert all(item.get("duplicate") for item in s2)

    # 3. Backup CSDL, xóa dữ liệu và Restore
    backup_path = unicode_space_dir / "backup_library.zip"
    lib_svc.backup(backup_path)
    assert backup_path.exists()

    # Xóa dữ liệu câu hỏi
    for q in services.questions.list_page():
        services.questions.delete(q.id)
    assert len(services.questions.list_page()) == 0

    # Restore lại từ backup
    lib_svc.restore_backup(backup_path)
    restored = services.questions.list_page()
    assert len(restored) == 1
    assert "Tìm số điểm cực trị" in restored[0].latex_source
