"""
Tests for unified bounding box calculation, padding, and page rendering (Phase J.2).
"""
import pytest
import pymupdf
from pathlib import Path
from latex_question_studio.preview.crop import calculate_bounding_box, render_page
from latex_question_studio.preview.compiler import Compiler
from latex_question_studio.preview.thumbnails import ThumbnailManager


def test_empty_page_fallback():
    """Trang rỗng không có chữ/hình thì bounding box fallback về page.rect an toàn."""
    doc = pymupdf.open()
    page = doc.new_page(width=400, height=300)
    bbox = calculate_bounding_box(page)
    assert bbox == page.rect
    assert bbox.width == 400
    assert bbox.height == 300
    doc.close()


def test_text_and_drawing_bounding_box_with_padding():
    """Kiểm tra bounding box kết hợp cả chữ và nét vẽ vector có padding bảo vệ."""
    doc = pymupdf.open()
    page = doc.new_page(width=500, height=500)
    
    # Thêm text tiếng Việt có dấu
    page.insert_text((50, 60), "Giải phương trình $\\sqrt{x^2 - 4} = 0$", fontsize=12)
    
    # Thêm hình vẽ vector (TikZ giả lập)
    shape = page.new_shape()
    shape.draw_rect(pymupdf.Rect(100, 100, 250, 200))
    shape.finish(color=(0, 0, 1), fill=(0.9, 0.9, 1))
    shape.commit()
    
    bbox = calculate_bounding_box(page, padding=(-14, -14, 14, 14))
    
    # Bbox phải bao phủ cả text và shape, và có lề an toàn
    assert bbox.x0 < 50
    assert bbox.y0 < 60
    assert bbox.x1 > 250
    assert bbox.y1 > 200
    
    # Không vượt quá biên trang
    assert bbox.x0 >= 0 and bbox.y0 >= 0
    assert bbox.x1 <= 500 and bbox.y1 <= 500
    doc.close()


def test_embedded_raster_image_bounding_box(tmp_path):
    """Kiểm tra bounding box nhận diện được ảnh raster nhúng qua get_image_info()."""
    doc = pymupdf.open()
    page = doc.new_page(width=600, height=600)
    
    # Tạo pixmap ảnh giả lập 100x100
    img_pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 100, 100), 0)
    img_pix.clear_with(0x80)
    img_rect = pymupdf.Rect(200, 250, 300, 350)
    page.insert_image(img_rect, pixmap=img_pix)
    
    bbox = calculate_bounding_box(page, padding=(-14, -14, 14, 14))
    assert bbox.x0 <= 200
    assert bbox.y0 <= 250
    assert bbox.x1 >= 300
    assert bbox.y1 >= 350
    doc.close()


def test_render_page_crop_vs_full(tmp_path):
    """So sánh chế độ crop=True (thumbnail) và crop=False (full page preview)."""
    doc = pymupdf.open()
    page = doc.new_page(width=500, height=800)
    page.insert_text((100, 100), "Nội dung câu hỏi nhỏ ở góc trên", fontsize=14)
    
    cropped_png = render_page(page, scale=1.0, crop=True)
    full_png = render_page(page, scale=1.0, crop=False)
    
    crop_pix = pymupdf.Pixmap(cropped_png)
    full_pix = pymupdf.Pixmap(full_png)
    
    # Thumbnail crop phải nhỏ hơn đáng kể so với full page 500x800
    assert crop_pix.width < full_pix.width or crop_pix.height < full_pix.height
    assert full_pix.width == 500 and full_pix.height == 800
    doc.close()


def test_multi_page_consistency(tmp_path):
    """Kiểm tra tài liệu nhiều trang: ThumbnailManager và Compiler thống nhất logic."""
    doc = pymupdf.open()
    p1 = doc.new_page(width=400, height=400)
    p1.insert_text((50, 50), "Trang 1: Đề bài", fontsize=12)
    p2 = doc.new_page(width=400, height=400)
    p2.insert_text((50, 50), "Trang 2: Lời giải dài tiếp theo", fontsize=12)
    
    pdf_path = tmp_path / "multi.pdf"
    doc.save(str(pdf_path))
    doc.close()
    
    # Render qua Compiler.render
    png_p1, total_pages = Compiler.render(pdf_path, page=0)
    assert total_pages == 2
    assert len(png_p1) > 100
    
    # Render qua ThumbnailManager.render_and_cache
    mgr = ThumbnailManager(tmp_path / "cache")
    res = mgr.render_and_cache(pdf_path, "test_key", page=0)
    assert res.format in ("webp", "png")
    assert res.file_path.exists()
