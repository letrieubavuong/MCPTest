"""Phase M1 Real-World Acceptance Test Suite.
Validates real-world lesson fixtures (Math 8, KHTN 9, Physics 10) and edge cases
with pdfLaTeX compilation on Windows, asset verification, student privacy fail-closed,
and directory relocation tests.
"""
from pathlib import Path
import hashlib
import shutil
import subprocess
import pytest
import pymupdf

from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.assets import AssetStore
from latex_question_studio.application.lessons import LessonService, block
from latex_question_studio.application.legacy_lesson_importer import LegacyLessonImporter

FIXTURES_ROOT = Path(__file__).parent / "fixtures" / "m1_lessons"


def setup_services(tmp_path):
    cfg = AppConfig.load(tmp_path / "app_data")
    srv = create_services(cfg)
    store = AssetStore(cfg.data_dir)
    return srv, LessonService(srv), store


def run_pdflatex(cwd, filename="main.tex", timeout=45):
    cmd = [
        "pdflatex",
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-no-shell-escape",
        filename,
    ]
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=timeout)
    return res


def test_math8_real_acceptance(tmp_path):
    """Toán 8: Formulas, align*, tabular, headings with nested math braces, pdfLaTeX export."""
    services, lesson_svc, store = setup_services(tmp_path)
    importer = LegacyLessonImporter(asset_store=store)
    file_path = FIXTURES_ROOT / "math8_identities" / "math8_identities.tex"
    assert file_path.is_file(), f"Missing fixture {file_path}"

    dry = importer.dry_run(file_path)
    assert dry.coverage_percent >= 95.0, f"Coverage too low: {dry.coverage_percent}"
    assert len(dry.warnings) == 0, f"Unexpected warnings: {dry.warnings}"
    q_blocks = [b for b in dry.blocks if b.get("kind") in ("exercise", "example")]
    assert len(q_blocks) >= 2, f"Expected at least 2 questions/exercises, got {len(q_blocks)}"

    # Verify heading preserved nested math without destroying braces
    titles = [b["title"] for b in dry.blocks]
    assert any("$(a+b)^2" in t for t in titles), f"Heading with math not preserved: {titles}"

    # Verify align* and tabular in theory block
    sources = "\n".join(b["source"] for b in dry.blocks)
    assert r"\begin{align*}" in sources
    assert r"\begin{tabular}" in sources

    # Import into lesson service
    doc = importer.import_to_lesson(dry, lesson_svc)
    assert doc["id"] is not None

    # Export teacher bundle & compile with real pdfLaTeX
    teacher_folder = lesson_svc.export(doc, tmp_path / "export_teacher", audience="teacher")
    assert (teacher_folder / "bai-giang.pdf").is_file()
    assert (teacher_folder / "main.tex").is_file()

    # Verify teacher pdfLaTeX compilation
    res = run_pdflatex(teacher_folder)
    assert res.returncode == 0, f"Teacher compile failed: {res.stdout.decode('utf-8', 'replace')[-1000:]}"

    # Export student bundle & verify privacy
    student_folder = lesson_svc.export(doc, tmp_path / "export_student", audience="student")
    assert (student_folder / "bai-giang.pdf").is_file()

    student_tex = (student_folder / "main.tex").read_text(encoding="utf-8")
    # Exercise solution must be stripped
    assert "Áp dụng công thức $(a - b)^2" not in student_tex
    # Public example is kept by default policy='full'
    assert "Ta áp dụng hằng đẳng thức" in student_tex

    # Check student PDF with PyMuPDF
    with pymupdf.open(student_folder / "bai-giang.pdf") as pdf:
        student_text = "".join(page.get_text() for page in pdf)
    assert "Áp dụng công thức $(a - b)^2" not in student_text

    # Now configure all blocks including examples to policy='question' and re-export
    for b in doc["blocks"]:
        b["policy"] = "question"
    doc = lesson_svc.save(doc)

    student_folder_strict = lesson_svc.export(doc, tmp_path / "export_student_strict", audience="student")
    student_tex_strict = (student_folder_strict / "main.tex").read_text(encoding="utf-8")
    assert "Ta áp dụng hằng đẳng thức" not in student_tex_strict

    with pymupdf.open(student_folder_strict / "bai-giang.pdf") as pdf:
        strict_text = "".join(page.get_text() for page in pdf)
    assert "Ta áp dụng hằng đẳng thức" not in strict_text


