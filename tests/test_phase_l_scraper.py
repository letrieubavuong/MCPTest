"""Unit and integration tests for Phase L Web Scraping, Adapters, Staging, and Phase K Exam Export."""
from pathlib import Path
import pytest
import shutil
import tempfile

from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.assets import AssetStore
from latex_question_studio.application.services import create_services
from latex_question_studio.application.web_import import QuestionDraft, WebScraperService
from latex_question_studio.preview.compiler import Compiler
from latex_question_studio.scraping.adapters.generic import GenericArticleAdapter
from latex_question_studio.scraping.adapters.loigiaihay import LoigiaihayAdapter
from latex_question_studio.scraping.adapters.tech24 import Tech24Adapter
from latex_question_studio.scraping.adapters.vietjack import VietjackAdapter
from latex_question_studio.scraping.fetcher import SSRFGuard, RobotsPolicy
from latex_question_studio.scraping.html_to_latex import html_to_latex


# --- 1. SSRF GUARD & ROBOTS.TXT TESTS ---

def test_ssrf_guard_blocks_private_and_local_networks():
    blocked_urls = [
        "http://localhost:8080/admin",
        "http://127.0.0.1/secret",
        "http://10.0.0.1/internal",
        "http://172.16.0.1/keys",
        "http://192.168.1.1/router",
        "http://169.254.169.254/latest/meta-data/",
        "ftp://example.com/file.txt",
        "file:///etc/passwd",
    ]
    for url in blocked_urls:
        safe, err = SSRFGuard.is_safe_url(url)
        assert not safe, f"Expected {url} to be blocked by SSRFGuard, but got safe: {err}"


def test_html_to_latex_mathjax_and_katex():
    html = """
    <p>Cho hàm số <script type="math/tex">y = f(x)</script> có đạo hàm <script type="math/tex; mode=display">f'(x) = 3x^2 - 6x</script>.</p>
    <p>Giá trị <span class="katex"><annotation encoding="application/x-tex">x = 2</annotation></span> là điểm cực tiểu.</p>
    """
    latex, images = html_to_latex(html)
    assert "$y = f(x)$" in latex
    assert "\\[ f'(x) = 3x^2 - 6x \\]" in latex
    assert "$x = 2$" in latex
    assert images == []


def test_html_to_latex_mathml_and_formatting():
    html = """
    <p>Biểu thức: <math><mfrac><mi>x</mi><mn>2</mn></mfrac></math> với <b>x &gt; 0</b>.</p>
    <p>Ký hiệu: x ∈ ℝ và y ≥ 5.</p>
    """
    latex, _ = html_to_latex(html)
    assert r"\frac{x}{2}" in latex
    assert r"\textbf{x > 0}" in latex
    assert r"\in" in latex
    assert r"\ge" in latex


# --- 2. SITE ADAPTER TESTS (OFFLINE HTML FIXTURES) ---

def test_vietjack_adapter_offline_fixture():
    fixture = """
    <div class="content">
        <p><b>Câu 1:</b> Cho tập hợp <script type="math/tex">A = \{1; 2; 3\}</script>. Số phần tử của A là:</p>
        <p><b>A.</b> 1</p>
        <p><b>B.</b> 2</p>
        <p><b>C.</b> 3</p>
        <p><b>D.</b> 4</p>
        <p><b>Lời giải:</b></p>
        <p>Tập hợp A có 3 phần tử. Chọn <b>C.</b></p>
        <p><b>Câu 2:</b> Hàm số nào đồng biến trên R?</p>
        <p>A. y = 2x + 1</p>
        <p>B. y = -x</p>
        <p>C. y = x^2</p>
        <p>D. y = 1/x</p>
        <p><b>Đáp án: A</b></p>
    </div>
    """
    adapter = VietjackAdapter()
    assert adapter.can_handle("https://vietjack.com/toan-12/bai-tap.jsp")
    questions = adapter.extract_questions(fixture, "https://vietjack.com/toan-12/bai-tap.jsp")

    assert len(questions) == 2

    # Question 1
    q1 = questions[0]
    assert "A = \\{1; 2; 3\\}" in q1.prompt_html
    assert len(q1.options_html) == 4
    assert q1.options_html[0] == "1"
    assert q1.options_html[2] == "3"
    assert q1.correct_choice == 2  # C is index 2
    assert "Tập hợp A có 3 phần tử" in q1.solution_html
    assert q1.question_type == "mcq"

    # Question 2
    q2 = questions[1]
    assert "Hàm số nào đồng biến" in q2.prompt_html
    assert len(q2.options_html) == 4
    assert q2.correct_choice == 0  # A is index 0


