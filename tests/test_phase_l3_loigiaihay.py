"""Phase L.3 Loigiaihay Multi-layout Extraction & Exam Fidelity Test Suite.

Verifies:
- Strict domain matching for loigiaihay.com (rejects lookalike/spoofed hostnames)
- Layout detection: dispatches between SBTExerciseExtractor, ExamPaperExtractor, and GenericLoigiaihayExtractor
- SBT Layout fidelity: extracts 9 exercises (36.1 to 36.9), separates prompt from solution
- SBT 36.5 table preservation: preserves 7-statement True/False table intact as essay (no 4-item squeeze, no dropped rows)
- Exam Paper fidelity: Part I (16 MCQ), Part II (3 TF, 4 items each), Part III (3 Short Answer)
- Answer joining: eliminates question duplication from "Lời giải và đáp án"
- Semantic answer extraction: MCQ from 'Đáp án : [A-D]', TF from 'fa-square-check', Short Answer sub-items
- MathJax and Unicode safety: formula preservation, thin space U+2009 normalization
- Real pdfLaTeX compilation for both SBT and Exam bundles into valid PDFs
- Live URL smoke tests for SBT, Exam, and Tech12h regression
"""

import os
import shutil
import urllib.parse
from pathlib import Path
import pytest

from latex_question_studio.application.assets import AssetStore
from latex_question_studio.application.web_import import (
    WebScraperService,
    get_adapter_for_url,
)
from latex_question_studio.preview.compiler import Compiler
from latex_question_studio.scraping.adapters.base import AdapterStatus, RawExtractedQuestion
from latex_question_studio.scraping.adapters.loigiaihay import (
    ExamPaperExtractor,
    GenericLoigiaihayExtractor,
    LoigiaihayAdapter,
    SBTExerciseExtractor,
)
from latex_question_studio.scraping.fetcher import SafeFetcher
from latex_question_studio.scraping.html_to_latex import html_to_latex


def test_loigiaihay_domain_matching_and_anti_spoofing():
    """L3.1: Strict domain matching accepts loigiaihay.com and subdomains, rejects lookalike hostnames."""
    adapter = LoigiaihayAdapter()

    # Valid domains
    assert adapter.can_handle("https://loigiaihay.com/bai-tap-1.html")
    assert adapter.can_handle("http://loigiaihay.com/de-thi.html")
    assert adapter.can_handle("https://www.loigiaihay.com/de-thi.html")
    assert adapter.can_handle("https://m.loigiaihay.com/bai-tap.html")

    # Reject lookalikes and spoofing
    assert not adapter.can_handle("https://loigiaihay.com.attacker.com/fake")
    assert not adapter.can_handle("https://fake-loigiaihay.com/quiz")
    assert not adapter.can_handle("https://loigiaihay.vn/quiz")
    assert not adapter.can_handle("https://notloigiaihay.com/quiz")

    # Routing check
    routed = get_adapter_for_url("https://loigiaihay.com/giai-sbt-khtn-9.html")
    assert isinstance(routed, LoigiaihayAdapter)
    assert routed.name == "Lời Giải Hay (loigiaihay.com)"


def test_loigiaihay_extractor_dispatching():
    """L3.1: Dispatches to SBT, Exam, or Generic extractor based on content markers."""
    adapter = LoigiaihayAdapter()

    # 1. SBT content marker
    sbt_html = """
    <div class="content-box-unit">
        <div id="sub-question-1">
            <div class="font-bold">Bài 36.1</div>
            <div class="content-box-unit-detail">Đề bài 36.1</div>
        </div>
    </div>
    """
    sbt_qs = adapter.extract_questions(sbt_html, "https://loigiaihay.com/sbt")
    assert len(sbt_qs) == 1
    assert sbt_qs[0].metadata.get("source_section") == "SBT"

    # 2. Exam content marker
    exam_html = """
    <div class="exam-part-title">PHẦN I. Câu trắc nghiệm nhiều phương án lựa chọn</div>
    <div class="question">
        <p>Câu 1: Câu hỏi thi 1</p>
        <p>A. 1</p><p>B. 2</p><p>C. 3</p><p>D. 4</p>
    </div>
    """
    exam_qs = adapter.extract_questions(exam_html, "https://loigiaihay.com/exam")
    assert len(exam_qs) == 1
    assert exam_qs[0].metadata.get("source_section") == "Phần I"

    # 3. Generic fallback
    generic_html = """
    <div class="article-content">
        <p>Câu 1. Một câu hỏi thông thường.</p>
        <p>A. Đáp án 1</p><p>B. Đáp án 2</p><p>C. Đáp án 3</p><p>D. Đáp án 4</p>
        <p>Lời giải: Chọn A.</p>
    </div>
    """
    gen_qs = adapter.extract_questions(generic_html, "https://loigiaihay.com/article")
    assert len(gen_qs) == 1
    assert gen_qs[0].metadata.get("source_section") == "Generic"
    assert gen_qs[0].correct_choice == 0


