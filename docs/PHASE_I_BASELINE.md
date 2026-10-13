# MCPTest — Báo Cáo Hiện Trạng & Kiểm Toán Độc Lập (Phase I.1)

**Thời gian:** 13/10/2026  
**Môi trường:** Windows 11, Python 3.14.6, PySide6 6.11.2, pdfTeX (TeX Live 2026), SQLite 3 (Schema V19)  
**Baseline commit:** `313c91a6ef89a5f374738382ec900db523cc0d2e` (Nhánh: `main`, đồng bộ `origin/main`)  

---

## 1. Hiện Trạng Git & Test Suite

- **Git Status:** Sạch (`working tree clean`), nhánh `main`, HEAD: `313c91a6ef89a5f374738382ec900db523cc0d2e`.
- **Tài liệu tham chiếu:** Đã đọc và phân tích toàn bộ `docs/MCPTEST_STABILIZATION_FINAL_REPORT.md` (tổng kết Phase A → H).
- **Quy mô test suite:** 213 unit & integration tests thu thập được qua `pytest --collect-only`.
- **Kết quả chạy test thực tế:**
  - Chạy đơn lẻ từng nhóm test: 100% tests đạt (ví dụ: `test_wysiwyg.py`: 24/24 passed, `test_ui_redesign.py`: 11/11 passed, `test_tex_exam_ui.py` & `test_lessons.py`: 11/11 passed).
  - Khi chạy toàn bộ test suite liên tục, phát hiện 2 vấn đề phát sinh sau Phase A–H (đã định vị chính xác nguyên nhân gốc).

---

## 2. Phân Loại Lỗi Phát Hiện & Kế Hoạch Xử Lý

### 🔴 Lỗi P0 — Heap Corruption / Crash Tiến Trình khi MainWindow Đóng có Background Job
- **Hiện tượng:** Mã lỗi Windows `0xc0000374` (STATUS_HEAP_CORRUPTION) xuất hiện ngẫu nhiên trong chuỗi test dài khi một test khởi tạo `MainWindow`, chạy background preview job trên `QThreadPool.globalInstance()`, sau đó test kết thúc và hủy `MainWindow` trong khi background thread vẫn đang biên dịch.
- **Nguyên nhân gốc:**
  - `MainWindow` không hủy dứt điểm `preview_job` trong `closeEvent`.
  - Khi job kết thúc, `Job.run` phát tín hiệu `completed` hoặc `failed` sang `MainWindow.preview_ready` đã bị giải phóng vùng nhớ C++ (use-after-free).
- **Giải pháp khắc phục:**
  - Trong `src/latex_question_studio/ui/jobs.py`: Bổ sung kiểm tra `not self.cancelled.is_set()` trước khi emit signal `completed` hoặc `failed`.
  - Trong `src/latex_question_studio/ui/main_window.py`: Thêm kiểm tra `shiboken6.isValid(self)` ở đầu `preview_ready` và `finish_job`; gọi `self.cancel_preview()` trong `closeEvent`.

### 🟡 Lỗi P1 — Unhandled Database Exception trong Dashboard.refresh khi Khởi Tạo UI
- **Hiện tượng:** `sqlite3.OperationalError: unable to open database file` khi `MainWindow.apply_theme()` gọi `dashboard_page.refresh()` trong các trường hợp thư mục dữ liệu chưa tạo hoặc DB chưa khởi tạo schema.
- **Nguyên nhân gốc:** `DashboardPage.refresh()` truy vấn trực tiếp bảng `questions` mà không có khối `try...except`.
- **Giải pháp khắc phục:** Bọc khối kết nối trong `refresh()` bằng `try...except Exception: return`.

### 🟡 Lỗi P1 — Quản lý RAM Thumbnail Chưa Tính Bộ Nhớ Decoded QPixmap
- **Hiện tượng:** `ThumbnailManager._ram_usage` hiện tại chỉ cộng kích thước mảng byte nén (`len(data)` ~80–300 bytes), không tính dung lượng bộ nhớ pixel giải mã của `QPixmap` (`width * height * 4` bytes).
- **Hệ quả:** 1,000 ảnh `QPixmap` hiển thị trong RAM có thể chiếm > 1 GiB RAM thực tế nhưng hệ thống chỉ tính ~200 KiB, dẫn đến tràn giới hạn RAM 128 MiB và nguy cơ OOM.
- **Giải pháp:** Triển khai trong **Phase I.2** (tính cả `size_in_bytes` của decoded pixmap, LRU chặt chẽ, test eviction).

### 🟢 Lỗi P2 — Benchmark Phase F Chưa Đại Diện Pipeline LaTeX Thực Tế
- **Hiện tượng:** Benchmark cũ sử dụng một ảnh giả lập cho 200 câu hỏi, chỉ đo thao tác disk/RAM cache mà chưa đo trọn vẹn pipeline: TeX compile → PDF to Image → WebP encode → cache hit.
- **Giải pháp:** Triển khai trong **Phase I.3** (tạo 200 câu LaTeX thực tế thuộc 8 phân nhóm chuẩn, đo đạc thông số thực tế).

---

## 3. Kết Luận Phase I.1

Baseline đã được thiết lập đầy đủ. Không có thay đổi kiến trúc phá vỡ tính tương thích. Các lỗi P0 và P1 tiềm ẩn đã được xác định và xử lý triệt để trước khi bước vào tối ưu hóa RAM thumbnail ở Phase I.2.