def test_khtn9_real_acceptance(tmp_path):
    """KHTN 9: TikZ refraction diagram, subfolder image asset staging, UTF-8 Vietnamese, pdfLaTeX."""
    services, lesson_svc, store = setup_services(tmp_path)
    importer = LegacyLessonImporter(asset_store=store)
    file_path = FIXTURES_ROOT / "khtn9_refraction" / "khtn9_refraction.tex"
    assert file_path.is_file(), f"Missing fixture {file_path}"

    dry = importer.dry_run(file_path)
    assert dry.coverage_percent >= 95.0
    assert len(dry.blocks) >= 3

    # Import to lesson
    doc = importer.import_to_lesson(dry, lesson_svc)

    # Check asset staged in blocks
    all_assets = {}
    for b in doc["blocks"]:
        all_assets.update(b.get("assets", {}))
    assert len(all_assets) >= 1, "Expected staged image asset in blocks"
    asset_info = list(all_assets.values())[0]
    staged_path = store.root / asset_info["path"]
    assert staged_path.is_file(), f"Staged asset does not exist: {staged_path}"
    assert hashlib.sha256(staged_path.read_bytes()).hexdigest() == asset_info["hash"]

    # Verify TikZ preserved verbatim in block source
    all_source = "\n".join(b["source"] for b in doc["blocks"])
    assert r"\begin{tikzpicture}" in all_source
    assert "Tia tới" in all_source
    assert "Tia khúc xạ" in all_source

    # Export teacher
    teacher_folder = lesson_svc.export(doc, tmp_path / "export_khtn_teacher", audience="teacher")
    res_t = run_pdflatex(teacher_folder)
    assert res_t.returncode == 0, f"Teacher compile failed: {res_t.stdout.decode('utf-8', 'replace')[-1000:]}"

    # Export student
    student_folder = lesson_svc.export(doc, tmp_path / "export_khtn_student", audience="student")
    res_s = run_pdflatex(student_folder)
    assert res_s.returncode == 0, f"Student compile failed: {res_s.stdout.decode('utf-8', 'replace')[-1000:]}"

    # Verify student PDF contains TikZ text but no solution
    with pymupdf.open(student_folder / "bai-giang.pdf") as pdf:
        student_text = "".join(page.get_text() for page in pdf)
    assert "Pháp tuyến" in student_text
    assert "chiết quang hơn" not in student_text


def test_physics10_recursive_input_and_relocation(tmp_path):
    """Vật lí 10: Multi-level recursive \\input, ex_test, graph TikZ, and bundle relocation."""
    services, lesson_svc, store = setup_services(tmp_path)
    importer = LegacyLessonImporter(asset_store=store)
    file_path = FIXTURES_ROOT / "physics10_motion" / "main.tex"
    assert file_path.is_file(), f"Missing fixture {file_path}"

    dry = importer.dry_run(file_path)
    assert dry.coverage_percent >= 95.0
    assert len(dry.warnings) == 0
    # Must have imported contents from LyThuyet, DangToan, and BTVD
    all_source = "\n".join(b["source"] for b in dry.blocks)
    assert "a = \\text{const}" in all_source or "a = \\mathrm{const}" in all_source or "gia tốc không đổi" in all_source
    assert "Một ô tô chuyển động nhanh dần đều" in all_source
    assert "Một đoàn tàu đang chạy" in all_source
    assert "Tính quãng đường vật đi được trong" in all_source

    doc = importer.import_to_lesson(dry, lesson_svc)

    # Export bundle
    export_dir = tmp_path / "orig_export"
    bundle_path = lesson_svc.export(doc, export_dir, audience="teacher")
    assert (bundle_path / "bai-giang.pdf").is_file()

    # Relocation test: Move exported bundle to completely different path and recompile
    relocated_dir = tmp_path / "relocated_bundles" / "moved_physics10"
    shutil.copytree(bundle_path, relocated_dir)

    res_reloc = run_pdflatex(relocated_dir)
    assert res_reloc.returncode == 0, f"Relocated compilation failed: {res_reloc.stdout.decode('utf-8', 'replace')[-1000:]}"
    assert (relocated_dir / "main.pdf").is_file() or (relocated_dir / "bai-giang.pdf").is_file()


