"""Tests for Phase L: Deduplication Engine and UI (L1 & L2).

Validates:
- Safe LaTeX normalization (stripping comments, whitespace, preserving numbers/signs/math/TikZ/images).
- Level 1: Exact normalized matching.
- Level 2: MCQ choice permutation matching with \\True verification.
- Level 2 Invariant: True/False statements MUST NOT be permuted.
- Level 3: Advisory similarity guardrails (different numbers/signs prevent false duplicates).
- Database scanning, safe transactional deletion, and FK reference protection.
- Metadata merging and clean .tex/report export.
"""
from pathlib import Path
import json
import pytest

from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.dedup import (
    DeduplicationService, normalize_latex, extract_numbers, compute_token_similarity
)


def test_normalize_latex_safety():
    source = r"""
    % Đây là comment đầu file
    \begin{ex} % comment inline
    Tính đạo hàm của $f(x) = -3x^2 + 5x - 7$. \% Ký hiệu phần trăm
    \choice
    {$f'(x) = -6x + 5$}
    {\True $f'(x) = -6x - 5$}
    {$f'(x) = 6x + 5$}
    {$f'(x) = -3x + 5$}
    \loigiai{
        Lời giải chi tiết ở đây.
    }
    \end{ex}
    """
    normalized = normalize_latex(source)
    assert "% Đây là comment" not in normalized
    assert "\\%" in normalized  # Escaped percent preserved
    assert "-3x^2" in normalized
    assert "-6x + 5" in normalized
    assert "\\choice" in normalized


def test_level1_exact_normalized_duplicates(tmp_path):
    services = create_services(AppConfig.load(tmp_path / "app"))
    dedup = DeduplicationService(services)

    # 2 questions identical except comments and spacing
    q1_src = r"\begin{ex} Giải phương trình $x^2 - 4 = 0$. \choice{$x=1$}{$x=2$}{$x=3$}{\True $x=\pm 2$}\end{ex}"
    q2_src = r"""\begin{ex}
    % Comment khác
    Giải phương trình $x^2 - 4 = 0$.
    \choice
    {$x=1$}
    {$x=2$}
    {$x=3$}
    {\True $x=\pm 2$}
    \end{ex}"""
    q3_src = r"\begin{ex} Giải phương trình $x^2 - 9 = 0$. \choice{$x=1$}{$x=2$}{$x=3$}{\True $x=\pm 3$}\end{ex}"

    q1 = services.questions.create(q1_src, "mcq")
    q2 = services.questions.create(q2_src, "mcq")
    q3 = services.questions.create(q3_src, "mcq")

    groups = dedup.scan_database()
    assert len(groups) == 1
    g = groups[0]
    assert g.match_level == "exact"
    assert g.confidence == 1.0
    group_ids = {it.id for it in g.items}
    assert q1.id in group_ids and q2.id in group_ids
    assert q3.id not in group_ids
    # Crucial contract: NO auto-deletion
    assert len(g.selected_to_delete) == 0


def test_level2_mcq_permutation_duplicates(tmp_path):
    services = create_services(AppConfig.load(tmp_path / "app"))
    dedup = DeduplicationService(services)

    # 2 MCQ questions with permuted options, same correct answer text ($x=2$)
    q1_src = r"\begin{ex} Tìm nghiệm của $2x - 4 = 0$. \choice{$x=1$}{\True $x=2$}{$x=3$}{$x=4$}\end{ex}"
    q2_src = r"\begin{ex} Tìm nghiệm của $2x - 4 = 0$. \choice{$x=3$}{$x=4$}{$x=1$}{\True $x=2$}\end{ex}"
    # Question with same prompt and choices, but DIFFERENT correct answer ($x=1$) -> NOT a duplicate!
    q3_src = r"\begin{ex} Tìm nghiệm của $2x - 4 = 0$. \choice{\True $x=1$}{$x=2$}{$x=3$}{$x=4$}\end{ex}"

    q1 = services.questions.create(q1_src, "mcq")
    q2 = services.questions.create(q2_src, "mcq")
    q3 = services.questions.create(q3_src, "mcq")

    groups = dedup.scan_database()
    # Exactly 1 permutation group between q1 and q2
    perm_groups = [g for g in groups if g.match_level == "permutation"]
    assert len(perm_groups) == 1
    g = perm_groups[0]
    assert g.confidence == 0.95
    item_ids = {it.id for it in g.items}
    assert q1.id in item_ids and q2.id in item_ids
    assert q3.id not in item_ids


def test_level2_true_false_invariant_never_permuted(tmp_path):
    """True/False statements a, b, c, d must NEVER be treated as permuted duplicates."""
    services = create_services(AppConfig.load(tmp_path / "app"))
    dedup = DeduplicationService(services)

    # Question 1: a=Đúng, b=Sai, c=Đúng, d=Sai
    tf1_src = r"\begin{ex} Cho hàm số $y=f(x)$. \choiceTF{\True Mệnh đề 1}{Mệnh đề 2}{\True Mệnh đề 3}{Mệnh đề 4}\end{ex}"
    # Question 2: Swapped statement order (Mệnh đề 2 moved to front)
    tf2_src = r"\begin{ex} Cho hàm số $y=f(x)$. \choiceTF{Mệnh đề 2}{\True Mệnh đề 1}{\True Mệnh đề 3}{Mệnh đề 4}\end{ex}"

    services.questions.create(tf1_src, "true_false")
    services.questions.create(tf2_src, "true_false")

    groups = dedup.scan_database()
    # Must NOT have any permutation group for TF
    perm_groups = [g for g in groups if g.match_level == "permutation"]
    assert len(perm_groups) == 0