def test_tech24_adapter_offline_fixture():
    fixture = """
    <div class="question-item">
        <p>Câu 1: Nghiệm của phương trình 2x - 4 = 0 là:</p>
        <div class="answer"><b>A.</b> x = 1</div>
        <div class="answer"><b>B.</b> x = 2</div>
        <div class="answer"><b>C.</b> x = 3</div>
        <div class="answer"><b>D.</b> x = 4</div>
        <div class="solution">Giải: 2x = 4 suy ra x = 2. Đáp án: B</div>
    </div>
    """
    adapter = Tech24Adapter()
    assert adapter.can_handle("https://tech24.vn/trac-nghiem-toan/")
    questions = adapter.extract_questions(fixture, "https://tech24.vn/trac-nghiem-toan/")

    assert len(questions) == 1
    q = questions[0]
    assert "Nghiệm của phương trình" in q.prompt_html
    assert len(q.options_html) == 4
    assert q.correct_choice == 1  # B is index 1
    assert "x = 2" in q.solution_html


def test_loigiaihay_adapter_offline_fixture():
    fixture = """
    <div class="box-content">
        <p><strong>Câu 1:</strong> Tính giá trị của biểu thức 5 + 3.</p>
        <p>A. 7</p>
        <p>B. 8</p>
        <p>C. 9</p>
        <p>D. 10</p>
        <div class="loi-giai">Ta có 5 + 3 = 8. Chọn B.</div>
    </div>
    """
    adapter = LoigiaihayAdapter()
    assert adapter.can_handle("https://loigiaihay.com/bai-tap-1.html")
    questions = adapter.extract_questions(fixture, "https://loigiaihay.com/bai-tap-1.html")

    assert len(questions) == 1
    q = questions[0]
    assert "5 + 3" in q.prompt_html
    assert len(q.options_html) == 4
    assert q.correct_choice == 1  # B
    assert "Ta có 5 + 3 = 8" in q.solution_html


def test_generic_adapter_true_false_and_short_answer():
    fixture_tf = """
    <p>Câu 1: Cho hàm số f(x) = x^3 - 3x. Các mệnh đề sau đúng hay sai?</p>
    <p>a) Đạo hàm f'(x) = 3x^2 - 3 (Đúng)</p>
    <p>b) Hàm số có 3 điểm cực trị (Sai)</p>
    <p>c) f(0) = 0 (Đúng)</p>
    <p>d) Đồ thị hàm số đi qua gốc tọa độ (Đúng)</p>
    """
    adapter = GenericArticleAdapter()
    q_list = adapter.extract_questions(fixture_tf, "http://test.local")
    assert len(q_list) == 1
    q = q_list[0]
    assert q.question_type == "true_false"
    assert len(q.options_html) == 4
    assert q.choice_tf_answers == [True, False, True, True]

    fixture_sa = """
    <p>Bài 2: Tính diện tích hình vuông có cạnh bằng 5 cm.</p>
    <p>Đáp số: 25</p>
    <p>Lời giải: Diện tích bằng 5 x 5 = 25 cm2.</p>
    """
    q_sa_list = adapter.extract_questions(fixture_sa, "http://test.local")
    assert len(q_sa_list) == 1
    q_sa = q_sa_list[0]
    assert q_sa.question_type == "short_answer"
    assert q_sa.short_answer_text == "25"


# --- 3. QUESTION DRAFT & EX_TEST SERIALIZATION ---

def test_question_draft_ex_test_serialization():
    # MCQ
    mcq_draft = QuestionDraft(
        id="q1",
        source_url="http://test.com",
        title="Câu 1",
        question_type="mcq",
        prompt_latex="Tìm $x$ biết $2x = 6$.",
        options_latex=["$x = 1$", "$x = 2$", "$x = 3$", "$x = 4$"],
        correct_choice=2,  # C
        solution_latex="$x = 6/2 = 3$."
    )
    tex = mcq_draft.to_ex_test_latex()
    assert "\\begin{ex}" in tex
    assert "Tìm $x$ biết $2x = 6$." in tex
    assert "\\choice" in tex
    assert "\\True $x = 3$" in tex
    assert "\\loigiai{$x = 6/2 = 3$.}" in tex
    assert "\\end{ex}" in tex

    # True/False
    tf_draft = QuestionDraft(
        id="q2",
        source_url="http://test.com",
        title="Câu 2",
        question_type="true_false",
        prompt_latex="Cho mệnh đề:",
        options_latex=["Mệnh đề 1", "Mệnh đề 2", "Mệnh đề 3", "Mệnh đề 4"],
        choice_tf_answers=[True, False, True, False],
        solution_latex="Giải thích chi tiết."
    )
    tf_tex = tf_draft.to_ex_test_latex()
    assert "\\choiceTF" in tf_tex
    assert "\\True Mệnh đề 1" in tf_tex
    assert "\\True Mệnh đề 3" in tf_tex
    assert "\\True Mệnh đề 2" not in tf_tex


# --- 4. MODERATION & SAFE DATABASE COMMIT ---