def test_loigiaihay_sbt_extraction_fidelity():
    """L3.2: SBT layout extracts 9 exercises (36.1-36.9) and preserves 36.5 7-statement table intact."""
    sbt_file = Path("tests/fixtures/loigiaihay/sbt.html")
    if not sbt_file.is_file():
        sbt_file = Path("scratch_l3/sbt.html")
    if not sbt_file.is_file():
        pytest.skip("SBT snapshot not present")

    html = sbt_file.read_text(encoding="utf-8")
    adapter = LoigiaihayAdapter()
    url = "https://loigiaihay.com/giai-sbt-khoa-hoc-tu-nhien-9-bai-36-khai-quat-ve-di-truyen-hoc-trang-97-98-99-ket-noi-tri-thuc-a174817.html"
    questions = adapter.extract_questions(html, url)

    # 1. Exactly 9 exercises
    assert len(questions) == 9, f"Expected 9 SBT exercises, got {len(questions)}"

    # 2. Numbering sequence 36.1 to 36.9
    for i, q in enumerate(questions, 1):
        assert f"36.{i}" in q.title, f"Question index {i} title should contain 36.{i}, got {q.title}"
        assert q.metadata.get("source_url") == url
        assert q.metadata.get("dom_locator") == f"#sub-question-{i}"
        assert q.metadata.get("source_snapshot_hash")
        assert q.metadata.get("fetched_at")

    # 3. Exercise 36.5 table preservation: 7 statements, essay type, NO 4-item squeeze, NO dropped rows
    q_36_5 = questions[4]
    assert q_36_5.title == "Bài 36.5"
    assert q_36_5.question_type == "essay", "Bài 36.5 must be essay to preserve 7-statement table"
    assert q_36_5.metadata.get("has_table") is True
    assert "<table" in q_36_5.prompt_html
    # Count rows in the table
    row_count = q_36_5.prompt_html.count("<tr")
    assert row_count >= 8, f"Table must have at least 8 rows (1 header + 7 statements), found {row_count}"
    assert not q_36_5.choice_tf_answers, "Bài 36.5 must not be compressed into 4-item choice_tf"

    # 4. Prompt and solution separation
    for q in questions:
        assert q.prompt_html, f"{q.title} prompt must not be empty"
        assert q.solution_html, f"{q.title} solution must not be empty"
        assert "Phương pháp giải" in q.solution_html or "Lời giải" in q.solution_html


def test_loigiaihay_exam_extraction_fidelity_and_answer_joining():
    """L3.3: Exam layout extracts 22 questions (16 MCQ + 3 TF + 3 Short Answer) without duplicates."""
    exam_file = Path("tests/fixtures/loigiaihay/exam.html")
    if not exam_file.is_file():
        exam_file = Path("scratch_l3/exam.html")
    if not exam_file.is_file():
        pytest.skip("Exam snapshot not present")

    html = exam_file.read_text(encoding="utf-8")
    adapter = LoigiaihayAdapter()
    url = "https://loigiaihay.com/de-thi-giua-ki-1-khtn-9-ket-noi-tri-thuc-de-so-2-a173750.html"
    questions = adapter.extract_questions(html, url)

    # 1. Total 22 questions (16 + 3 + 3), ZERO duplication from solution section
    assert len(questions) == 22, f"Expected 22 total exam questions, got {len(questions)}"

    part1 = [q for q in questions if q.metadata.get("source_section") == "Phần I"]
    part2 = [q for q in questions if q.metadata.get("source_section") == "Phần II"]
    part3 = [q for q in questions if q.metadata.get("source_section") == "Phần III"]

    assert len(part1) == 16, f"Expected 16 MCQ in Part I, got {len(part1)}"
    assert len(part2) == 3, f"Expected 3 True/False in Part II, got {len(part2)}"
    assert len(part3) == 3, f"Expected 3 Short Answer in Part III, got {len(part3)}"

    # 2. Part I (16 MCQ): all have 4 choices and exact answers joined
    expected_p1_answers = [2, 0, 0, 0, 1, 2, 3, 1, 1, 0, 2, 3, 1, 2, 0, 0]
    for idx, q in enumerate(part1):
        assert q.question_type == "mcq"
        assert len(q.options_html) == 4, f"{q.title} must have 4 options"
        assert q.correct_choice == expected_p1_answers[idx], (
            f"{q.title}: expected answer {expected_p1_answers[idx]}, got {q.correct_choice}"
        )
        assert q.solution_html, f"{q.title} must have solution text joined"

    # 3. Part II (3 True/False): each has 4 statements and 4 boolean answers
    for q in part2:
        assert q.question_type == "true_false"
        assert len(q.options_html) == 4, f"{q.title} must have 4 statements"
        assert len(q.choice_tf_answers) == 4, f"{q.title} must have 4 TF answers"
        assert all(isinstance(val, bool) for val in q.choice_tf_answers), (
            f"{q.title} choice_tf_answers must all be booleans"
        )
        assert q.solution_html, f"{q.title} must have solution text joined"

    # Specific vector check for Part II Câu 1
    assert part2[0].choice_tf_answers == [True, False, False, True]

    # 4. Part III (3 Short Answer): retains sub-items a), b), c), d) and answers
    for q in part3:
        assert q.question_type == "short_answer"
        assert q.short_answer_text, f"{q.title} must have short answer text"
        assert "a)" in q.short_answer_text, f"{q.title} answer key must contain sub-item a)"
        assert q.solution_html, f"{q.title} must have solution text joined"


