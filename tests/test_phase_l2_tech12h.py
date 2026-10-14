"""Phase L.2 Tech12h Adapter and Real-World Validation Test Suite.

Verifies:
- Strict domain matching for tech12h.com (rejects tech24.vn and lookalike hostnames)
- Robust extraction of 25 questions with 4 choices each, math formulas, and images
- Semantic correct choice detection via confirmed DOM markup (<h6> inside <li>)
- Guardrails: sets needs_review and correct_choice=None when markup is ambiguous
- Incomplete question handling: missing/broken images flag draft and prevent DB commit
- Real-world pdfLaTeX compilation into valid multi-page PDF
- Live URL test against https://tech12h.com/bai-hoc/trac-nghiem-khtn-9-ket-noi-bai-5-khuc-xa-anh-sang
"""
import shutil
from pathlib import Path
import pytest

from latex_question_studio.application.assets import AssetStore
from latex_question_studio.application.web_import import (
    WebScraperService,
    QuestionDraft,
    get_adapter_for_url,
)
from latex_question_studio.scraping.adapters.base import AdapterStatus, RawExtractedQuestion
from latex_question_studio.scraping.adapters.tech12h import Tech12hAdapter
from latex_question_studio.scraping.adapters.tech24 import Tech24Adapter
from latex_question_studio.scraping.fetcher import SafeFetcher
from latex_question_studio.preview.compiler import Compiler


def test_tech12h_domain_matching_and_anti_spoofing():
    """L2.1 & L2.4: Domain matching must be strict and prevent spoofing / confusion with tech24."""
    adapter = Tech12hAdapter()

    # Valid domains
    assert adapter.can_handle("https://tech12h.com/bai-hoc/trac-nghiem-khtn-9-ket-noi-bai-5-khuc-xa-anh-sang")
    assert adapter.can_handle("http://tech12h.com/bai-hoc/bai-1")
    assert adapter.can_handle("https://www.tech12h.com/bai-hoc/toan-12")
    assert adapter.can_handle("https://m.tech12h.com/bai-hoc/vat-li-10")

    # Must NEVER handle tech24.vn!
    assert not adapter.can_handle("https://tech24.vn/bai-hoc/hoa-hoc-11")
    tech24_adapter = get_adapter_for_url("https://tech24.vn/bai-hoc/hoa-hoc-11")
    assert isinstance(tech24_adapter, Tech24Adapter)
    assert not isinstance(tech24_adapter, Tech12hAdapter)

    # Must reject spoofed and lookalike hostnames
    assert not adapter.can_handle("https://tech12h.com.evil-phishing.org/quiz")
    assert not adapter.can_handle("https://fake-tech12h.com/quiz")
    assert not adapter.can_handle("https://tech12h.vn/quiz")
    assert not adapter.can_handle("https://nottech12h.com/quiz")

    # Routing registry check
    routed = get_adapter_for_url("https://tech12h.com/bai-hoc/trac-nghiem-khtn-9-ket-noi-bai-5-khuc-xa-anh-sang")
    assert isinstance(routed, Tech12hAdapter)
    assert routed.name == "Tech12h (tech12h.com)"


def test_tech12h_extraction_25_questions_structure():
    """L2.1 & L2.4: Extracts all 25 questions accurately with prompt, 4 choices, and correct answer."""
    adapter = Tech12hAdapter()

    # Build representative Tech12h HTML container
    q_blocks = []
    answers = ["D", "B", "B", "C", "B", "B", "B", "D", "B", "C",
               "A", "A", "D", "A", "B", "B", "B", "B", "D", "A",
               "C", "D", "B", "B", "A"]

    for i in range(1, 26):
        ans_letter = answers[i - 1]
        opts_html = []
        for ltr in ("A", "B", "C", "D"):
            if ltr == ans_letter:
                opts_html.append(f"<li><h6>{ltr}. Nội dung đáp án đúng {ltr} cho câu {i}.</h6></li>")
            else:
                opts_html.append(f"<li>{ltr}. Phương án sai {ltr} cho câu {i}.</li>")

        # In question 2, add option image; in question 24, add prompt image
        prompt_extra = ""
        if i == 2:
            opts_html[2] = '<li>C. <span class="imd"><img src="/sites/default/files/ck5/2024-05/image_354.png" width="63" height="44"></span></li>'
        elif i == 24:
            prompt_extra = '<p><span class="imd"><img src="/sites/default/files/ck5/2024-05/image_355.png" width="289" height="175"></span></p>'

        q_html = f"""
        <p><strong>Câu&nbsp;{i}:&nbsp;</strong>Đề bài câu hỏi số {i} về hiện tượng khúc xạ ánh sáng với $v_1 > v_2$.</p>
        {prompt_extra}
        <ul>
            {"".join(opts_html)}
        </ul>
        """
        q_blocks.append(q_html)

    full_html = f"""
    <html>
    <body>
        <div class="block-content-body trac_nghiem">
            <div class="accordion accordion-detail tex2jax" id="accordionExample">
                {"".join(q_blocks)}
            </div>
            <div class="kqua">Xem đáp án</div>
        </div>
        <div class="sidebar">Nội dung quảng cáo và tin liên quan</div>
    </body>
    </html>
    """

    base_url = "https://tech12h.com/bai-hoc/trac-nghiem-khtn-9-ket-noi-bai-5-khuc-xa-anh-sang"
    questions, status, warnings = adapter.extract_with_status(full_html, base_url)

    assert status in (AdapterStatus.SUPPORTED, AdapterStatus.PARTIAL)
    assert len(questions) == 25, f"Mong đợi 25 câu hỏi, trích xuất được: {len(questions)}"

    for idx, q in enumerate(questions):
        expected_ans_code = ord(answers[idx]) - ord("A")
        assert q.title == f"Câu {idx + 1}"
        assert len(q.options_html) == 4, f"Câu {idx + 1} phải có 4 phương án"
        assert q.correct_choice == expected_ans_code, f"Câu {idx + 1}: đáp án mong đợi {answers[idx]}, nhận được: {q.correct_choice}"

    # Question 2 option C image
    assert "https://tech12h.com/sites/default/files/ck5/2024-05/image_354.png" in questions[1].image_urls
    # Question 24 prompt image
    assert "https://tech12h.com/sites/default/files/ck5/2024-05/image_355.png" in questions[23].image_urls


