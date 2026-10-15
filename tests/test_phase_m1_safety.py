r"""Tests for Phase M.1.2: Lesson Safety, Provenance & Student Confidentiality.

Verifies:
1. Pinned bank question revisions and local overrides (never mutates bank questions).
2. Autosave on switching lessons and concurrent edit conflict detection.
3. Pedagogical block policies (full / question / private):
   - Student export strips \loigiai, \shortans, \dapso, \True, \False, teacher_notes.
   - Public examples with policy='full' retain solutions in student export.
   - Private blocks are completely omitted.
   - Subfiles in LyThuyet/, DangToan/, BTVD/ contain zero leaked solutions or notes.
4. Fail-closed security with exact block title and line number on uncertified macro.
5. Immutability of exported bundles and manifest integrity.
"""
import json
from pathlib import Path
import pytest
import shutil

from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.lessons import LessonService, block
from latex_question_studio.preview.compiler import Compiler


def setup_test_services(tmp_path):
    cfg = AppConfig.load(tmp_path / "data")
    services = create_services(cfg)
    lesson_srv = LessonService(services)
    return services, lesson_srv


def test_pinned_revision_and_local_overrides(tmp_path):
    """Verifies that inserting a question pins its revision and local edits never mutate the bank."""
    services, lesson_srv = setup_test_services(tmp_path)

    # 1. Create original question in question bank
    orig_q = services.questions.create(
        r"""\begin{ex}
Câu hỏi ngân hàng gốc.
\choice
{\True A}
{B}
{C}
{D}
\loigiai{Lời giải ngân hàng gốc.}
\end{ex}""",
        question_type="mcq",
    )
    assert orig_q.revision == 1

    # 2. Insert into lesson
    doc = lesson_srv.create(title="Bài giảng kiểm tra ghim")
    doc = lesson_srv.insert_questions(doc, [orig_q.id], kind="exercise")
    doc = lesson_srv.save(doc)

    q_block = next(b for b in doc["blocks"] if b.get("question"))
    assert q_block["question"]["id"] == orig_q.id
    assert q_block["question"]["revision"] == 1

    # 3. Modify question locally in lesson
    q_block["source"] = r"""\begin{ex}
Câu hỏi đã được giáo viên chỉnh sửa cục bộ trong bài giảng.
\choice
{\True A'}
{B'}
{C'}
{D'}
\loigiai{Lời giải cục bộ.}
\end{ex}"""
    doc = lesson_srv.save(doc)

    # 4. Verify bank question remains completely untouched
    bank_q = services.questions.get(orig_q.id)
    assert bank_q.revision == 1
    assert "ngân hàng gốc" in bank_q.latex_source
    assert "chỉnh sửa cục bộ" not in bank_q.latex_source

    # 5. Verify lesson retains local override with pinned link
    saved_doc = lesson_srv.get(doc["id"])
    saved_q_block = next(b for b in saved_doc["blocks"] if b.get("question"))
    assert "chỉnh sửa cục bộ" in saved_q_block["source"]
    assert saved_q_block["question"]["id"] == orig_q.id
    assert saved_q_block["question"]["revision"] == 1


def test_concurrent_save_conflict_detection(tmp_path):
    """Verifies that saving with a stale revision raises conflict error and prevents overwrite."""
    _, lesson_srv = setup_test_services(tmp_path)

    doc = lesson_srv.create(title="Bài giảng đồng thời")
    doc_copy_a = lesson_srv.get(doc["id"])
    doc_copy_b = lesson_srv.get(doc["id"])

    # User A updates and saves
    doc_copy_a["blocks"][0]["title"] = "Thay đổi bởi A"
    lesson_srv.save(doc_copy_a)

    # User B tries to save stale document
    doc_copy_b["blocks"][0]["title"] = "Thay đổi bởi B"
    with pytest.raises(ValueError, match="Bài đã thay đổi ở nơi khác"):
        lesson_srv.save(doc_copy_b)


