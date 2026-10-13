import json
import pytest
from pathlib import Path
from PySide6.QtCore import Qt

from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.lessons import LessonService, build_template_blocks
from latex_question_studio.ui.main_window import MainWindow


def test_lesson_template_and_three_folder_manifest(tmp_path):
    services = create_services(AppConfig.load(tmp_path))
    svc = LessonService(services)

    # 1. Create lesson from standard template with 2 methods
    doc = svc.create(
        title="Chuyên đề Hàm số 12",
        subject="Toán",
        grade="12",
        template_key="standard",
        num_methods=2,
        include_warmup=True,
        include_homework=True,
    )
    assert doc["id"] is not None
    assert doc["title"] == "Chuyên đề Hàm số 12"
    assert doc["revision"] == 1

    # 2. Verify 3-folder manifest: LyThuyet/, DangToan/, BTVD/
    files = svc.file_manifest(doc)
    roles = [f["role"] for f in files]
    assert "theory" in roles
    assert "method" in roles
    assert "exercise" in roles

    # Expect 1 theory file, 2 method files, 1 exercise file
    theory_files = [f for f in files if f["role"] == "theory"]
    method_files = [f for f in files if f["role"] == "method"]
    exercise_files = [f for f in files if f["role"] == "exercise"]

    assert len(theory_files) == 1
    assert theory_files[0]["filename"].startswith("LyThuyet/")
    assert len(method_files) == 2
    for m in method_files:
        assert m["filename"].startswith("DangToan/")
    assert len(exercise_files) == 1
    assert exercise_files[0]["filename"].startswith("BTVD/")

    # 3. Check SQLite persistence in lesson_files
    records = svc.file_records(doc["id"])
    assert len(records) == len(files)


def test_insert_bank_questions_with_math_and_tikz(tmp_path):
    services = create_services(AppConfig.load(tmp_path))
    svc = LessonService(services)

    # Create questions with TikZ, display math, and ex_test macros in question bank
    tikz_q = services.questions.create(
        r"""\begin{ex}
Cho đồ thị hàm số $y=f(x)$ như hình vẽ:
\begin{tikzpicture}[scale=0.8]
\draw[->] (-2,0) -- (3,0) node[right] {$x$};
\draw[->] (0,-2) -- (0,3) node[above] {$y$};
\draw[domain=-1.5:2.5,smooth,variable=\x,blue,thick] plot ({\x},{\x^2 - \x - 1});
\end{tikzpicture}
Khẳng định nào sau đây đúng?
\choice{Hàm số nghịch biến trên $(1; +\infty)$}{\True Hàm số đồng biến trên $(1; +\infty)$}{Hàm số đồng biến trên $(-\infty; 0)$}{Hàm số nghịch biến trên $(-1; 2)$}
\loigiai{Dựa vào bảng biến thiên và đồ thị, trên $(1; +\infty)$ đồ thị đi lên nên hàm số đồng biến.}
\end{ex}""",
        "mcq",
        cognitive_level="TH",
    )

    doc = svc.create(title="Khảo sát hàm số", template_key="legacy")
    # Insert question into lesson exercises
    updated = svc.insert_questions(doc, [tikz_q.id], kind="exercise")
    saved = svc.save(updated)

    # Check question block was attached with pinned revision
    inserted_block = next((b for b in saved["blocks"] if b.get("question") and b["question"]["id"] == tikz_q.id), None)
    assert inserted_block is not None
    assert inserted_block["question"]["revision"] == 1
    assert r"\begin{tikzpicture}" in inserted_block["source"]

    # Lock file and check exercise ordering table
    locked_doc = svc.lock_file(saved, "exercise", locked=True)
    svc.save(locked_doc)

    records = svc.file_records(saved["id"])
    ex_record = next(r for r in records if r["role"] == "exercise")
    assert ex_record["locked"] is True
    assert len(ex_record["exercises"]) == 1
    assert ex_record["exercises"][0]["question_id"] == tikz_q.id