def test_loigiaihay_mathjax_and_unicode_thin_space_safety():
    """L3.4: Normalizes Unicode thin spaces (U+2009) and preserves MathJax delimiters."""
    # Test thin space normalization
    text_with_thin_space = "Đoạn mạch có điện trở 50\u2009\u03a9 hoạt động dưới hiệu điện thế 220\u2009V."
    latex_out, _ = html_to_latex(f"<p>{text_with_thin_space}</p>")
    assert "\u2009" not in latex_out
    assert "\\Omega" in latex_out

    # Test MathJax \( ... \) preservation without escaping subscripts
    math_html = "<p>Năng lượng của vật là \\(W = \\frac{1}{2}mv^2 + W_t\\).</p>"
    latex_math, _ = html_to_latex(math_html)
    assert "$W = \\frac{1}{2}mv^2 + W_t$" in latex_math
    assert "W\\_t" not in latex_math  # Underscore must NOT be escaped in math mode!


def test_loigiaihay_guardrails_for_ambiguous_answers():
    """L3.3: Sets needs_review and does NOT guess when answer markup is incomplete."""
    extractor = ExamPaperExtractor()
    url = "https://loigiaihay.com/exam-incomplete"

    # Incomplete exam with missing answer in solution
    html = """
    <div class="exam-part-title">PHẦN I. Câu trắc nghiệm nhiều phương án lựa chọn</div>
    <div class="question">
        <p>Câu 1: Đề bài không có đáp án giải.</p>
        <p>A. Lựa chọn 1</p><p>B. Lựa chọn 2</p><p>C. Lựa chọn 3</p><p>D. Lựa chọn 4</p>
    </div>
    <div class="font-bold">Lời giải và đáp án</div>
    <p>Không có phần giải cho câu 1.</p>
    """
    qs = extractor.extract(html, url)
    assert len(qs) == 1
    assert qs[0].correct_choice is None
    assert qs[0].needs_review is True
    assert any("Chưa trích xuất được đáp án đúng" in w for w in qs[0].warnings)


@pytest.mark.skipif(not shutil.which("pdflatex"), reason="pdfLaTeX not installed")
def test_loigiaihay_sbt_pdflatex_compilation(tmp_path):
    """L3.4: Compiles all 9 SBT exercises (including 36.5 table) into a valid multi-page PDF."""
    sbt_file = Path("tests/fixtures/loigiaihay/sbt.html")
    if not sbt_file.is_file():
        sbt_file = Path("scratch_l3/sbt.html")
    if not sbt_file.is_file():
        pytest.skip("SBT snapshot not present")

    compiler = Compiler(str(tmp_path))
    adapter = LoigiaihayAdapter()
    service = WebScraperService()
    asset_store = AssetStore(tmp_path / "assets")

    html = sbt_file.read_text(encoding="utf-8")
    url = "https://loigiaihay.com/giai-sbt-khtn-9-bai-36"
    raw_qs = adapter.extract_questions(html, url)
    drafts = service._convert_raw_questions(raw_qs, url, asset_store)

    assert len(drafts) == 9
    for d in drafts:
        d.status = "verified"

    export_dir = tmp_path / "sbt_export"
    res = service.export_drafts_to_exam_bundle(
        drafts,
        "SBT KHTN 9 Bài 36",
        export_dir,
        compiler,
    )
    assert res["ok"], f"SBT pdfLaTeX compilation failed: {res.get('error')}\n{res.get('compile_log')}"
    assert Path(res["pdf_path"]).is_file()
    assert Path(res["pdf_path"]).stat().st_size > 0


