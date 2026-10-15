"""Tests for Phase M.2.2: Deduplication Engine & Scope-Separated Deletion.

Verifies:
1. SQLite Bank deletion: Rowcount check, FK reference protection, metadata cleanup, zero false success.
2. .tex File Mode: Non-destructive cleaning preserving preamble, theory, comments, TikZ, and order.
3. Multi-file support: Independent cleaning of multiple files without modifying originals.
4. UI interaction on DedupPage: Scope switching, dynamic action bar counts, primary protection.
"""
from pathlib import Path
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox

from latex_question_studio.application.dedup import (
    DeduplicationService, DuplicateGroup, DuplicateItem, normalize_latex
)
from latex_question_studio.application.services import create_services
from latex_question_studio.app.config import AppConfig
from latex_question_studio.ui.pages.dedup_page import DedupPage


@pytest.fixture
def test_services(tmp_path):
    config = AppConfig.load(tmp_path / "app")
    return create_services(config)


def test_sqlite_delete_selected_verified_rowcount(test_services):
    """Verifies SQLite deletion checks rowcount and never reports false success for nonexistent IDs."""
    service = DeduplicationService(test_services)

    # 1. Insert 2 sample questions
    with test_services.database.transaction() as conn:
        conn.execute(
            "INSERT INTO questions (id, revision, latex_source, question_type, solution, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("q_real_1", 1, "\\begin{ex} Cau 1 \\choice{A}{B}{C}{D} \\end{ex}", "mcq", "Loi giai 1", "2026-10-15", "2026-10-15")
        )
        conn.execute(
            "INSERT INTO questions (id, revision, latex_source, question_type, solution, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("q_real_2", 1, "\\begin{ex} Cau 2 \\choice{A}{B}{C}{D} \\end{ex}", "mcq", "Loi giai 2", "2026-10-15", "2026-10-15")
        )
        conn.execute(
            "INSERT INTO question_metadata (question_id, data_json) VALUES (?, ?)",
            ("q_real_1", '{"tags": ["toan10"]}')
        )

    # 2. Try deleting a real question and a nonexistent question
    count, errors = service.delete_selected(["q_real_1", "q_nonexistent_999"])
    assert count == 1
    assert len(errors) == 1
    assert "q_nonexi" in errors[0]

    # Verify real_1 is deleted, including metadata
    with test_services.database.connect() as conn:
        q_row = conn.execute("SELECT id FROM questions WHERE id = 'q_real_1'").fetchone()
        assert q_row is None
        meta_row = conn.execute("SELECT question_id FROM question_metadata WHERE question_id = 'q_real_1'").fetchone()
        assert meta_row is None
        # real_2 still exists
        assert conn.execute("SELECT id FROM questions WHERE id = 'q_real_2'").fetchone() is not None


def test_sqlite_delete_preserves_referenced_questions(test_services):
    """Verifies questions referenced in lessons or exams are protected from deletion."""
    service = DeduplicationService(test_services)

    with test_services.database.transaction() as conn:
        conn.execute(
            "INSERT INTO questions (id, revision, latex_source, question_type, solution, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("q_referenced", 1, "\\begin{ex} Cau dang dung \\end{ex}", "essay", "", "2026-10-15", "2026-10-15")
        )
        conn.execute(
            "INSERT INTO lessons (id, title, revision, document_json, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("lesson_1", "Chuyen de Ham so", 1, '{"blocks": [{"question_id": "q_referenced"}]}', "2026-10-15")
        )

    # Attempt deletion
    count, errors = service.delete_selected(["q_referenced"])
    assert count == 0
    assert len(errors) == 1
    assert "Đang được sử dụng trong" in errors[0]
    assert "Chuyen de Ham so" in errors[0]

    # Verify question was NOT deleted
    with test_services.database.connect() as conn:
        row = conn.execute("SELECT id FROM questions WHERE id = 'q_referenced'").fetchone()
        assert row is not None