def test_lesson_export_bundle_three_folders_and_manifest(tmp_path):
    services = create_services(AppConfig.load(tmp_path / "data"))
    svc = LessonService(services)

    # Question with attached asset
    asset_file = tmp_path / "sample_chart.png"
    asset_file.write_bytes(
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\xf8\xcf\xc0\xf0\x1f\x00\x05\x00\x01\xff\x89\x99=\x1d\x00\x00\x00\x00IEND\xaeB`\x82'
    )

    q = services.questions.create(
        r"\begin{ex} Đồ thị dưới đây minh họa bài toán: \includegraphics[width=.5\linewidth]{sample_chart.png} \choice{A}{\True B}{C}{D} \loigiai{Xem hình.} \end{ex}"
    )
    import hashlib
    content_hash = hashlib.sha256(asset_file.read_bytes()).hexdigest()
    with services.database.transaction() as c:
        c.execute(
            "INSERT INTO assets (id, content_hash, relative_path, bytes) VALUES (?,?,?,?)",
            ("a_chart", content_hash, "assets/chart.png", asset_file.stat().st_size),
        )
        c.execute("INSERT INTO question_assets (question_id, asset_id, original_reference) VALUES (?,?,?)", (q.id, "a_chart", "sample_chart.png"))
    (services.config.data_dir / "assets").mkdir(parents=True, exist_ok=True)
    (services.config.data_dir / "assets" / "chart.png").write_bytes(asset_file.read_bytes())

    # Create and prepare lesson
    doc = svc.create(title="Bài giảng Đại số và Giải tích", template_key="legacy")
    doc = svc.insert_questions(doc, [q.id], kind="exercise")
    doc = svc.lock_file(doc, "exercise", locked=True)
    doc = svc.save(doc)

    export_dest = tmp_path / "exports"
    # Export for student and teacher
    teacher_bundle = svc.export(doc, export_dest, audience="teacher")
    assert teacher_bundle.is_dir()

    # 1. Verify 3-folder structure in exported bundle
    assert (teacher_bundle / "LyThuyet").is_dir()
    assert (teacher_bundle / "DangToan").is_dir()
    assert (teacher_bundle / "BTVD").is_dir()
    assert (teacher_bundle / "main.tex").is_file()
    assert (teacher_bundle / "manifest.json").is_file()

    # 2. Verify main.tex links all 3 folders with \input
    main_tex = (teacher_bundle / "main.tex").read_text(encoding="utf-8")
    assert r"\input{LyThuyet/ly-thuyet}" in main_tex
    assert r"\input{DangToan/dang-01-" in main_tex
    assert r"\input{BTVD/bai-tap-van-dung}" in main_tex

    # 3. Verify manifest.json
    manifest = json.loads((teacher_bundle / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["audience"] == "teacher"
    assert manifest["lesson_id"] == doc["id"]
    assert "main.tex" in manifest["sha256"]
    assert "LyThuyet/ly-thuyet.tex" in manifest["sha256"]
    assert "BTVD/bai-tap-van-dung.tex" in manifest["sha256"]

    # 4. Verify student bundle hides solutions
    student_bundle = svc.export(doc, export_dest, audience="student")
    assert student_bundle.is_dir()
    student_ex_tex = (student_bundle / "BTVD" / "bai-tap-van-dung.tex").read_text(encoding="utf-8")
    # Must NOT expose solution in student exercise file
    assert "Xem hình." not in student_ex_tex
    assert r"\loigiai" not in student_ex_tex


def test_lesson_ui_document_editor(qtbot, tmp_path):
    services = create_services(AppConfig.load(tmp_path))
    svc = LessonService(services)
    doc = svc.create(title="Bài học UI Test", template_key="legacy")

    window = MainWindow(services)
    qtbot.addWidget(window)
    window.show()

    # Switch to Lesson page (Page 4)
    window.show_page(4)
    lesson_ui = window.lesson_page

    # Verify Document Editor structure:
    # 1. Left outline tree
    assert lesson_ui.tree is not None
    assert lesson_ui.tree.topLevelItemCount() > 0

    # 2. File source combo box (3-folder view)
    assert lesson_ui.file_source is not None
    assert lesson_ui.file_source.count() >= 3

    # 3. Canvas editor and title
    assert lesson_ui.title.text() == "Bài học UI Test"
    assert lesson_ui.editor is not None

    # Test adding a block and saving via UI
    lesson_ui.add_block(child=False)
    assert lesson_ui.tree.topLevelItemCount() > 0

    window.close()
