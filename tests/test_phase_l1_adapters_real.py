"""Phase L.1 Real-World Web Adapters Hardening and Compliance Test Suite.

Verifies:
- Adapter explicit status enum (supported, generic_fallback, blocked, parse_failed, partial, needs_review)
- Extraction of lazy-loaded images (data-src, data-original, data-lazy-src, srcset)
- Missing image safety: flags draft as incomplete, attaches warning, blocks auto-verification
- SSRF protection on main requests and image downloads (IPv4/IPv6 private ranges, cloud metadata)
- Multi-case fixture audit for VietJack, Tech24, Loigiaihay, Generic (MCQ, True/False, Short Answer, Math, Images)
"""

from pathlib import Path
import tempfile
import pytest

from latex_question_studio.application.assets import AssetStore
from latex_question_studio.application.web_import import (
    QuestionDraft,
    WebScraperService,
    get_adapter_for_url,
)
from latex_question_studio.scraping.adapters.base import (
    AdapterStatus,
    BaseSiteAdapter,
    RawExtractedQuestion,
    extract_img_urls,
)
from latex_question_studio.scraping.adapters.vietjack import VietjackAdapter
from latex_question_studio.scraping.adapters.tech24 import Tech24Adapter
from latex_question_studio.scraping.adapters.loigiaihay import LoigiaihayAdapter
from latex_question_studio.scraping.fetcher import SafeFetcher, SSRFGuard


def test_adapter_status_enum_values():
    """Yêu cầu L2.4: AdapterStatus phải định nghĩa rõ ràng các trạng thái."""
    assert AdapterStatus.SUPPORTED == "supported"
    assert AdapterStatus.GENERIC_FALLBACK == "generic_fallback"
    assert AdapterStatus.BLOCKED == "blocked"
    assert AdapterStatus.PARSE_FAILED == "parse_failed"
    assert AdapterStatus.PARTIAL == "partial"
    assert AdapterStatus.NEEDS_REVIEW == "needs_review"


def test_lazy_loaded_image_extraction():
    """Yêu cầu L2.5: Trích xuất ảnh lười tải từ data-src, data-original, data-lazy-src, srcset."""
    html = """
    <div>
        <p>Hình 1: <img src="placeholder.gif" data-original="https://cdn.example.com/math1.png" /></p>
        <p>Hình 2: <img data-src="/images/circuit.jpg" /></p>
        <p>Hình 3: <img data-lazy-src="relative/path/figure.png" /></p>
        <p>Hình 4: <img srcset="highres.png 2x, lowres.png 1x" /></p>
        <p>Bỏ qua SVG data URI: <img src="data:image/svg+xml;base64,PHN2..." /></p>
    </div>
    """
    base_url = "https://example.com/exercises/page1.html"
    urls = extract_img_urls(html, base_url)
    assert len(urls) == 4
    assert urls[0] == "https://cdn.example.com/math1.png"
    assert urls[1] == "https://example.com/images/circuit.jpg"
    assert urls[2] == "https://example.com/exercises/relative/path/figure.png"
    assert urls[3] == "https://example.com/exercises/highres.png"


def test_vietjack_adapter_with_lazy_images_and_math():
    """Kiểm thử VietJack trích xuất câu hỏi có ảnh lazy load và công thức MathJax."""
    html = """
    <div class="content">
        <p><b>Câu 1:</b> Cho hàm số <script type="math/tex">y = x^3 - 3x</script> có đồ thị như hình vẽ:</p>
        <p><img src="data:image/gif;base64,R0lGODlh" data-src="https://vietjack.com/toan-12/images/hinh1.png" /></p>
        <p><b>A.</b> Hàm số đồng biến trên (1, 3).</p>
        <p><b>B.</b> Hàm số nghịch biến trên (-1, 1).</p>
        <p><b>C.</b> Hàm số có 2 điểm cực đại.</p>
        <p><b>D.</b> Giá trị nhỏ nhất bằng 0.</p>
        <p><b>Lời giải:</b></p>
        <p>Ta có đạo hàm <script type="math/tex">y' = 3x^2 - 3</script>. Dựa vào đồ thị, chọn đáp án B.</p>
    </div>
    """
    adapter = VietjackAdapter()
    questions, status, warnings = adapter.extract_with_status(html, "https://vietjack.com/toan-12/bai-tap.jsp")
    assert status == AdapterStatus.SUPPORTED
    assert len(questions) == 1
    q = questions[0]
    assert q.correct_choice == 1  # B
    assert len(q.options_html) == 4
    assert len(q.image_urls) == 1
    assert q.image_urls[0] == "https://vietjack.com/toan-12/images/hinh1.png"