@pytest.mark.skipif(not shutil.which("pdflatex"), reason="pdfLaTeX not installed")
def test_loigiaihay_exam_pdflatex_compilation(tmp_path):
    """L3.4: Compiles 22 Exam questions (Part I, II, III) cleanly into a valid PDF."""
    exam_file = Path("tests/fixtures/loigiaihay/exam.html")
    if not exam_file.is_file():
        exam_file = Path("scratch_l3/exam.html")
    if not exam_file.is_file():
        pytest.skip("Exam snapshot not present")

    compiler = Compiler(str(tmp_path))
    adapter = LoigiaihayAdapter()
    service = WebScraperService()
    asset_store = AssetStore(tmp_path / "assets")

    html = exam_file.read_text(encoding="utf-8")
    url = "https://loigiaihay.com/de-thi-giua-ki-1-khtn-9"
    raw_qs = adapter.extract_questions(html, url)
    drafts = service._convert_raw_questions(raw_qs, url, asset_store)

    assert len(drafts) == 22
    for d in drafts:
        d.status = "verified"

    export_dir = tmp_path / "exam_export"
    res = service.export_drafts_to_exam_bundle(
        drafts,
        "Đề thi giữa kì 1 KHTN 9 Đề 2",
        export_dir,
        compiler,
    )
    assert res["ok"], f"Exam pdfLaTeX compilation failed: {res.get('error')}\n{res.get('compile_log')}"
    assert Path(res["pdf_path"]).is_file()
    assert Path(res["pdf_path"]).stat().st_size > 0


def test_loigiaihay_live_urls_smoke(tmp_path):
    """L3.0 & L3.6: Test live fetch and extraction against both Loigiaihay URLs and Tech12h regression."""
    fetcher = SafeFetcher()
    adapter = LoigiaihayAdapter()

    # 1. SBT live URL
    sbt_url = "https://loigiaihay.com/giai-sbt-khoa-hoc-tu-nhien-9-bai-36-khai-quat-ve-di-truyen-hoc-trang-97-98-99-ket-noi-tri-thuc-a174817.html"
    sbt_res = fetcher.fetch(sbt_url, check_robots=True)
    if not sbt_res.ok:
        pytest.skip(f"Live network access to {sbt_url} failed: {sbt_res.error}")

    assert sbt_res.status_code == 200
    sbt_html = sbt_res.content.decode("utf-8", errors="replace")
    sbt_qs = adapter.extract_questions(sbt_html, sbt_url)
    assert len(sbt_qs) == 9, f"Live SBT: expected 9 questions, got {len(sbt_qs)}"
    assert sbt_qs[4].metadata.get("has_table") is True

    # 2. Exam live URL
    exam_url = "https://loigiaihay.com/de-thi-giua-ki-1-khtn-9-ket-noi-tri-thuc-de-so-2-a173750.html"
    exam_res = fetcher.fetch(exam_url, check_robots=True)
    if not exam_res.ok:
        pytest.skip(f"Live network access to {exam_url} failed: {exam_res.error}")

    assert exam_res.status_code == 200
    exam_html = exam_res.content.decode("utf-8", errors="replace")
    exam_qs = adapter.extract_questions(exam_html, exam_url)
    assert len(exam_qs) == 22, f"Live Exam: expected 22 questions, got {len(exam_qs)}"

    # 3. Regression Tech12h live URL
    tech12h_url = "https://tech12h.com/bai-hoc/trac-nghiem-khtn-9-ket-noi-bai-5-khuc-xa-anh-sang"
    tech12h_res = fetcher.fetch(tech12h_url, check_robots=True)
    if tech12h_res.ok:
        tech12h_adapter = get_adapter_for_url(tech12h_url)
        tech12h_html = tech12h_res.content.decode("utf-8", errors="replace")
        tech12h_qs = tech12h_adapter.extract_questions(tech12h_html, tech12h_url)
        assert len(tech12h_qs) == 25, f"Live Tech12h regression: expected 25 questions, got {len(tech12h_qs)}"