def test_file_clean_preserves_preamble_theory_and_order(test_services, tmp_path):
    """Verifies cleaning .tex files removes only targeted question spans, preserving preamble and theory."""
    service = DeduplicationService(test_services)

    source_tex = tmp_path / "de_toan_chuan.tex"
    original_content = r"""\documentclass[12pt,a4paper]{article}
\usepackage{amsmath,amssymb}
\usepackage[utf8]{vietnam}
\usepackage{tikz}

\begin{document}
\section{LÝ THUYẾT TRỌNG TÂM}
Định lý Pythagoras: Trong tam giác vuông, bình phương cạnh huyền bằng tổng bình phương hai cạnh góc vuông.
% Đây là comment quan trọng của giáo viên

\section{BÀI TẬP VẬN DỤNG}

\begin{ex}
Câu hỏi 1: Tìm $x$ biết $x + 2 = 5$.
\choice{\True $x=3$}{$x=2$}{$x=1$}{$x=0$}
\loigiai{Ta có $x = 5 - 2 = 3$.}
\end{ex}

\begin{ex}
Câu hỏi 2: Đây là câu bị lặp lại.
\choice{$A$}{\True $B$}{$C$}{$D$}
\loigiai{Lời giải câu 2.}
\end{ex}

\begin{ex}
Câu hỏi 3: Câu hỏi số 3 độc nhất.
\choice{$A$}{$B$}{\True $C$}{$D$}
\end{ex}

\begin{ex}
Câu hỏi 2: Đây là câu bị lặp lại.
\choice{$A$}{\True $B$}{$C$}{$D$}
\loigiai{Lời giải câu 2.}
\end{ex}

\section{TỔNG KẾT BÀI HỌC}
Chúc các em học tốt!
\end{document}
"""
    source_tex.write_text(original_content, encoding="utf-8")

    # 1. Scan files
    groups = service.scan_files([source_tex])
    assert len(groups) == 1
    group = groups[0]
    assert len(group.items) == 2  # item 2 and item 4

    # Verify span offsets are extracted
    for it in group.items:
        assert it.file_path == str(source_tex.resolve())
        assert it.span_start > 0
        assert it.span_end > it.span_start

    # Mark the duplicate (the second occurrence) for removal
    duplicate_item = group.items[1]
    cleaned_tex = tmp_path / "de_toan_chuan_cleaned.tex"

    # 2. Clean tex files
    results = service.clean_tex_files(
        [duplicate_item],
        output_map={str(source_tex.resolve()): cleaned_tex}
    )

    assert str(source_tex.resolve()) in results
    res = results[str(source_tex.resolve())]
    assert res["removed_count"] == 1
    assert res["remaining_count"] == 3
    assert res["original_count"] == 4

    # 3. Verify original file is COMPLETELY UNTOUCHED
    assert source_tex.read_text(encoding="utf-8") == original_content

    # 4. Verify cleaned file content fidelity
    cleaned_content = cleaned_tex.read_text(encoding="utf-8")
    assert r"\documentclass[12pt,a4paper]{article}" in cleaned_content
    assert r"\section{LÝ THUYẾT TRỌNG TÂM}" in cleaned_content
    assert "Định lý Pythagoras" in cleaned_content
    assert "% Đây là comment quan trọng của giáo viên" in cleaned_content
    assert r"\section{BÀI TẬP VẬN DỤNG}" in cleaned_content
    assert "Câu hỏi 1: Tìm $x$ biết $x + 2 = 5$." in cleaned_content
    assert "Câu hỏi 3: Câu hỏi số 3 độc nhất." in cleaned_content
    assert r"\section{TỔNG KẾT BÀI HỌC}" in cleaned_content
    assert r"\end{document}" in cleaned_content

    # Exactly 1 occurrence of Question 2 remains
    assert cleaned_content.count("Câu hỏi 2: Đây là câu bị lặp lại.") == 1