def test_edge_case_nested_environments(tmp_path):
    """Nested environments (ex -> enumerate -> align* + tikz; loigiai -> itemize)."""
    _, _, store = setup_services(tmp_path)
    importer = LegacyLessonImporter(asset_store=store)
    file_path = FIXTURES_ROOT / "edge_cases" / "nested_env.tex"

    dry = importer.dry_run(file_path)
    ex_block = [b for b in dry.blocks if b["kind"] in ("exercise", "example")][0]

    # Verify everything was captured inside this one question block without truncation
    assert r"\begin{align*}" in ex_block["source"]
    assert r"\begin{tikzpicture}" in ex_block["source"]
    assert r"\begin{itemize}" in ex_block["source"]
    assert r"(x, y) = (2, 1)" in ex_block["source"]


def test_edge_case_missing_asset(tmp_path):
    """Missing asset reported in warnings, not crashed."""
    _, _, store = setup_services(tmp_path)
    importer = LegacyLessonImporter(asset_store=store)
    file_path = FIXTURES_ROOT / "edge_cases" / "missing_asset.tex"

    dry = importer.dry_run(file_path)
    assert len(dry.warnings) >= 1
    assert any("anh_hoan_toan_khong_ton_tai_12345.png" in w for w in dry.warnings)


def test_edge_case_circular_input(tmp_path):
    """Circular \\input loop detected and safely halted without infinite loop."""
    _, _, store = setup_services(tmp_path)
    importer = LegacyLessonImporter(asset_store=store)
    file_path = FIXTURES_ROOT / "edge_cases" / "cycle_main.tex"

    dry = importer.dry_run(file_path)
    assert len(dry.warnings) >= 1 or len(dry.unresolved_dependencies) >= 1
    all_warnings = " ".join(dry.warnings) + " ".join(str(d) for d in dry.unresolved_dependencies)
    assert "circular" in all_warnings.lower() or "vòng lặp" in all_warnings.lower() or "cycle" in all_warnings.lower()
    all_source = "\n".join(b["source"] for b in dry.blocks)
    assert "Bắt đầu tài liệu" in all_source
    assert "Nội dung file A" in all_source


def test_edge_case_uncertified_macro_fail_closed(tmp_path):
    """Uncertified macro in question block causes fail-closed with exact block location and line number."""
    _, lesson_svc, _ = setup_services(tmp_path)
    doc = lesson_svc.create("Bài test bảo mật", "Toán", "10")
    b = block(
        "exercise",
        "Khối bảo mật đặc biệt",
        source=r"\begin{ex} Đề thi \dangerousteachercheat{Secret123} \loigiai{Lời giải} \end{ex}",
    )
    b["policy"] = "question"
    doc["blocks"].append(b)

    with pytest.raises(ValueError) as exc:
        lesson_svc.body(doc, audience="student")

    err = str(exc.value)
    assert "Khối 'Khối bảo mật đặc biệt'" in err
    assert "dangerousteachercheat" in err
    assert "chưa được chứng nhận" in err


def test_edge_case_syntax_error(tmp_path):
    """Syntax error (unclosed environment/brace) handled gracefully without uncaught crash."""
    _, _, store = setup_services(tmp_path)
    importer = LegacyLessonImporter(asset_store=store)
    file_path = FIXTURES_ROOT / "edge_cases" / "syntax_error.tex"

    dry = importer.dry_run(file_path)
    # Parser should capture remaining text as raw or theory block rather than throwing unhandled exception
    assert len(dry.blocks) >= 1
    assert "đoạn văn chưa đóng ngoặc" in "\n".join(b["source"] for b in dry.blocks)
