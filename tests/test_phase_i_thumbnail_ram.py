from pathlib import Path
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import QByteArray, QBuffer, QIODevice

from latex_question_studio.preview.thumbnails import ThumbnailManager


def _create_image_bytes(width: int, height: int, fmt: str = "PNG") -> bytes:
    img = QImage(width, height, QImage.Format.Format_RGB32)
    img.fill(0x336699)
    buf = QByteArray()
    buffer = QBuffer(buf)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buffer, fmt)
    return bytes(buf.data())


def test_decoded_pixmap_memory_accounting(qapp, tmp_path):
    cache_dir = tmp_path / "thumbnails"
    mgr = ThumbnailManager(cache_dir, ram_limit=64 * 1024 * 1024)

    # Image 400x300: decoded RGBA memory = 400 * 300 * 4 = 480,000 bytes
    width, height = 400, 300
    expected_decoded_bytes = width * height * 4
    raw_png = _create_image_bytes(width, height)
    compressed_bytes_len = len(raw_png)

    key = "test_item_1"
    disk_file, fmt = mgr.save(key, raw_png, prefer_webp=False)

    # 1. Before get_pixmap(): RAM cache stores only compressed bytes, no pixmap
    assert mgr.ram_count() == 1
    assert mgr.pixmap_count() == 0
    assert mgr.ram_usage() == compressed_bytes_len

    # 2. After get_pixmap(): decoded QPixmap is accounted for in RAM
    pix = mgr.get_pixmap(key)
    assert pix is not None and not pix.isNull()
    assert mgr.pixmap_count() == 1
    # RAM usage must include both compressed bytes and uncompressed pixel memory
    expected_total = compressed_bytes_len + expected_decoded_bytes
    assert mgr.ram_usage() == expected_total
    assert mgr.ram_usage() > 480_000


def test_pixmap_eviction_under_ram_pressure(qapp, tmp_path):
    cache_dir = tmp_path / "thumbnails"
    # Small RAM limit of 350 KB: fits only 1 decoded 250x250 image (~250 KB) + compressed headers
    mgr = ThumbnailManager(cache_dir, ram_limit=350 * 1024)

    w, h = 250, 250
    decoded_per_image = w * h * 4  # 250,000 bytes
    img_data = _create_image_bytes(w, h)

    # Save 3 items
    for i in range(1, 4):
        mgr.save(f"item_{i}", img_data, prefer_webp=False)

    # Access pixmaps sequentially
    pix1 = mgr.get_pixmap("item_1")
    assert mgr.pixmap_count() == 1
    assert mgr.ram_usage() >= decoded_per_image

    pix2 = mgr.get_pixmap("item_2")
    # Due to Tier-1 eviction, item_1's pixmap was freed (pix=None), retaining only compressed bytes
    # Thus item_2's pixmap fits within the 350 KB limit without exceeding it!
    assert mgr.ram_usage() <= 350 * 1024
    assert mgr.pixmap_count() == 1
    assert mgr._ram_cache["item_1"][3] is None  # item_1 pixmap was evicted
    assert mgr._ram_cache["item_2"][3] is not None  # item_2 pixmap is active

    # Now request item_1 pixmap again: should decode seamlessly on demand
    pix1_reloaded = mgr.get_pixmap("item_1")
    assert pix1_reloaded is not None and not pix1_reloaded.isNull()
    assert mgr.ram_usage() <= 350 * 1024
    assert mgr._ram_cache["item_1"][3] is not None
    assert mgr._ram_cache["item_2"][3] is None  # item_2 was now evicted


def test_large_and_consecutive_images_strict_lru(qapp, tmp_path):
    cache_dir = tmp_path / "thumbnails"
    # 2 MiB limit
    limit = 2 * 1024 * 1024
    mgr = ThumbnailManager(cache_dir, ram_limit=limit)

    # Create 20 consecutive large images: 600x600 decoded = 1.44 MB each
    w, h = 600, 600
    img_data = _create_image_bytes(w, h)

    for i in range(20):
        key = f"large_{i:02d}"
        mgr.save(key, img_data, prefer_webp=False)
        pix = mgr.get_pixmap(key)
        assert pix is not None
        # RAM usage must never exceed limit (allowing at most 1 item if single item > limit)
        assert mgr.ram_usage() <= limit + 50_000, f"RAM usage {mgr.ram_usage()} exceeded limit {limit}"

    # Verify disk cache is fully preserved for all 20 images
    for i in range(20):
        res = mgr.get(f"large_{i:02d}")
        assert res is not None
        assert res[2].is_file()


def test_clear_cache_preserves_user_assets(qapp, tmp_path):
    cache_dir = tmp_path / "cache" / "thumbnails"
    user_assets_dir = tmp_path / "user_assets"
    user_assets_dir.mkdir(parents=True, exist_ok=True)

    # Create user asset
    real_asset = user_assets_dir / "geometry_figure.png"
    real_asset.write_bytes(b"AUTHORITATIVE_USER_IMAGE_DATA")

    mgr = ThumbnailManager(cache_dir)
    img_bytes = _create_image_bytes(100, 100)
    for i in range(10):
        mgr.save(f"item_{i}", img_bytes)
        mgr.get_pixmap(f"item_{i}")

    assert mgr.ram_usage() > 0
    assert mgr.disk_usage() > 0

    # Clear thumbnail cache
    cleared = mgr.clear_cache()
    assert cleared == 10
    assert mgr.ram_usage() == 0
    assert mgr.disk_usage() == 0

    # User asset must be 100% untouched
    assert real_asset.is_file()
    assert real_asset.read_bytes() == b"AUTHORITATIVE_USER_IMAGE_DATA"
