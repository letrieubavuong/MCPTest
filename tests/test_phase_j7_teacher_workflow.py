"""
Phase J.7.4 - Real-world Teacher Acceptance, Exam Integrity & Macro Security Test Suite.
Tests:
1. Comprehensive question formats: MCQ, True/False, Short Answer, Essay with \\immini, TikZ, siunitx.
2. Student vs Teacher export integrity and independent portable compilation.
3. Custom unrecognized macro fail-closed safety handling.
4. Thumbnail cache key invalidation on asset, preamble, or engine changes.
5. Multi-version exam generation (seeds, shuffling).
6. Multi-file lesson bundle compilation.
"""
from dataclasses import replace
import hashlib
import shutil
import subprocess
import zipfile
from pathlib import Path
import pytest

from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.exams import ExamService
from latex_question_studio.application.importing import ImportService
from latex_question_studio.application.lessons import LessonService, student_source
from latex_question_studio.preview.compiler import Compiler
from latex_question_studio.preview.thumbnails import ThumbnailManager


VALID_PNG = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff\x89\x99=\x1d\x00\x00\x00\x00IEND\xaeB`\x82'


def test_j74_comprehensive_real_data_exam_and_portable_zip(tmp_path):
    """J.7.4 #1 & #2: Đề thi thực tế chứa \\immini, TikZ, siunitx, bóc tách an toàn và xuất ZIP độc lập."""
    work_dir = tmp_path / "CSDL_Vat_Ly_2026"
    work_dir.mkdir(parents=True, exist_ok=True)
    img_file = work_dir / "do_thi_dao_dong.png"
    img_file.write_bytes(VALID_PNG)

    config = AppConfig(data_dir=work_dir / "data")
    services = create_services(config)
    import_svc = ImportService(services)
    exam_svc = ExamService(services)

    # Chuẩn bị file TeX chứa 3 câu hỏi thực tế có ảnh và TikZ
    sample_content = (
        r"\begin{ex}" "\n"
        r"\immini{Một chất điểm dao động điều hòa có đồ thị li độ như hình vẽ. Biên độ dao động của chất điểm là:}" "\n"
        r"{\includegraphics[width=3cm]{do_thi_dao_dong.png}}" "\n"
        r"\choice{\True $A = 4\text{ cm}$}{$A = 8\text{ cm}$}{$A = 2\text{ cm}$}{$A = 10\text{ cm}$}" "\n"
        r"\loigiai{Từ đồ thị ta thấy giá trị cực đại của li độ là $4\text{ cm}$.}" "\n"
        r"\end{ex}" "\n\n"
        r"\begin{ex}" "\n"
        r"Cho mạch điện có điện trở $R = 50\,\Omega$, cuộn cảm thuần $L = \frac{1}{\pi}\text{ H}$." "\n"
        r"\begin{center}" "\n"
        r"\begin{tikzpicture}" "\n"
        r"\draw[thick] (0,0) -- (1,0) to[R=$R$] (3,0) -- (4,0);" "\n"
        r"\end{tikzpicture}" "\n"
        r"\end{center}" "\n"
        r"\choiceTF{\True a) Cảm kháng của cuộn dây là $Z_L = 100\,\Omega$ khi $f = 50\text{ Hz}$.}" "\n"
        r"{b) Cường độ dòng điện trễ pha $\pi/2$ so với điện áp hai đầu điện trở.}" "\n"
        r"{\True c) Mạch điện có tính cảm kháng.}" "\n"
        r"{d) Khi tăng tần số thì hệ số công suất của mạch tăng.}" "\n"
        r"\loigiai{Cảm kháng $Z_L = 2\pi f L = 2\pi \cdot 50 \cdot (1/\pi) = 100\,\Omega$.}" "\n"
        r"\end{ex}" "\n\n"
        r"\begin{ex}" "\n"
        r"Một con lắc lò xo dao động với chu kỳ $T = 0{,}4\text{ s}$. Tần số dao động của con lắc là bao nhiêu Hertz?" "\n"
        r"\dapsoTL{2.5}" "\n"
        r"\shortans{2.5}" "\n"
        r"\loigiai{Tần số dao động là $f = 1/T = 1/0.4 = 2.5\text{ Hz}$.}" "\n"
        r"\end{ex}"
    )
    tex_path = work_dir / "de_kiem_tra_mau.tex"
    tex_path.write_text(sample_content, encoding="utf-8")

    batch, staged = import_svc.stage([tex_path])
    assert len(staged) == 3
    import_svc.commit(batch)

    imported_qs = services.questions.list_page()
    assert len(imported_qs) == 3

    # Sinh đề thi
    version, snapshot = exam_svc.generate(
        title="ĐỀ KIỂM TRA ĐỊNH KỲ VẬT LÍ 12",
        manual_ids=[q.id for q in imported_qs],
        seed=20261014,
        shuffle_questions=False,
        subject="VẬT LÍ",
        school="THPT CHUYÊN"
    )
    assert len(snapshot['questions']) == 3

    # Xuất gói portable ZIP
    zip_path = work_dir / "De_Thi_Vat_Li_Portable.zip"
    exam_svc.export_zip(
        snapshot,
        zip_path,
        export_student=True,
        export_teacher=True,
        export_answers=True,
        compile_pdf=False
    )
    assert zip_path.is_file() and zip_path.stat().st_size > 500

    # Giải nén tại thư mục hoàn toàn độc lập
    isolated_dir = tmp_path / "ThuMucGiaoVienDocLap"
    isolated_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(isolated_dir)

    student_tex = (isolated_dir / "de-thi-hoc-sinh.tex").read_text(encoding="utf-8")
    teacher_tex = (isolated_dir / "de-thi-giao-vien.tex").read_text(encoding="utf-8")

    # Kiểm toán an toàn đề học sinh
    assert r"\begin{document}" in student_tex
    student_body = student_tex.split(r"\begin{document}")[1]
    assert r"\True" not in student_body
    assert r"\loigiai" not in student_body
    assert r"\dapsoTL" not in student_body
    assert r"\shortans" not in student_body
    assert "Từ đồ thị ta thấy" not in student_body
    assert "Cảm kháng $Z_L" not in student_body

    # Đề giáo viên đầy đủ
    assert r"\loigiai" in teacher_tex
    assert "Từ đồ thị ta thấy" in teacher_tex

    # Biên dịch PDF độc lập cả 2 bản qua pdfLaTeX trên thư mục giải nén
    compiler = Compiler(isolated_dir)
    engine_bin = compiler.engine_path()
    if engine_bin:
        proc_t = subprocess.run(
            [engine_bin, "-interaction=nonstopmode", "de-thi-giao-vien.tex"],
            cwd=str(isolated_dir),
            capture_output=True,
            text=True,
            timeout=30
        )
        assert proc_t.returncode == 0, f"Teacher compile failed: {proc_t.stdout[-500:]}"
        assert (isolated_dir / "de-thi-giao-vien.pdf").is_file()
        assert (isolated_dir / "de-thi-giao-vien.pdf").stat().st_size > 1000

        proc_s = subprocess.run(
            [engine_bin, "-interaction=nonstopmode", "de-thi-hoc-sinh.tex"],
            cwd=str(isolated_dir),
            capture_output=True,
            text=True,
            timeout=30
        )
        assert proc_s.returncode == 0, f"Student compile failed: {proc_s.stdout[-500:]}"
        assert (isolated_dir / "de-thi-hoc-sinh.pdf").is_file()
        assert (isolated_dir / "de-thi-hoc-sinh.pdf").stat().st_size > 1000


def test_j74_custom_macro_fail_closed_handling():
    """J.7.4 #3: Macro lạ không thuộc allowlist và có định dạng nghi vấn được xử lý an toàn (fail-closed)."""
    source_with_suspicious_custom_macro = (
        r"\begin{ex}" "\n"
        r"Tìm nghiệm của phương trình $x^2 = 4$." "\n"
        r"\MyCustomSecretAnswerMacro{2 và -2}" "\n"
        r"\end{ex}"
    )
    
    with pytest.raises(ValueError, match="Macro chưa được chứng nhận cho source học sinh"):
        student_source(source_with_suspicious_custom_macro, hide_answers=True)


def test_j74_thumbnail_cache_invalidation_on_asset_and_preamble_change(tmp_path):
    """J.7.4 #4: Thay đổi asset hoặc preamble làm thay đổi hash key, vô hiệu hóa thumbnail cũ."""
    thumb_mgr = ThumbnailManager(tmp_path / "cache")
    
    asset1 = tmp_path / "asset.png"
    asset1.write_bytes(b"image_version_1")
    
    key1 = thumb_mgr.compute_key(
        source=r"\begin{ex}Hello\end{ex}",
        preamble=r"\documentclass{article}",
        dependencies={},
        assets={"fig1": asset1},
        engine="pdflatex"
    )
    
    # Modify asset content
    asset1.write_bytes(b"image_version_2_changed")
    key2 = thumb_mgr.compute_key(
        source=r"\begin{ex}Hello\end{ex}",
        preamble=r"\documentclass{article}",
        dependencies={},
        assets={"fig1": asset1},
        engine="pdflatex"
    )
    assert key1 != key2, "Cache key must change when asset content changes"

    # Modify preamble
    key3 = thumb_mgr.compute_key(
        source=r"\begin{ex}Hello\end{ex}",
        preamble=r"\documentclass[12pt]{article}",
        dependencies={},
        assets={"fig1": asset1},
        engine="pdflatex"
    )
    assert key2 != key3, "Cache key must change when preamble changes"


def test_j74_multi_version_exam_generation_shuffling(tmp_path):
    """J.7.4 #5: Sinh nhiều mã đề với seed khác nhau tạo thứ tự và mã đề độc lập."""
    config = AppConfig(data_dir=tmp_path / "data")
    services = create_services(config)
    exam_svc = ExamService(services)

    q_ids = []
    for i in range(5):
        q = services.questions.create(f"\\begin{{ex}}Cau {i}\\choice{{\\True A}}{{B}}{{C}}{{D}}\\loigiai{{Lời giải {i}}}\\end{{ex}}")
        q_ids.append(q.id)

    v1, snap1 = exam_svc.generate(
        title="ĐỀ THI 1",
        manual_ids=q_ids,
        seed=111,
        shuffle_questions=True
    )

    v2, snap2 = exam_svc.generate(
        title="ĐỀ THI 2",
        manual_ids=q_ids,
        seed=999,
        shuffle_questions=True
    )

    order1 = [q['question_id'] for q in snap1['questions']]
    order2 = [q['question_id'] for q in snap2['questions']]
    assert len(order1) == 5 and len(order2) == 5
    assert snap1['exam_code'] != snap2['exam_code'] or order1 != order2


def test_j74_multi_file_lesson_bundle_export_and_compile(tmp_path):
    """J.7.4 #5: Soạn bài giảng đa tệp (LyThuyet, DangToan, BTVD) xuất và biên dịch thành công."""
    config = AppConfig(data_dir=tmp_path / "data")
    services = create_services(config)
    lessons = LessonService(services)

    doc = lessons.create("Bài 1: Dao động điều hòa", subject="Vật lí")
    doc = lessons.save(doc)

    export_folder = tmp_path / "export_lesson"
    export_folder.mkdir(parents=True, exist_ok=True)

    bundle_dir = lessons.export(
        doc,
        folder=export_folder,
        audience="teacher",
        worksheet=False,
        engine="pdflatex"
    )

    assert (bundle_dir / "LyThuyet" / "ly-thuyet.tex").is_file()
    assert any((bundle_dir / "DangToan").glob("*.tex"))
    assert (bundle_dir / "BTVD" / "bai-tap-van-dung.tex").is_file()
    assert (bundle_dir / "main.tex").is_file()
    assert (bundle_dir / "bai-giang.pdf").is_file()