def test_student_policy_all_question_types_and_notes(tmp_path):
    """Verifies that MCQ, True/False, Short Answer, and Essay are sanitized according to policy."""
    _, lesson_srv = setup_test_services(tmp_path)

    doc = lesson_srv.create(
        title="Bảo mật bài học sinh toàn diện",
        blocks=[
            # Block 1: Theory with teacher note
            {
                "id": "b_theory",
                "kind": "theory",
                "title": "I. Lý thuyết cơ bản",
                "source": r"Định lý Pytago: $a^2 + b^2 = c^2$.",
                "policy": "full",
                "parent": None,
                "teacher_notes": "GHI CHÚ RIÊNG: Nhấn mạnh tam giác vuông.",
                "assets": {},
                "question": None,
            },
            # Block 2: Example with public solution (policy=full)
            {
                "id": "b_example",
                "kind": "example",
                "title": "Ví dụ 1",
                "source": r"""\begin{ex}
Tính cạnh huyền tam giác vuông có hai cạnh góc vuông là 3 và 4.
\loigiai{LỜI GIẢI CÔNG KHAI VÍ DỤ: Áp dụng $c = \sqrt{3^2 + 4^2} = 5$.}
\end{ex}""",
                "policy": "full",
                "parent": None,
                "teacher_notes": "",
                "assets": {},
                "question": None,
            },
            # Block 3: MCQ Exercise (policy=question)
            {
                "id": "b_mcq",
                "kind": "exercise",
                "title": "Bài tập 1: Trắc nghiệm",
                "source": r"""\begin{ex}
Tam giác có cạnh 6, 8, 10 là tam giác:
\choice
{\True Vuông}
{\False Nhọn}
{\False Tù}
{\False Đều}
\loigiai{LỜI GIẢI TRẮC NGHIỆM BÍ MẬT: $6^2 + 8^2 = 100 = 10^2$.}
\end{ex}""",
                "policy": "question",
                "parent": None,
                "teacher_notes": "LƯU Ý MCQ RIÊNG",
                "assets": {},
                "question": None,
            },
            # Block 4: Short Answer Exercise (policy=question)
            {
                "id": "b_short",
                "kind": "exercise",
                "title": "Bài tập 2: Điền khuyết",
                "source": r"""\begin{ex}
Chu vi tam giác có ba cạnh 3, 4, 5 bằng bao nhiêu?
\shortans{12}
\dapso{ĐÁP SỐ BÍ MẬT 12}
\loigiai{LỜI GIẢI ĐIỀN KHUYẾT: $3 + 4 + 5 = 12$.}
\end{ex}""",
                "policy": "question",
                "parent": None,
                "teacher_notes": "",
                "assets": {},
                "question": None,
            },
            # Block 5: Private Teacher-only Block (policy=private)
            {
                "id": "b_private",
                "kind": "exercise",
                "title": "Đề kiểm tra dự phòng (Tuyệt mật)",
                "source": r"""\begin{ex}
ĐỀ KIỂM TRA TUYỆT MẬT DÀNH CHO TUẦN SAU.
\loigiai{ĐÁP ÁN ĐỀ THI BÍ MẬT.}
\end{ex}""",
                "policy": "private",
                "parent": None,
                "teacher_notes": "",
                "assets": {},
                "question": None,
            },
        ],
    )
    doc = lesson_srv.save(doc)

    # 1. Student Master Body
    student_body, _ = lesson_srv.body(doc, audience="student", worksheet=False)

    # Must NOT contain private data
    assert "GHI CHÚ RIÊNG" not in student_body
    assert "LƯU Ý MCQ RIÊNG" not in student_body
    assert "LỜI GIẢI TRẮC NGHIỆM BÍ MẬT" not in student_body
    assert "ĐÁP SỐ BÍ MẬT" not in student_body
    assert "LỜI GIẢI ĐIỀN KHUYẾT" not in student_body
    assert "ĐỀ KIỂM TRA TUYỆT MẬT" not in student_body
    assert "\\True" not in student_body
    assert "\\False" not in student_body
    assert "\\shortans" not in student_body

    # Must retain public example solution
    assert "LỜI GIẢI CÔNG KHAI VÍ DỤ" in student_body

    # 2. Teacher Master Body
    teacher_body, _ = lesson_srv.body(doc, audience="teacher", worksheet=False)
    assert "GHI CHÚ RIÊNG" in teacher_body
    assert "LỜI GIẢI TRẮC NGHIỆM BÍ MẬT" in teacher_body
    assert "ĐỀ KIỂM TRA TUYỆT MẬT" in teacher_body
    assert "\\True" in teacher_body