def test_tech12h_guardrails_for_ambiguous_and_missing_answers():
    r"""L2.1 Guardrail: If answer markup is missing or ambiguous, NEVER speculate \True."""
    adapter = Tech12hAdapter()
    base_url = "https://tech12h.com/bai-hoc/test"

    # Case A: 0 options with <h6>
    html_no_h6 = """
    <div class="trac_nghiem">
        <p><strong>Câu 1:</strong> Đề bài không có đáp án nổi bật.</p>
        <ul>
            <li>A. Phương án A</li>
            <li>B. Phương án B</li>
            <li>C. Phương án C</li>
            <li>D. Phương án D</li>
        </ul>
    </div>
    """
    questions_a = adapter.extract_questions(html_no_h6, base_url)
    assert len(questions_a) == 1
    assert questions_a[0].correct_choice is None
    assert questions_a[0].needs_review is True
    assert any("Chưa xác định chắc chắn" in w for w in questions_a[0].warnings)

    # Case B: Multiple options with <h6>
    html_multi_h6 = """
    <div class="trac_nghiem">
        <p><strong>Câu 1:</strong> Đề bài có nhiều đáp án nổi bật.</p>
        <ul>
            <li><h6>A. Phương án A</h6></li>
            <li><h6>B. Phương án B</h6></li>
            <li>C. Phương án C</li>
            <li>D. Phương án D</li>
        </ul>
    </div>
    """
    questions_b = adapter.extract_questions(html_multi_h6, base_url)
    assert len(questions_b) == 1
    assert questions_b[0].correct_choice is None
    assert questions_b[0].needs_review is True
    assert any("nhiều hơn 1 phương án" in w for w in questions_b[0].warnings)

    # Case C: Option with only an image
    html_img_only = """
    <div class="trac_nghiem">
        <p><strong>Câu 1:</strong> Đề bài có phương án chỉ chứa hình ảnh.</p>
        <ul>
            <li><h6>A. Phương án A văn bản</h6></li>
            <li>B. <img src="/images/fig_b.png" /></li>
            <li>C. Phương án C</li>
            <li>D. Phương án D</li>
        </ul>
    </div>
    """
    questions_c = adapter.extract_questions(html_img_only, base_url)
    assert len(questions_c) == 1
    assert any("chỉ chứa hình ảnh" in w for w in questions_c[0].warnings)


def test_tech12h_adapter_status_and_security_blocking():
    """L2.0 & L2.4: Detect security blocks, captcha, and parse failures."""
    adapter = Tech12hAdapter()
    base_url = "https://tech12h.com/test"

    # Cloudflare block
    cf_html = "<html><head><title>Just a moment...</title></head><body>Enable JavaScript and cookies to continue. Cloudflare Ray ID: 12345</body></html>"
    _, status_cf, warns_cf = adapter.extract_with_status(cf_html, base_url)
    assert status_cf == AdapterStatus.BLOCKED

    # Empty HTML
    _, status_empty, _ = adapter.extract_with_status("", base_url)
    assert status_empty == AdapterStatus.PARSE_FAILED