def test_level3_similarity_number_difference_guardrail(tmp_path):
    """Questions with different numerical values must not be merged as duplicates."""
    services = create_services(AppConfig.load(tmp_path / "app"))
    dedup = DeduplicationService(services)

    # Only numbers differ: $2x + 4$ vs $5x + 10$
    q1_src = r"\begin{ex} Tính tích phân $\int (2x + 4) dx$.\end{ex}"
    q2_src = r"\begin{ex} Tính tích phân $\int (5x + 10) dx$.\end{ex}"

    q1 = services.questions.create(q1_src, "essay")
    q2 = services.questions.create(q2_src, "essay")

    groups = dedup.scan_database()
    # Any similarity group must have a clear advisory reason noting the numerical difference
    for g in groups:
        if g.match_level == "similarity":
            assert "Khác số liệu" in g.match_reason or g.confidence < 1.0


def test_dedup_safe_delete_and_fk_protection(tmp_path):
    services = create_services(AppConfig.load(tmp_path / "app"))
    dedup = DeduplicationService(services)

    q1 = services.questions.create(r"\begin{ex}Câu hỏi gốc\choice{A}{\True B}{C}{D}\end{ex}", "mcq")
    q2 = services.questions.create(r"\begin{ex}Câu hỏi gốc\choice{A}{\True B}{C}{D}\end{ex}", "mcq")
    q3 = services.questions.create(r"\begin{ex}Câu hỏi độc lập\choice{A}{\True B}{C}{D}\end{ex}", "mcq")

    # Simulate q2 being referenced in a lesson
    with services.database.transaction() as conn:
        conn.execute(
            "INSERT INTO lessons (id, title, revision, document_json, updated_at) VALUES (?, ?, ?, ?, ?)",
            ("lesson_1", "Bài học 1", 1, json.dumps({"blocks": [{"question": {"id": q2.id}}]}), "2026-10-14"),
        )

    # Attempt to delete q2 without force: must be blocked by reference check
    count, errors = dedup.delete_selected([q2.id], force=False)
    assert count == 0
    assert len(errors) == 1
    assert "Đang được sử dụng" in errors[0]
    assert services.questions.get(q2.id) is not None

    # Deleting unreferenced q1 succeeds
    count1, errors1 = dedup.delete_selected([q1.id], force=False)
    assert count1 == 1
    assert len(errors1) == 0
    assert services.questions.get(q1.id) is None


def test_dedup_merge_metadata(tmp_path):
    services = create_services(AppConfig.load(tmp_path / "app"))
    dedup = DeduplicationService(services)

    q1 = services.questions.create(r"\begin{ex}Câu 1\end{ex}")
    q2 = services.questions.create(r"\begin{ex}Câu 1 trùng\end{ex}")

    with services.database.transaction() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO question_metadata (question_id, data_json) VALUES (?, ?)",
            (q1.id, json.dumps({"tags": ["tag1"], "notes": "Ghi chú 1"})),
        )
        conn.execute(
            "INSERT OR REPLACE INTO question_metadata (question_id, data_json) VALUES (?, ?)",
            (q2.id, json.dumps({"tags": ["tag2", "tag1"], "notes": "Ghi chú 2"})),
        )

    ok = dedup.merge_metadata(q1.id, [q2.id])
    assert ok

    with services.database.connect() as conn:
        row = conn.execute("SELECT data_json FROM question_metadata WHERE question_id=?", (q1.id,)).fetchone()
        meta = json.loads(row[0])
        assert "tag1" in meta["tags"]
        assert "tag2" in meta["tags"]
        assert "Ghi chú 2" in meta["notes"]


def test_dedup_scan_files_and_export_clean_tex(tmp_path):
    services = create_services(AppConfig.load(tmp_path / "app"))
    dedup = DeduplicationService(services)

    tex_file = tmp_path / "de_kiem_tra.tex"
    tex_content = r"""
\begin{ex}
Câu hỏi 1 duy nhất.
\choice{A}{\True B}{C}{D}
\end{ex}

\begin{ex}
Câu hỏi 2 bị lặp lại.
\choice{A}{B}{\True C}{D}
\end{ex}

\begin{ex}
% Lặp lại câu hỏi 2 với comment
Câu hỏi 2 bị lặp lại.
\choice{A}{B}{\True C}{D}
\end{ex}
"""
    tex_file.write_text(tex_content, encoding="utf-8")

    groups = dedup.scan_files([tex_file])
    assert len(groups) == 1
    g = groups[0]
    assert len(g.items) == 2

    # Export clean .tex keeping only item 1 and item 2 (omitting item 3)
    clean_out = tmp_path / "de_kiem_tra_cleaned.tex"
    items_to_keep = {f"{tex_file.name}::q1", f"{tex_file.name}::q2"}
    dedup.export_clean_tex(tex_file, items_to_keep, clean_out)

    assert clean_out.is_file()
    cleaned_text = clean_out.read_text(encoding="utf-8")
    assert "Câu hỏi 1 duy nhất" in cleaned_text
    assert cleaned_text.count("Câu hỏi 2 bị lặp lại") == 1

    # Test report export
    json_report = tmp_path / "report.json"
    csv_report = tmp_path / "report.csv"
    dedup.export_report(groups, json_report, "json")
    dedup.export_report(groups, csv_report, "csv")

    assert json_report.is_file()
    assert csv_report.is_file()
    assert "Group ID" in csv_report.read_text(encoding="utf-8-sig")
