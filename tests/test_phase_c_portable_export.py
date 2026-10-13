import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile
import pytest

from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.exams import ExamService
from latex_question_studio.application.importing import ImportService
from latex_question_studio.application.services import create_services
from latex_question_studio.preview.compiler import Compiler

VALID_1X1_PNG = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff\x89\x99=\x1d\x00\x00\x00\x00IEND\xaeB`\x82'


def test_preflight_export_checks(tmp_path):
    services = create_services(AppConfig.load(tmp_path / 'data'))
    exam = ExamService(services)

    # 1. Kiểm tra preflight với snapshot cơ bản
    snapshot = {
        'title': 'Đề kiểm tra',
        'questions': [],
        'assets': {'missing.png': str(tmp_path / 'non_existent.png')}
    }
    check = exam.preflight_export(snapshot, tmp_path / 'out', engine='pdflatex', preamble_file=str(tmp_path / 'no_preamble.tex'))
    assert not check['ok']
    assert any('no_preamble.tex' in err for err in check['errors'])
    assert 'missing.png' in check['missing_assets']


def test_path_traversal_protection(tmp_path):
    services = create_services(AppConfig.load(tmp_path / 'data'))
    exam = ExamService(services)

    asset_file = tmp_path / 'asset.png'
    asset_file.write_bytes(VALID_1X1_PNG)

    # Cố tình đưa đường dẫn asset có path traversal: ../evil.png
    snapshot = {
        'title': 'Hack attempt',
        'questions': [{'id': 'q1', 'source': r'\includegraphics{../evil.png}', 'solution': ''}],
        'assets': {'../evil.png': str(asset_file)}
    }

    with pytest.raises(ValueError, match="path traversal"):
        exam.export_tex(snapshot, tmp_path / 'out' / 'test.tex')


def test_copy_class_dependencies_raise_on_missing(tmp_path, monkeypatch):
    import latex_question_studio.application.exams as exams_module
    # Giả lập profile rỗng
    empty_root = tmp_path / 'empty_profile'
    empty_root.mkdir()
    monkeypatch.setattr(exams_module, 'default_profile_root', lambda: empty_root)

    with pytest.raises(FileNotFoundError, match="Thiếu file phụ thuộc lớp LaTeX"):
        exams_module.ExamService.copy_class_dependencies(tmp_path / 'dest', raise_on_missing=True)


def test_portable_bundle_and_zip_integrity_and_audience(tmp_path):
    services = create_services(AppConfig.load(tmp_path / 'data'))
    img_path = tmp_path / 'hinh1.png'
    img_path.write_bytes(VALID_1X1_PNG)

    q_source = (
        r'\begin{ex}' "\n"
        r'Cho hàm số $y = f(x)$ có đồ thị như hình vẽ:' "\n"
        r'\includegraphics{hinh1.png}' "\n"
        r'\choice{\True A. $1$}{B. $2$}{C. $3$}{D. $4$}' "\n"
        r'\loigiai{Lời giải chi tiết: đáp án là A.}' "\n"
        r'\end{ex}'
    )
    tex_path = tmp_path / 'cau1.tex'
    tex_path.write_text(q_source, encoding='utf-8')

    batch, _ = ImportService(services).stage([tex_path])
    assert ImportService(services).commit(batch) == 1

    q_id = services.questions.list_page()[0].id
    _, snapshot = ExamService(services).generate('Đề Khảo Sát Toán 12', manual_ids=[q_id])

    # 1. Xuất bundle thư mục
    bundle_dir = tmp_path / 'bundle_export'
    exam_svc = ExamService(services)
    bundle_res = exam_svc.export_bundle(
        snapshot,
        bundle_dir,
        export_student=True,
        export_teacher=True,
        export_answers=True,
        compile_pdf=False
    )
    assert bundle_res['ok']
    assert (bundle_dir / 'de-thi-hoc-sinh.tex').is_file()
    assert (bundle_dir / 'de-thi-giao-vien.tex').is_file()
    assert (bundle_dir / 'dap-an.tex').is_file()
    assert (bundle_dir / 'bien-dich.bat').is_file()
    assert (bundle_dir / 'HUONG_DAN_BIEN_DICH.txt').is_file()
    assert (bundle_dir / 'MAPClass.cls').is_file()
    assert (bundle_dir / 'Packages' / 'ex_test.sty').is_file()
    assert len(list((bundle_dir / 'assets').glob('*.png'))) >= 1
    assert (bundle_dir / 'manifest.json').is_file()

    manifest = json.loads((bundle_dir / 'manifest.json').read_text(encoding='utf-8'))
    assert manifest['audience'] == 'all'
    for rel_path, digest in manifest['sha256'].items():
        assert hashlib.sha256((bundle_dir / rel_path).read_bytes()).hexdigest() == digest

    # 2. Xuất ZIP portable học sinh
    zip_path = tmp_path / 'DeThi_HocSinh_Unicode_TiengViet.zip'
    exam_svc.export_zip(
        snapshot,
        zip_path,
        export_student=True,
        export_teacher=False,
        export_answers=False,
        compile_pdf=False
    )
    assert zip_path.is_file()

    # 3. Giải nén sang thư mục độc lập hoàn toàn và kiểm tra
    extract_dir = tmp_path / 'independent_extracted'
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(extract_dir)

    assert (extract_dir / 'main.tex').is_file()
    assert (extract_dir / 'de-thi-hoc-sinh.tex').is_file()
    assert not (extract_dir / 'de-thi-giao-vien.tex').exists()
    assert (extract_dir / 'MAPClass.cls').is_file()
    assert len(list((extract_dir / 'assets').glob('*.png'))) >= 1

    zip_manifest = json.loads((extract_dir / 'manifest.json').read_text(encoding='utf-8'))
    assert zip_manifest['audience'] == 'student'
    # Đảm bảo hash trong manifest khớp 100% với từng file giải nén
    for rel_path, digest in zip_manifest['sha256'].items():
        assert (extract_dir / rel_path).is_file()
        assert hashlib.sha256((extract_dir / rel_path).read_bytes()).hexdigest() == digest

    # Đảm bảo không chứa lời giải trong body của học sinh
    main_tex = (extract_dir / 'main.tex').read_text(encoding='utf-8')
    body = main_tex.split(r'\begin{document}', 1)[1]
    assert 'Lời giải chi tiết' not in body
    assert r'\True' not in body


def test_independent_standalone_compilation(tmp_path):
    """Kiểm tra gói portable ZIP sau khi giải nén ở thư mục độc lập có thể tự biên dịch bằng pdflatex."""
    compiler = Compiler(tmp_path / 'compiler')
    engine_bin = compiler.engine_path()
    if not engine_bin:
        pytest.skip("pdflatex không có trên hệ thống để kiểm tra biên dịch độc lập")

    services = create_services(AppConfig.load(tmp_path / 'data'))
    img_path = tmp_path / 'math_pic.png'
    img_path.write_bytes(VALID_1X1_PNG)

    q_source = (
        r'\begin{ex}' "\n"
        r'Tập nghiệm của phương trình $\log_2(x - 1) = 3$ là:' "\n"
        r'\includegraphics[width=2cm]{math_pic.png}' "\n"
        r'\choice{\True A. $\{9\}$}{B. $\{7\}$}{C. $\{8\}$}{D. $\{10\}$}' "\n"
        r'\loigiai{Ta có $x - 1 = 2^3 = 8 \Leftrightarrow x = 9$.}' "\n"
        r'\end{ex}'
    )
    tex_path = tmp_path / 'cau_math.tex'
    tex_path.write_text(q_source, encoding='utf-8')

    batch, _ = ImportService(services).stage([tex_path])
    ImportService(services).commit(batch)

    q_id = services.questions.list_page()[0].id
    _, snapshot = ExamService(services).generate('Đề Toán Portable', manual_ids=[q_id])

    zip_path = tmp_path / 'portable_exam.zip'
    ExamService(services).export_zip(
        snapshot,
        zip_path,
        export_student=True,
        export_teacher=True,
        compile_pdf=False
    )

    # Giải nén sang một thư mục độc lập
    standalone_dir = tmp_path / 'standalone_workspace'
    with zipfile.ZipFile(zip_path, 'r') as zf:
        zf.extractall(standalone_dir)

    # Chạy pdflatex độc lập trên thư mục giải nén
    proc = subprocess.run(
        [engine_bin, '-interaction=nonstopmode', 'de-thi-hoc-sinh.tex'],
        cwd=str(standalone_dir),
        capture_output=True,
        text=True,
        timeout=30
    )
    assert proc.returncode == 0, f"Biên dịch thất bại: {proc.stdout[-500:]}"
    assert (standalone_dir / 'de-thi-hoc-sinh.pdf').is_file()
    assert (standalone_dir / 'de-thi-hoc-sinh.pdf').stat().st_size > 1000