def test_multi_file_dedup_and_clean(test_services, tmp_path):
    """Verifies deduplication across multiple .tex files and multi-file cleaned export."""
    service = DeduplicationService(test_services)

    file1 = tmp_path / "de_so_1.tex"
    file2 = tmp_path / "de_so_2.tex"

    content1 = r"""\documentclass{article}
\begin{document}
\begin{ex}
Câu hỏi chung giữa 2 đề thi.
\choice{\True A}{B}{C}{D}
\end{ex}
\begin{ex}
Tính diện tích hình tròn có bán kính $R = 5$.
\choice{\True $25\pi$}{$10\pi$}{$5\pi$}{$50\pi$}
\end{ex}
\end{document}
"""

    content2 = r"""\documentclass{article}
\begin{document}
\begin{ex}
Câu hỏi chung giữa 2 đề thi.
\choice{\True A}{B}{C}{D}
\end{ex}
\begin{ex}
Giải phương trình bậc hai $x^2 - 4x + 3 = 0$.
\choice{$x=1$}{$x=2$}{\True $x=1; x=3$}{$x=4$}
\end{ex}
\end{document}
"""

    file1.write_text(content1, encoding="utf-8")
    file2.write_text(content2, encoding="utf-8")

    groups = service.scan_files([file1, file2])
    assert len(groups) == 1
    g = groups[0]
    assert len(g.items) == 2
    assert g.items[0].file_path != g.items[1].file_path

    # Keep file1's question as primary, remove file2's duplicate
    item_to_remove = next(it for it in g.items if it.file_path == str(file2.resolve()))

    out_dir = tmp_path / "cleaned_output"
    results = service.clean_tex_files([item_to_remove], output_dir=out_dir)

    assert str(file2.resolve()) in results
    out_file2 = results[str(file2.resolve())]["output_path"]
    assert out_file2.is_file()
    c2 = out_file2.read_text(encoding="utf-8")
    assert "Câu hỏi chung giữa 2 đề thi." not in c2
    assert "Giải phương trình bậc hai $x^2 - 4x + 3 = 0$." in c2
    assert r"\documentclass{article}" in c2
    assert r"\end{document}" in c2

    # File 1 was not affected
    assert str(file1.resolve()) not in results
    assert file1.read_text(encoding="utf-8") == content1


def test_ui_dedup_page_scope_switching_and_counts(qtbot, test_services, monkeypatch):
    """UI test for DedupPage: scope switching, dynamic action button label, primary radio and selection count."""
    # Prevent popup modals from blocking
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: QMessageBox.StandardButton.Ok)
    monkeypatch.setattr(QMessageBox, "question", lambda *args, **kwargs: QMessageBox.StandardButton.Yes)

    page = DedupPage(test_services)
    qtbot.addWidget(page)
    page.resize(1366, 768)
    page.show()

    # 1. Initial scope is Database
    assert page.scope_combo.currentData() == "database"
    assert page.db_filter_widget.isVisible()
    assert not page.file_control_widget.isVisible()
    assert "Xóa khỏi ngân hàng CSDL" in page.delete_btn.text()
    assert not page.delete_btn.isEnabled()

    # 2. Switch scope to Files
    page.scope_combo.setCurrentIndex(1)
    assert page.scope_combo.currentData() == "files"
    assert not page.db_filter_widget.isVisible()
    assert page.file_control_widget.isVisible()
    assert "Loại câu khỏi file .tex" in page.delete_btn.text()
    assert not page.delete_btn.isEnabled()

    # 3. Simulate populated groups in File mode
    dummy_item1 = DuplicateItem(
        id="file1.tex::q1",
        source=r"\begin{ex} Cau trung 1 \end{ex}",
        normalized_source=r"\begin{ex} Cau trung 1 \end{ex}",
        question_type="mcq",
        source_location="file1.tex (dòng 5)",
        file_path="C:/temp/file1.tex",
        span_start=50,
        span_end=100,
    )
    dummy_item2 = DuplicateItem(
        id="file1.tex::q2",
        source=r"\begin{ex} Cau trung 1 \end{ex}",
        normalized_source=r"\begin{ex} Cau trung 1 \end{ex}",
        question_type="mcq",
        source_location="file1.tex (dòng 15)",
        file_path="C:/temp/file1.tex",
        span_start=150,
        span_end=200,
    )
    dummy_group = DuplicateGroup(
        group_id="test_group_1",
        match_level="exact",
        confidence=1.0,
        match_reason="Trùng 100%",
        items=[dummy_item1, dummy_item2],
        primary_id=dummy_item1.id,
    )

    page._on_scan_finished([dummy_group])
    assert page.group_list.count() == 1
    assert page.current_group_idx == 0

    # Verify action bar initially has 0 selected
    assert "(0 câu đã chọn)" in page.delete_btn.text()
    assert not page.delete_btn.isEnabled()

    # Check the checkbox for item 2
    page._toggle_delete(dummy_item2.id, True)
    assert "(1 câu đã chọn)" in page.delete_btn.text()
    assert page.delete_btn.isEnabled()

    # Change primary to item 2
    page._set_primary(dummy_item2.id, True)
    assert dummy_group.primary_id == dummy_item2.id
    # Primary cannot be selected to delete, so count resets to 0
    assert "(0 câu đã chọn)" in page.delete_btn.text()
    assert not page.delete_btn.isEnabled()