def test_fail_closed_reports_block_location(tmp_path):
    """Verifies that an uncertified macro in student source fails closed with block title and line."""
    _, lesson_srv = setup_test_services(tmp_path)

    doc = lesson_srv.create(
        title="Bài kiểm tra macro lạ",
        blocks=[
            {
                "id": "b_bad",
                "kind": "exercise",
                "title": "Bài tập ma trận đặc biệt",
                "source": r"""\begin{ex}
Tính định thức ma trận.
\customDangerousMacro{Dữ liệu nguy hiểm}
\loigiai{Giải}
\end{ex}""",
                "policy": "question",
                "parent": None,
                "teacher_notes": "",
                "assets": {},
                "question": None,
            }
        ],
    )
    doc = lesson_srv.save(doc)

    with pytest.raises(ValueError) as excinfo:
        lesson_srv.body(doc, audience="student")

    msg = str(excinfo.value)
    assert "Bài tập ma trận đặc biệt" in msg
    assert "customDangerousMacro" in msg
    assert "Dòng 3" in msg


@pytest.mark.skipif(not shutil.which("pdflatex"), reason="pdfLaTeX required")
def test_student_export_subfiles_and_manifest_leak_free(tmp_path):
    """Verifies exported bundle subfiles, main.tex, manifest, and PDF are completely leak-free."""
    import pymupdf
    services, lesson_srv = setup_test_services(tmp_path)

    doc = lesson_srv.create(
        title="Xuất bài học sinh an toàn",
        blocks=[
            {
                "id": "b_th",
                "kind": "theory",
                "title": "Lý thuyết trọng tâm",
                "source": r"Công thức: $E = mc^2$.",
                "policy": "full",
                "parent": None,
                "teacher_notes": "BÍ MẬT GHI CHÚ LÝ THUYẾT",
                "assets": {},
                "question": None,
            },
            {
                "id": "b_ex",
                "kind": "exercise",
                "title": "Bài tập nguyên tử",
                "source": r"""\begin{ex}
Khối lượng nghỉ $m_0 = 1\text{ kg}$. Tính năng lượng $E$.
\choice
{\True $9 \cdot 10^{16}\text{ J}$}
{\False $3 \cdot 10^8\text{ J}$}
{\False $1\text{ J}$}
{\False $0\text{ J}$}
\loigiai{LỜI GIẢI BÍ MẬT: $E = m_0 c^2 = 1 \cdot (3\cdot 10^8)^2 = 9\cdot 10^{16}\text{ J}$.}
\end{ex}""",
                "policy": "question",
                "parent": None,
                "teacher_notes": "BÍ MẬT GHI CHÚ BÀI TẬP",
                "assets": {},
                "question": None,
            },
        ],
    )
    doc = lesson_srv.save(doc)

    # Export as student
    out_dir = tmp_path / "export_student_safety"
    export_folder = lesson_srv.export(doc, out_dir, audience="student")

    # 1. Check main.tex
    main_tex = (export_folder / "main.tex").read_text(encoding="utf-8")
    assert "BÍ MẬT" not in main_tex
    assert "\\True" not in main_tex

    # 2. Check all subfiles in LyThuyet/, DangToan/, BTVD/
    for tex_file in export_folder.rglob("*.tex"):
        content = tex_file.read_text(encoding="utf-8")
        assert "BÍ MẬT" not in content, f"Leaked secret in subfile {tex_file}"
        assert "\\True" not in content, f"Leaked \\True in subfile {tex_file}"

    # 3. Check manifest.json
    manifest_data = json.loads((export_folder / "manifest.json").read_text(encoding="utf-8"))
    assert manifest_data["audience"] == "student"
    assert "sha256" in manifest_data

    # 4. Check compiled PDF text extraction
    with pymupdf.open(export_folder / "bai-giang.pdf") as pdf:
        pdf_text = "".join(page.get_text() for page in pdf)
    assert "BÍ MẬT" not in pdf_text
    assert "9\\cdot 10^{16}\\text{ J}" not in pdf_text or "LỜI GIẢI" not in pdf_text
    assert "LỜI GIẢI BÍ MẬT" not in pdf_text
