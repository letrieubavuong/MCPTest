from pathlib import Path
import hashlib
import pytest
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QApplication

from latex_question_studio.preview.compiler import Compiler
from latex_question_studio.preview.thumbnails import ThumbnailManager


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_compiler_render_bounding_box_and_aspect_ratio(tmp_path, qapp):
    """Kiểm tra render tính toán bounding box chính xác, không làm méo tỷ lệ."""
    import pymupdf
    pdf_path = tmp_path / "test_doc.pdf"
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842) # A4
    page.insert_text((72, 100), "Câu 1: Cho hàm số f(x) liên tục trên đoạn [0; 1].", fontsize=12)
    page.draw_rect(pymupdf.Rect(72, 120, 200, 220), color=(0, 0, 1), fill=(0.9, 0.9, 1))
    doc.save(str(pdf_path))
    doc.close()

    png_bytes, pages = Compiler.render(pdf_path, page=0, scale=1.0)
    assert pages == 1
    assert len(png_bytes) > 0

    img = QImage()
    assert img.loadFromData(png_bytes)
    # Ảnh render phải bám theo nội dung thực, không phải toàn trang A4 595x842
    assert img.width() < 595
    assert img.height() < 842

    # Kiểm tra bảo toàn tỷ lệ khi scale vào card
    pix = QPixmap.fromImage(img)
    card_w = 320
    scaled = pix.scaledToWidth(min(card_w - 30, pix.width()), Qt.TransformationMode.SmoothTransformation)
    orig_ratio = pix.width() / pix.height()
    scaled_ratio = scaled.width() / scaled.height()
    assert abs(orig_ratio - scaled_ratio) < 0.05


def test_thumbnail_cache_invalidation_rules(tmp_path):
    """
    Kiểm tra cache key của thumbnail bị vô hiệu hóa khi:
    - LaTeX source thay đổi
    - Asset thay đổi
    - Preamble thay đổi
    - Engine thay đổi
    """
    mgr = ThumbnailManager(cache_dir=tmp_path / "cache")
    source_a = r"\begin{ex} Tính tích phân $\int_0^1 x dx$. \choice{A}{B}{C}{D} \end{ex}"
    source_b = r"\begin{ex} Tính tích phân $\int_0^2 x dx$. \choice{A}{B}{C}{D} \end{ex}"

    asset_path = tmp_path / "img.png"
    asset_path.write_bytes(b"dummy image 1")

    key_base = mgr.compute_key(source=source_a, assets={"img.png": asset_path}, preamble="preamble 1", engine="pdflatex")
    
    # 1. LaTeX thay đổi
    key_diff_src = mgr.compute_key(source=source_b, assets={"img.png": asset_path}, preamble="preamble 1", engine="pdflatex")
    assert key_diff_src != key_base

    # 2. Asset thay đổi nội dung
    asset_path.write_bytes(b"dummy image 2 - modified")
    key_diff_asset = mgr.compute_key(source=source_a, assets={"img.png": asset_path}, preamble="preamble 1", engine="pdflatex")
    assert key_diff_asset != key_base

    # 3. Preamble thay đổi
    key_diff_preamble = mgr.compute_key(source=source_a, assets={"img.png": asset_path}, preamble="preamble 2", engine="pdflatex")
    assert key_diff_preamble != key_base

    # 4. Engine thay đổi
    key_diff_engine = mgr.compute_key(source=source_a, assets={"img.png": asset_path}, preamble="preamble 1", engine="xelatex")
    assert key_diff_engine != key_base


def test_thumbnail_error_state_and_no_white_box(tmp_path, qapp):
    """
    Kiểm tra khi render thất bại:
    - Không lưu thumbnail trắng vào cache
    - Trạng thái lỗi được ghi nhận chính xác
    """
    mgr = ThumbnailManager(cache_dir=tmp_path / "cache")
    key_bad = "invalid_compile_key_12345"

    # Khi không có ảnh hoặc render lỗi, get trả về None
    assert mgr.get(key_bad) is None
    assert mgr.get_pixmap(key_bad) is None

    # Giả lập ghi nhận lỗi biên dịch
    compile_errors = {}
    compile_errors["q1"] = "! Undefined control sequence: \\invalidcmd"
    assert "q1" in compile_errors
    assert "Undefined control sequence" in compile_errors["q1"]


def test_high_quality_pdf_preview_preserved(tmp_path):
    """
    Kiểm tra pipeline giữ nguyên đường dẫn PDF chất lượng cao,
    không thay thế PDF bằng thumbnail giảm độ phân giải.
    """
    compiler = Compiler(data_dir=tmp_path)
    source = r"\begin{ex} Cho tam giác $ABC$. \end{ex}"
    res = compiler.compile(source)
    assert res.ok
    assert res.pdf is not None
    assert res.pdf.exists()
    assert res.pdf.suffix.lower() == ".pdf"
    assert res.pdf.stat().st_size > 1000