def test_database_commit_requires_explicit_verified_status(tmp_path):
    config = AppConfig(data_dir=tmp_path)
    services = create_services(config)
    asset_store = AssetStore(tmp_path)
    service = WebScraperService()

    draft_unverified = QuestionDraft(
        id="d1",
        source_url="http://example.com/q1",
        title="Câu chưa duyệt",
        question_type="mcq",
        prompt_latex="Nội dung câu 1",
        options_latex=["A", "B", "C", "D"],
        correct_choice=0,
        status="needs_review"  # NOT verified!
    )

    draft_rejected = QuestionDraft(
        id="d2",
        source_url="http://example.com/q2",
        title="Câu bị từ chối",
        question_type="mcq",
        prompt_latex="Nội dung câu 2",
        options_latex=["A", "B", "C", "D"],
        correct_choice=1,
        status="rejected"
    )

    # Attempt commit: MUST be refused!
    res = service.commit_drafts_to_db([draft_unverified, draft_rejected], services, asset_store)
    assert not res["ok"]
    assert res["committed_count"] == 0
    assert services.questions.count() == 0  # Database remains untouched!

    # Now verify draft 1
    draft_unverified.status = "verified"
    res2 = service.commit_drafts_to_db([draft_unverified, draft_rejected], services, asset_store)
    assert res2["ok"]
    assert res2["committed_count"] == 1
    assert services.questions.count() == 1

    saved = services.questions.list_page(10, 0)[0]
    assert "Nội dung câu 1" in saved.latex_source
    assert saved.question_type == "mcq"


# --- 5. PHASE K EXAM BUNDLE EXPORT & PDF COMPILER VALIDATION ---

def test_export_drafts_to_phase_k_exam_bundle(tmp_path):
    compiler = Compiler(str(tmp_path))
    if not compiler.engine_path():
        pytest.skip("pdfLaTeX not installed on system")

    service = WebScraperService()

    # Create verified drafts across all sections
    mcq = QuestionDraft(
        id="m1", source_url="http://web", title="Câu TN 1", question_type="mcq",
        prompt_latex="Phương trình bậc nhất $ax + b = 0$ có nghiệm duy nhất khi:",
        options_latex=["$a \\ne 0$", "$a = 0$", "$b \\ne 0$", "$b = 0$"],
        correct_choice=0, status="verified"
    )

    tf = QuestionDraft(
        id="tf1", source_url="http://web", title="Câu ĐS 1", question_type="true_false",
        prompt_latex="Cho hàm số bậc hai $y = x^2 - 4x + 3$. Xét tính đúng sai:",
        options_latex=["Đỉnh của parabol là $I(2; -1)$", "Đồ thị cắt trục hoành tại 2 điểm", "Hàm số nghịch biến trên $(2; +\\infty)$", "Giá trị nhỏ nhất là $-1$"],
        choice_tf_answers=[True, True, False, True], status="verified"
    )

    short_ans = QuestionDraft(
        id="sa1", source_url="http://web", title="Câu TLN 1", question_type="short_answer",
        prompt_latex="Tìm nghiệm nguyên dương của $x^2 - 9 = 0$.",
        short_answer_key="3", status="verified"
    )

    essay = QuestionDraft(
        id="es1", source_url="http://web", title="Câu TL 1", question_type="essay",
        prompt_latex="Giải phương trình $\\sqrt{x + 1} = 2$.",
        solution_latex="Bình phương hai vế ta được $x + 1 = 4 \\Leftrightarrow x = 3$.",
        status="verified"
    )

    export_dir = tmp_path / "exam_export"
    res = service.export_drafts_to_exam_bundle(
        [mcq, tf, short_ans, essay],
        "Đề kiểm tra giữa kỳ 1",
        export_dir,
        compiler
    )

    assert res["ok"], f"Export failed: {res.get('error')}\n{res.get('compile_log')}"
    assert Path(res["tex_path"]).is_file()
    assert Path(res["pdf_path"]).is_file()
    assert Path(res["zip_path"]).is_file()

    # Verify Phase K Structure in generated TeX
    tex_content = Path(res["tex_path"]).read_text(encoding="utf-8")
    assert r"\TieudeT{ĐỀ KIỂM TRA GIỮA KỲ 1}" in tex_content
    assert r"\PhanI" in tex_content
    assert r"\begin{cauhoiTN}{De01}" in tex_content
    assert r"\PhanII" in tex_content
    assert r"\begin{cauhoiDS}{De01}" in tex_content
    assert r"\PhanIII" in tex_content
    assert r"\begin{cauhoiTLN}{De01}" in tex_content
    assert r"\PhanTL" in tex_content
    assert r"\begin{cauhoiTL}{De01}" in tex_content


def test_export_never_reports_success_if_latex_fails_compilation(tmp_path):
    compiler = Compiler(str(tmp_path))
    service = WebScraperService()

    # Draft with intentionally broken syntax that cannot compile
    broken_draft = QuestionDraft(
        id="b1", source_url="http://web", title="Câu hỏng", question_type="essay",
        prompt_latex=r"Đây là lỗi \undefinedCommandThatFails12345 {",
        status="verified"
    )

    export_dir = tmp_path / "broken_export"
    res = service.export_drafts_to_exam_bundle(
        [broken_draft],
        "Đề thi lỗi",
        export_dir,
        compiler
    )

    # Non-negotiable requirement: DO NOT report export success if .tex does not compile!
    assert not res["ok"]
    assert res["pdf_path"] is None
    assert "Biên dịch pdfLaTeX thất bại" in res["error"]
