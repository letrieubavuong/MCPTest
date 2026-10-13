from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import os
import shutil
import tempfile
import time
from typing import Tuple, Optional, Dict, Any

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QImage, QPixmap


@dataclass(frozen=True)
class ThumbnailResult:
    key: str
    file_path: Path
    format: str
    data: bytes
    cache_hit: bool = False


class ThumbnailManager:
    """
    Manages generation, storage, and caching of LaTeX question thumbnails.
    - Preserves pdfLaTeX as the authoritative source.
    - Stores thumbnails as standalone files on disk (never Base64 in SQLite).
    - Supports WebP with lossless/high-quality encoding and fallback to PNG.
    - Implements LRU memory (RAM limit, default 128 MiB) and disk quota (default 1 GiB).
    - Safe cache clearance without deleting original user assets.
    """

    def __init__(
        self,
        cache_dir: Path | str,
        disk_limit: int = 1024 * 1024 * 1024,  # 1 GiB
        ram_limit: int = 128 * 1024 * 1024,     # 128 MiB
    ):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.disk_limit = disk_limit
        self.ram_limit = ram_limit
        self._ram_cache: OrderedDict[str, Tuple[bytes, str, int, Optional[QPixmap]]] = OrderedDict()
        self._ram_usage: int = 0

    def compute_key(
        self,
        source: str,
        assets: Optional[Dict[str, Any]] = None,
        preamble: str = "",
        dependencies: Optional[Dict[str, str]] = None,
        engine: str = "pdflatex",
        render_options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Computes a deterministic SHA-256 cache key based on LaTeX source,
        asset hashes, preamble/profile, dependencies, engine, and rendering options.
        """
        assets = assets or {}
        dependencies = dependencies or {}
        render_options = render_options or {"scale": 1.2, "quality": 92}

        asset_hashes = {}
        for name, target in sorted(assets.items()):
            if isinstance(target, (bytes, bytearray)):
                asset_hashes[name] = hashlib.sha256(target).hexdigest()
            else:
                p = Path(target)
                if p.is_file():
                    asset_hashes[name] = hashlib.sha256(p.read_bytes()).hexdigest()
                else:
                    asset_hashes[name] = f"missing:{name}"

        payload = {
            "source": source,
            "preamble": preamble,
            "dependencies": dict(sorted(dependencies.items())),
            "assets": asset_hashes,
            "engine": engine,
            "render_options": dict(sorted(render_options.items())),
            "version": "v1-phase-f",
        }
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def get(self, key: str) -> Optional[Tuple[bytes, str, Path]]:
        """
        Retrieves thumbnail from RAM cache or disk.
        Returns (data, format, path) or None if missing.
        """
        # 1. Check RAM cache
        if key in self._ram_cache:
            data, fmt, size, pix = self._ram_cache[key]
            self._ram_cache.move_to_end(key)
            disk_file = self.cache_dir / f"{key}.{fmt}"
            return data, fmt, disk_file

        # 2. Check disk cache
        for fmt in ("webp", "png"):
            disk_file = self.cache_dir / f"{key}.{fmt}"
            if disk_file.is_file():
                try:
                    data = disk_file.read_bytes()
                    # Touch file for LRU disk ordering
                    disk_file.touch(exist_ok=True)
                    self._put_ram(key, data, fmt)
                    return data, fmt, disk_file
                except OSError:
                    continue

        return None

    def get_pixmap(self, key: str) -> Optional[QPixmap]:
        """
        Retrieves cached QPixmap for fast PySide6 UI display.
        """
        if key in self._ram_cache:
            data, fmt, size, pix = self._ram_cache[key]
            if pix is not None and not pix.isNull():
                self._ram_cache.move_to_end(key)
                return pix
            # If pixmap was not created yet, create it
            pix = QPixmap()
            pix.loadFromData(data)
            self._ram_cache[key] = (data, fmt, size, pix)
            self._ram_cache.move_to_end(key)
            return pix

        res = self.get(key)
        if res is not None:
            data, fmt, path = res
            pix = QPixmap()
            pix.loadFromData(data)
            # update RAM entry with pixmap
            size = len(data)
            self._put_ram(key, data, fmt, pix)
            return pix

        return None

    def save(
        self,
        key: str,
        image_bytes: bytes,
        prefer_webp: bool = True,
        quality: int = 92,
    ) -> Tuple[Path, str]:
        """
        Saves thumbnail bytes to disk and RAM cache.
        Attempts WebP encoding for crisp math formulas and compact file sizes.
        Falls back to PNG if WebP fails or is unrequested.
        """
        fmt = "png"
        final_bytes = image_bytes

        if prefer_webp:
            # Use QImage to convert PNG bytes to high-quality WebP
            qimg = QImage()
            if qimg.loadFromData(image_bytes):
                byte_array = QByteArray()
                buffer = QBuffer(byte_array)
                buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                if qimg.save(buffer, "WEBP", quality):
                    final_bytes = bytes(byte_array.data())
                    fmt = "webp"

        disk_file = self.cache_dir / f"{key}.{fmt}"
        temp_file = disk_file.with_name(f"{disk_file.name}.{os.getpid()}.{time.monotonic_ns()}.tmp")

        temp_file.write_bytes(final_bytes)
        temp_file.replace(disk_file)

        self._put_ram(key, final_bytes, fmt)
        self._trim_disk(keep=disk_file)
        return disk_file, fmt

    def render_and_cache(
        self,
        pdf_path: Path | str,
        key: str,
        page: int = 0,
        scale: float = 1.2,
        prefer_webp: bool = True,
        quality: int = 92,
    ) -> ThumbnailResult:
        """
        Renders a PDF page to cropped thumbnail bytes and saves to cache.
        """
        existing = self.get(key)
        if existing:
            data, fmt, path = existing
            return ThumbnailResult(key=key, file_path=path, format=fmt, data=data, cache_hit=True)

        import pymupdf
        with pymupdf.open(pdf_path) as document:
            if page >= len(document):
                page = 0
            target = document[page]
            rectangles = [pymupdf.Rect(block[:4]) for block in target.get_text("blocks")]
            rectangles += [drawing["rect"] for drawing in target.get_drawings()]
            clip = None
            for rect in rectangles:
                clip = rect if clip is None else clip | rect

            # Add gentle padding to preserve descenders and accents
            if clip is not None:
                clip = (clip + (-10, -10, 10, 10)) & target.rect

            pixmap = target.get_pixmap(matrix=pymupdf.Matrix(scale, scale), clip=clip)
            raw_png = pixmap.tobytes("png")

        path, fmt = self.save(key, raw_png, prefer_webp=prefer_webp, quality=quality)
        return ThumbnailResult(key=key, file_path=path, format=fmt, data=raw_png, cache_hit=False)

    def _put_ram(self, key: str, data: bytes, fmt: str, pix: Optional[QPixmap] = None):
        size = len(data)
        if key in self._ram_cache:
            _, _, old_size, _ = self._ram_cache.pop(key)
            self._ram_usage -= old_size

        self._ram_cache[key] = (data, fmt, size, pix)
        self._ram_usage += size
        self._trim_ram()

    def _trim_ram(self):
        while self._ram_usage > self.ram_limit and len(self._ram_cache) > 1:
            k, (_, _, s, _) = self._ram_cache.popitem(last=False)
            self._ram_usage -= s

    def _trim_disk(self, keep: Optional[Path] = None):
        files = sorted(self.cache_dir.glob("*.webp")) + sorted(self.cache_dir.glob("*.png"))
        if not files:
            return
        files.sort(key=lambda p: p.stat().st_mtime)
        total_size = sum(f.stat().st_size for f in files)

        for f in files:
            if total_size <= self.disk_limit:
                break
            if keep is not None and f.resolve() == keep.resolve():
                continue
            try:
                size = f.stat().st_size
                f.unlink(missing_ok=True)
                total_size -= size
            except OSError:
                continue

    def clear_cache(self, preserve_assets: bool = True) -> int:
        """
        Safely clears thumbnail cache without deleting user assets or databases.
        """
        self._ram_cache.clear()
        self._ram_usage = 0

        cleared_count = 0
        for p in list(self.cache_dir.glob("*.webp")) + list(self.cache_dir.glob("*.png")) + list(self.cache_dir.glob("*.tmp")):
            try:
                p.unlink(missing_ok=True)
                cleared_count += 1
            except OSError:
                pass
        return cleared_count

    def disk_usage(self) -> int:
        return sum(f.stat().st_size for f in self.cache_dir.glob("*.*") if f.is_file())

    def ram_usage(self) -> int:
        return self._ram_usage