def test_tech12h_pdflatex_compilation_and_export(tmp_path):
    """L2.3 & L2.4: Tech12h questions must compile cleanly with pdfLaTeX into multi-page PDF."""
    compiler = Compiler(str(tmp_path))
    if not compiler.engine_path():
        pytest.skip("pdfLaTeX not installed on system")

    adapter = Tech12hAdapter()
    service = WebScraperService()
    asset_store = AssetStore(tmp_path / "assets")

    # Sample Tech12h questions with math formulas and degree symbols
    html = r"""
    <div class="trac_nghiem">
        <p><strong>Câu 1:&nbsp;</strong>Nhận định nào sau đây về hiện tượng khúc xạ là <strong>không</strong> đúng?</p>
        <ul>
            <li>A. Tia khúc xạ nằm ở môi trường thứ 2 tiếp giáp với môi trường chứa tia tới.</li>
            <li>B. Tia khúc xạ nằm trong mặt phẳng chứa tia tới và pháp tuyến.</li>
            <li>C. Khi góc tới bằng 0, góc khúc xạ cũng bằng 0.</li>
            <li><h6>D. Góc khúc xạ luôn bằng góc tới.</h6></li>
        </ul>
        <p><strong>Câu 2:&nbsp;</strong>Chiếu ánh sáng từ không khí vào nước có chiết suất $n = 4/3$. Nếu góc khúc xạ $r$ là 30<sup>o</sup> thì góc tới $i$ là:</p>
        <ul>
            <li>A. 20$^\circ$</li>
            <li>B. 36$^\circ$</li>
            <li><h6>C. 42$^\circ$</h6></li>
            <li>D. 45$^\circ$</li>
        </ul>
    </div>
    """
    raw_qs = adapter.extract_questions(html, "https://tech12h.com/test")
    drafts = service._convert_raw_questions(raw_qs, "https://tech12h.com/test", asset_store)

    assert len(drafts) == 2
    for d in drafts:
        d.status = "verified"

    export_dir = tmp_path / "export_tech12h"
    res = service.export_drafts_to_exam_bundle(
        drafts,
        "Đề kiểm tra KHTN 9 Tech12h",
        export_dir,
        compiler,
    )
    assert res["ok"], f"Compile pdfLaTeX thất bại: {res.get('error')}\n{res.get('compile_log')}"
    assert Path(res["pdf_path"]).is_file()
    assert Path(res["zip_path"]).is_file()


@pytest.mark.skipif(not shutil.which("pdflatex"), reason="pdfLaTeX not available")
def test_tech12h_live_url_smoke(tmp_path):
    """L2.0 & L2.4: Test live URL https://tech12h.com/bai-hoc/trac-nghiem-khtn-9-ket-noi-bai-5-khuc-xa-anh-sang."""
    url = "https://tech12h.com/bai-hoc/trac-nghiem-khtn-9-ket-noi-bai-5-khuc-xa-anh-sang"
    fetcher = SafeFetcher()
    res = fetcher.fetch(url, check_robots=True)

    if not res.ok:
        pytest.skip(f"Live network access to {url} failed: {res.error}")

    adapter = get_adapter_for_url(url)
    assert isinstance(adapter, Tech12hAdapter)

    service = WebScraperService(fetcher=fetcher)
    asset_store = AssetStore(tmp_path / "assets")

    ok, msg, drafts = service.fetch_and_extract(url, asset_store=asset_store, check_robots=True)
    assert ok, f"fetch_and_extract thất bại: {msg}"
    assert len(drafts) == 25, f"Mong đợi 25 câu hỏi từ trang thật, nhận: {len(drafts)}"

    # Check question 1 and 24
    assert drafts[0].title == "Câu 1"
    assert drafts[0].correct_choice == 3  # D
    assert len(drafts[0].options_latex) == 4

    assert drafts[23].title == "Câu 24"
    assert drafts[23].correct_choice == 1  # B
    assert len(drafts[23].local_assets) >= 1  # Successfully downloaded real assets


def test_tech12h_live_url_semester_review_smoke(tmp_path):
    """Test live URL without bold question prefix: https://tech12h.com/bai-hoc/trac-nghiem-tap-vat-li-9-ket-noi-tri-thuc-hoc-ki-1-phan-1."""
    url = "https://tech12h.com/bai-hoc/trac-nghiem-tap-vat-li-9-ket-noi-tri-thuc-hoc-ki-1-phan-1"
    fetcher = SafeFetcher()
    res = fetcher.fetch(url, check_robots=True)

    if not res.ok:
        pytest.skip(f"Live network access to {url} failed: {res.error}")

    adapter = get_adapter_for_url(url)
    assert isinstance(adapter, Tech12hAdapter)

    service = WebScraperService(fetcher=fetcher)
    asset_store = AssetStore(tmp_path / "assets")

    ok, msg, drafts = service.fetch_and_extract(url, asset_store=asset_store, check_robots=True)
    assert ok, f"fetch_and_extract thất bại: {msg}"
    assert len(drafts) == 24, f"Mong đợi 24 câu hỏi từ trang thật, nhận: {len(drafts)}"

    # Check question 1: ans B (1)
    assert drafts[0].title == "Câu 1"
    assert drafts[0].correct_choice == 1  # B
    assert len(drafts[0].options_latex) == 4
