from dataclasses import replace
import hashlib
import json
from pathlib import Path
import zipfile
import pytest

from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.exams import ExamService
from latex_question_studio.application.importing import ImportService
from latex_question_studio.application.search import SearchService
from latex_question_studio.application.services import create_services

VALID_PNG = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff\x89\x99=\x1d\x00\x00\x00\x00IEND\xaeB`\x82'


def test_full_lifecycle_exam_workflow_toan_vatli_khtn(tmp_path):
    """
    Kiểm thử trọn vẹn quy trình nghiệp vụ thực tế:
    1. Nhập TeX Toán, Vật lí, KHTN kèm TikZ, hình ảnh, bảng biểu.
    2. Phát hiện câu trùng khi nhập lại (deduplication).
    3. Tìm kiếm và chỉnh sửa bảo toàn revision.
    4. Tạo đề thi shuffle với seed xác định.
    5. Xuất đề học sinh vs giáo viên:
       - Tuyệt đối KHÔNG lộ \\True, \\loigiai, \\hdan, \\shortans trong đề học sinh.
       - Đầy đủ lời giải trong đề giáo viên.
       - Không làm mất TikZ và hình ảnh.
       - Không làm thay đổi nội dung câu gốc trong CSDL.
    6. Kiểm tra an toàn khi thiếu tài nguyên (không báo thành công giả).
    7. Giải nén ZIP sang thư mục độc lập và đối soát hash manifest.
    """
    config = AppConfig(data_dir=tmp_path / 'data')
    services = create_services(config)
    import_svc = ImportService(services)
    search_svc = SearchService(services)
    exam_svc = ExamService(services)

    # Chuẩn bị asset hình ảnh
    img_vatli = tmp_path / 'mach_rlc.png'
    img_vatli.write_bytes(VALID_PNG)

    # 1. Ba câu hỏi đại diện cho 3 môn
    # Môn Toán: Tích phân + \\choice + \\True + \\loigiai + TikZ
    toan_src = (
        r"\begin{ex}" "\n"
        r"Cho hàm số $f(x)$ liên tục. Tính tích phân $I = \int_0^1 x^2 \, dx$." "\n"
        r"\begin{center}" "\n"
        r"\begin{tikzpicture}" "\n"
        r"\draw[->] (-1,0) -- (2,0) node[right] {$x$};" "\n"
        r"\draw[->] (0,-1) -- (0,2) node[above] {$y$};" "\n"
        r"\draw (0,0) parabola (1,1);" "\n"
        r"\end{tikzpicture}" "\n"
        r"\end{center}" "\n"
        r"\choice" "\n"
        r"{\True A. $\dfrac{1}{3}$}" "\n"
        r"{B. $\dfrac{1}{2}$}" "\n"
        r"{C. $1$}" "\n"
        r"{D. $\dfrac{2}{3}$}" "\n"
        r"\loigiai{Ta có $\int_0^1 x^2 dx = \left.\dfrac{x^3}{3}\right|_0^1 = \dfrac{1}{3}$. Đáp án A.}" "\n"
        r"\end{ex}"
    )

    # Môn Vật lí: Mạch RLC + \\choiceTF + \\True + \\includegraphics
    vatli_src = (
        r"\begin{ex}" "\n"
        r"Một đoạn mạch xoay chiều RLC nối tiếp có sơ đồ như hình vẽ:" "\n"
        r"\begin{center}" "\n"
        r"\includegraphics[width=0.4\textwidth]{mach_rlc.png}" "\n"
        r"\end{center}" "\n"
        r"Xét tính đúng sai của các nhận định sau:" "\n"
        r"\choiceTF" "\n"
        r"{\True a) Khi xảy ra cộng hưởng thì điện áp cùng pha với dòng điện.}" "\n"
        r"{b) Hệ số công suất luôn bằng 0 khi có cộng hưởng.}" "\n"
        r"{\True c) Cường độ dòng điện hiệu dụng đạt cực đại khi $Z_L = Z_C$.}" "\n"
        r"{d) Điện áp giữa hai đầu tụ điện luôn sớm pha hơn dòng điện.}" "\n"
        r"\hdan{Khi cộng hưởng $Z_L = Z_C \Rightarrow \cos\varphi = 1$, dòng điện cùng pha với điện áp.}" "\n"
        r"\end{ex}"
    )

    # Môn KHTN (Hóa học): Độ pH + Bảng số liệu + \\shortans
    khtn_src = (
        r"\begin{ex}" "\n"
        r"Dung dịch chất X có bảng số liệu đo độ pH ở nhiệt độ $25^\circ\text{C}$ như sau:" "\n"
        r"\begin{center}" "\n"
        r"\begin{tabular}{|c|c|c|}" "\n"
        r"\hline" "\n"
        r"Mẫu & Nồng độ & pH \\" "\n"
        r"\hline" "\n"
        r"X & $0.01\text{M}$ & $2.0$ \\" "\n"
        r"\hline" "\n"
        r"\end{tabular}" "\n"
        r"\end{center}" "\n"
        r"Xác định độ pH của dung dịch X." "\n"
        r"\shortans{2}" "\n"
        r"\loigiai{Dựa vào bảng số liệu, pH của dung dịch X bằng 2.}" "\n"
        r"\end{ex}"
    )

    # Ghi ra các file TeX
    file_toan = tmp_path / "de_toan.tex"
    file_toan.write_text(toan_src, encoding='utf-8')

    file_vatli = tmp_path / "de_vatli.tex"
    file_vatli.write_text(vatli_src, encoding='utf-8')

    file_khtn = tmp_path / "de_khtn.tex"
    file_khtn.write_text(khtn_src, encoding='utf-8')

    # BƯỚC 1: Nhập vào hệ thống
    batch_1, staged_1 = import_svc.stage([file_toan, file_vatli, file_khtn])
    assert len(staged_1) == 3
    # Lần nhập đầu tiên không có câu nào bị trùng
    assert not any(item.get('duplicate') for item in staged_1)

    imported_count = import_svc.commit(batch_1)
    assert imported_count == 3

    # BƯỚC 2: Kiểm tra Deduplication khi nhập lại cùng dữ liệu
    batch_2, staged_2 = import_svc.stage([file_toan, file_vatli])
    assert len(staged_2) == 2
    # Cả hai câu phải được phát hiện trùng lặp
    assert all(item.get('duplicate') for item in staged_2)

    # BƯỚC 3: Tìm kiếm câu hỏi
    all_q = services.questions.list_page()
    assert len(all_q) == 3

    found_toan = search_svc.find(text="tích phân")
    assert any("tích phân" in q.latex_source for q in found_toan)

    found_vatli = search_svc.find(text="RLC")
    assert any("RLC" in q.latex_source for q in found_vatli)

    # BƯỚC 4: Chỉnh sửa câu hỏi (bảo toàn revision)
    q_toan = next(q for q in all_q if "tích phân" in q.latex_source)
    orig_toan_source = q_toan.latex_source
    updated_source = orig_toan_source.replace(r"$I = \int_0^1 x^2 \, dx$", r"$I = \int_0^2 x^2 \, dx$")
    updated_q = replace(q_toan, latex_source=updated_source)
    services.questions.update(updated_q)

    q_toan_reloaded = services.questions.get(q_toan.id)
    assert q_toan_reloaded.revision == 2
    assert "0^2" in q_toan_reloaded.latex_source

    # BƯỚC 5: Tạo đề thi với seed xác định
    q_ids = [q.id for q in services.questions.list_page()]
    version, snapshot = exam_svc.generate(
        title="Đề Khảo Sát Liên Môn",
        manual_ids=q_ids,
        seed=20261013,
        shuffle_questions=True,
        subject="KHOA HỌC",
        school="TRƯỜNG THPT CHUYÊN"
    )
    assert len(snapshot['questions']) == 3

    # BƯỚC 6: Xuất Bundle (học sinh + giáo viên)
    bundle_dir = tmp_path / "bundle_export"
    bundle_res = exam_svc.export_bundle(
        snapshot,
        bundle_dir,
        export_student=True,
        export_teacher=True,
        export_answers=True,
        compile_pdf=False
    )
    assert bundle_res['ok']

    student_tex_path = bundle_dir / "de-thi-hoc-sinh.tex"
    teacher_tex_path = bundle_dir / "de-thi-giao-vien.tex"
    assert student_tex_path.is_file()
    assert teacher_tex_path.is_file()

    student_tex = student_tex_path.read_text(encoding='utf-8')
    teacher_tex = teacher_tex_path.read_text(encoding='utf-8')

    # KIỂM TRA ĐẶC BIỆT 1: ĐỀ HỌC SINH KHÔNG LỘ ĐÁP ÁN (Phần thân đề thi)
    assert r"\begin{document}" in student_tex
    body_student_tex = student_tex.split(r"\begin{document}")[1]
    assert r"\True" not in body_student_tex
    assert r"\loigiai" not in body_student_tex
    assert r"\hdan" not in body_student_tex
    assert r"\shortans" not in body_student_tex
    assert "Lời giải chi tiết" not in body_student_tex
    assert "pH của dung dịch X bằng 2" not in body_student_tex

    # KIỂM TRA ĐẶC BIỆT 2: ĐỀ GIÁO VIÊN ĐẦY ĐỦ
    assert (r"\True" in teacher_tex) or (r"\loigiai" in teacher_tex)
    assert "Lời giải chi tiết" in teacher_tex or r"\loigiai" in teacher_tex

    # KIỂM TRA ĐẶC BIỆT 3: TIKZ VÀ HÌNH ẢNH ĐƯỢC BẢO TOÀN TRONG CẢ HAI BẢN
    assert "tikzpicture" in student_tex
    assert "tikzpicture" in teacher_tex
    assert "includegraphics" in student_tex
    assert "assets/" in student_tex and ".png" in student_tex
    assert "includegraphics" in teacher_tex
    assert "assets/" in teacher_tex and ".png" in teacher_tex
    assert len(list((bundle_dir / "assets").glob("*.png"))) >= 1

    # KIỂM TRA ĐẶC BIỆT 4: NỘI DUNG CÂU GỐC TRONG CSDL KHÔNG BỊ BIẾN ĐỔI
    for q_check in services.questions.list_page():
        assert len(q_check.latex_source) > 50
        if "mach_rlc.png" in q_check.latex_source:
            assert r"\choiceTF" in q_check.latex_source
            assert r"\True" in q_check.latex_source

    # BƯỚC 7: Xuất ZIP và giải nén sang thư mục độc lập
    zip_path = tmp_path / "DeThi_LienMon.zip"
    exam_svc.export_zip(
        snapshot,
        zip_path,
        export_student=True,
        export_teacher=False,
        export_answers=False,
        compile_pdf=False
    )
    assert zip_path.is_file()

    extract_dir = tmp_path / "extracted_standalone"
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(extract_dir)

    assert (extract_dir / "main.tex").is_file()
    assert (extract_dir / "de-thi-hoc-sinh.tex").is_file()
    assert (extract_dir / "manifest.json").is_file()
    assert len(list((extract_dir / "assets").glob("*.png"))) >= 1

    manifest = json.loads((extract_dir / "manifest.json").read_text(encoding='utf-8'))
    assert manifest['audience'] == 'student'
    for rel_path, digest in manifest['sha256'].items():
        extracted_file = extract_dir / rel_path
        assert extracted_file.is_file()
        assert hashlib.sha256(extracted_file.read_bytes()).hexdigest() == digest


def test_export_safety_fails_on_missing_resource(tmp_path):
    """Kiểm tra xuất đề thi phát hiện thiếu tài nguyên và không báo thành công giả."""
    config = AppConfig(data_dir=tmp_path / 'data')
    services = create_services(config)
    exam_svc = ExamService(services)

    fake_snapshot = {
        'title': 'Đề lỗi thiếu file',
        'questions': [
            {'question_id': 'q_err', 'source': r'\begin{ex} \includegraphics{non_existent.png} \end{ex}', 'solution': ''}
        ],
        'assets': {'non_existent.png': str(tmp_path / 'does_not_exist.png')}
    }

    # 1. preflight_export phát hiện missing assets và missing preamble
    check = exam_svc.preflight_export(fake_snapshot, tmp_path / 'out', preamble_file=str(tmp_path / 'missing_preamble.tex'))
    assert not check['ok']
    assert 'non_existent.png' in check['missing_assets']

    # 2. export_pdf với missing asset trả về ok=False
    pdf_out = tmp_path / 'out.pdf'
    res = exam_svc.export_pdf(fake_snapshot, pdf_out)
    assert not res.ok
    assert 'does_not_exist.png' in res.log or 'không hợp lệ' in res.log