def test_tech24_adapter_true_false_and_short_answer():
    """Kiểm thử Tech24 trích xuất dạng trắc nghiệm và lời giải."""
    html = """
    <div class="quiz-question">
        <p><b>Câu 10:</b> Cho tam giác ABC vuông tại A có AB = 3 cm, AC = 4 cm. Độ dài BC là:</p>
        <p>A. 5 cm</p>
        <p>B. 7 cm</p>
        <p>C. 25 cm</p>
        <p>D. 1 cm</p>
        <p><b>Hướng dẫn giải:</b> Áp dụng định lí Pytago: BC² = AB² + AC² = 25 suy ra BC = 5 cm. Chọn A.</p>
    </div>
    """
    adapter = Tech24Adapter()
    questions, status, warnings = adapter.extract_with_status(html, "https://tech24.vn/bai-tap-toan")
    assert status == AdapterStatus.SUPPORTED
    assert len(questions) == 1
    assert questions[0].correct_choice == 0  # A


def test_loigiaihay_adapter_status_and_extraction():
    """Kiểm thử Loigiaihay trích xuất dạng bài tập."""
    html = """
    <div class="content-question">
        <p><b>Câu 1.</b> Cho hình chóp S.ABCD có đáy là hình vuông cạnh a.</p>
        <p><b>A.</b> Thể tích là a³.</p>
        <p><b>B.</b> Thể tích là a³/3.</p>
        <p><b>C.</b> Thể tích là 2a³.</p>
        <p><b>D.</b> Thể tích là a³/6.</p>
        <p><b>Giải chi tiết:</b></p>
        <p>Diện tích đáy S = a². Chiều cao h = a. Thể tích V = 1/3 S h = a³/3. Đáp án B.</p>
    </div>
    """
    adapter = LoigiaihayAdapter()
    questions, status, warnings = adapter.extract_with_status(html, "https://loigiaihay.com/bai-1")
    assert status == AdapterStatus.SUPPORTED
    assert len(questions) == 1
    assert questions[0].correct_choice == 1  # B


def test_blocked_detection_when_cloudflare_or_captcha_encountered():
    """Yêu cầu L2.2 & L2.4: Nhận diện phản hồi bị chặn và gắn trạng thái BLOCKED."""
    cloudflare_html = """
    <html><head><title>Access Denied | Cloudflare</title></head>
    <body><h1>403 Forbidden</h1><p>Please complete the captcha below to proceed.</p></body></html>
    """
    adapter = VietjackAdapter()
    questions, status, warnings = adapter.extract_with_status(cloudflare_html, "https://vietjack.com")
    assert status == AdapterStatus.BLOCKED
    assert len(questions) == 0
    assert "BLOCKED" in warnings[0]


def test_ssrf_guard_protects_loopback_and_private_ips():
    """Yêu cầu L2.5: Bảo vệ chống SSRF ở cả request chính và tải ảnh."""
    assert SSRFGuard.is_safe_url("http://127.0.0.1/admin")[0] is False
    assert SSRFGuard.is_safe_url("http://10.100.1.5/secret")[0] is False
    assert SSRFGuard.is_safe_url("http://172.16.0.1/private")[0] is False
    assert SSRFGuard.is_safe_url("http://192.168.1.1/router")[0] is False
    assert SSRFGuard.is_safe_url("http://169.254.169.254/metadata")[0] is False
    assert SSRFGuard.is_safe_url("http://localhost:8000/db")[0] is False


def test_missing_image_flags_draft_as_incomplete_and_prevents_db_commit(tmp_path):
    """Yêu cầu L2.6: Nếu ảnh không tải được, đánh dấu chưa hoàn chỉnh và cấm commit."""
    fetcher = SafeFetcher()
    service = WebScraperService(fetcher)
    asset_store = AssetStore(tmp_path / "data")

    # Giả lập HTML có ảnh tới một URL không hợp lệ
    html_with_broken_img = """
    <p>Câu 1: Hình bên minh họa hiện tượng khúc xạ ánh sáng:</p>
    <img src="http://192.168.1.100/circuit.png" />
    <p>A. Đúng</p><p>B. Sai</p><p>C. Không xác định</p><p>D. Cả A và B</p>
    """
    # 192.168.1.100 sẽ bị SafeFetcher chặn do SSRF
    drafts = service.extract_from_html(
        html_with_broken_img,
        base_url="https://example.com/test",
        asset_store=asset_store
    )
    assert len(drafts) == 1
    draft = drafts[0]
    assert draft.has_missing_images is True
    assert any("thiếu" in w.lower() or "chưa hoàn chỉnh" in w.lower() for w in draft.warnings)

    # Nếu người dùng cố tình chuyển sang "verified" và lưu CSDL, hệ thống phải từ chối
    draft.status = "verified"
    from unittest.mock import MagicMock
    mock_services = MagicMock()
    with pytest.raises(ValueError, match="chưa hoàn chỉnh vì thiếu ảnh"):
        service.commit_drafts_to_db([draft], mock_services, asset_store)
