"""
Unified PDF Bounding Box & Page Rendering for LaTeX Question Studio.
Single source of truth for cropping question thumbnails and full-page previews.
"""
from typing import Tuple, Optional
import pymupdf


def calculate_bounding_box(
    page: pymupdf.Page,
    padding: Tuple[float, float, float, float] = (-14.0, -14.0, 14.0, 14.0)
) -> pymupdf.Rect:
    """
    Computes a tight, content-aware bounding box for a PDF page, combining:
    1. Text block bounds (get_text('blocks'))
    2. Vector graphics & TikZ drawings (get_drawings())
    3. Raster images & graphics (get_image_info())
    
    Applies protective padding (-pad_left, -pad_top, pad_right, pad_bottom)
    to prevent clipping Vietnamese accents (Â, Ê, Ô, ư, ơ, dấu hỏi/ngã/nặng),
    TikZ arrowheads, sub/superscripts, and fractions.
    
    If the page contains no detected content elements, returns the full page rectangle.
    """
    rectangles = []

    # 1. Text blocks
    for block in page.get_text("blocks"):
        if len(block) >= 4:
            rectangles.append(pymupdf.Rect(block[:4]))

    # 2. Vector graphics & TikZ drawings
    for drawing in page.get_drawings():
        if "rect" in drawing:
            rectangles.append(drawing["rect"])

    # 3. Embedded raster images (PNG, JPG, etc.)
    for img in page.get_image_info():
        if "bbox" in img:
            rectangles.append(pymupdf.Rect(img["bbox"]))

    if not rectangles:
        return page.rect

    # Union of all content rectangles
    clip = None
    for r in rectangles:
        if r.is_valid and not r.is_empty:
            clip = r if clip is None else clip | r

    if clip is None or not clip.is_valid or clip.is_empty:
        return page.rect

    # Apply padding and constrain to page boundaries
    padded_clip = (clip + padding) & page.rect
    if padded_clip.is_valid and not padded_clip.is_empty:
        return padded_clip

    return clip & page.rect


def render_page(
    page: pymupdf.Page,
    scale: float = 1.5,
    crop: bool = True,
    padding: Tuple[float, float, float, float] = (-14.0, -14.0, 14.0, 14.0),
    format: str = "png"
) -> bytes:
    """
    Renders a PDF page to raw image bytes with consistent scaling and cropping.
    - If crop=True (question thumbnail mode): clips tightly around content with padding.
    - If crop=False (full page preview mode): renders the entire page without clipping.
    """
    matrix = pymupdf.Matrix(scale, scale)
    clip = calculate_bounding_box(page, padding=padding) if crop else None
    pixmap = page.get_pixmap(matrix=matrix, clip=clip)
    return pixmap.tobytes(format)
