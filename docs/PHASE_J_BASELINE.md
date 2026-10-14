# BÁO CÁO HIỆN TRẠNG VÀ PHÉP ĐO TÁI LẬP — PHASE J.0

**Dự án:** MCPTest (LaTeX Question Studio)  
**Thời điểm thực hiện:** 14/10/2026  
**Baseline commit:** `ac1c0b033999c88ce3d5e2628f1a75ff9f007587`  
**Nhánh:** `main` (clean working tree)  

---

## 1. Môi trường kiểm thử thực tế

* **Hệ điều hành:** Windows 11 Pro 64-bit (`Windows-11-10.0.26100-SP0`)
* **Python Runtime:** Python 3.14.6 (64-bit)
* **GUI Toolkit:** PySide6 6.11.2 (Qt 6.11.2)
* **Phân phối TeX:** TeX Live 2026 (`pdfTeX 3.141592653-2.6-1.40.29`, kpathsea version 6.4.2)
* **Cơ sở dữ liệu:** SQLite 3 (WAL mode, schema version 19)

---

## 2. Kết quả kiểm thử trước Phase J

* **Tổng số bài kiểm thử pytest:** **227 / 227 PASSED (100%)**
* **Số lỗi (Failed):** 0
* **Số bài bỏ qua (Skipped):** 0
* **Thời gian chạy test:** ~8 phút 50 giây (bao gồm biên dịch pdfLaTeX thực tế và kiểm thử giao diện Qt)

---

## 3. Bộ dữ liệu tái lập được xác lập (Data Provenance)

Tuân thủ nguyên tắc không được bịa đặt hoặc gọi dữ liệu giả lập là dữ liệu thật:
1. **Dữ liệu thực từ kho lưu trữ:**
   * **898 câu hỏi thực** được trích xuất trực tiếp từ 23 tệp bài tập thực tế tại `3L1/Exercise/*.tex` (chứa các công thức vật lý, bảng số liệu, hình vẽ TikZ, `tkz-euclide`, macro `\immini`, `\impicinpar`, `\doC`).
   * **200 câu hỏi mẫu thực nghiệm** từ bộ benchmark Phase I.3 thuộc 8 nhóm phân loại (công thức toán, trắc nghiệm `\choice`, đúng sai `\choiceTF`, trả lời ngắn `\shortans`, `\includegraphics`, TikZ/`tkz-euclide`, bảng biểu, MAPClass).
2. **Dữ liệu tổng hợp có nhãn minh bạch:**
   * Được sinh qua script `scripts/generate_phase_j_dataset.py`.
   * Mọi câu hỏi tổng hợp đều được gắn nhãn bắt buộc `[SYNTHETIC-PHASE-J]` trong nội dung đề bài để phân biệt rành mạch, phục vụ đo kiểm tải lớn (1.000 câu và 10.000 câu).

---

## 4. Các điểm nghẽn và rủi ro được định vị cho Phase J

1. **J1 — Render lần đầu & Hàng đợi Viewport:**
   * Hiện tại, khi duyệt danh sách câu hỏi, thời gian biên dịch cold compile trung bình là ~2.61s/câu.
   * Nếu người dùng cuộn nhanh hoặc nạp nhiều câu, không được phép render toàn bộ hàng nghìn câu cùng lúc gây nghẽn CPU và giật UI.
   * Cần triển khai hàng đợi ưu tiên: **câu trong viewport > câu đang chọn > prefetch lân cận > background**.
   * Cần loại trừ duplicate jobs (deduplication) theo cache key.
   * Cần giới hạn concurrency (2–3 worker threads) để bảo vệ TeX engine và tài nguyên hệ thống.

2. **J2 — Chuẩn hóa một logic Crop Bounding Box duy nhất:**
   * Bounding box đang được tính rải rác giữa `compiler.py` và `thumbnails.py`.
   * Cần hợp nhất vào một hàm duy nhất `calculate_crop_box()` tính toán chuẩn xác cho cả vector drawings, text blocks, ảnh raster `get_image_info()`, padding an toàn và hỗ trợ câu nhiều trang.

3. **J3 — Kiểm toán an toàn đề học sinh sau mở rộng `STUDENT_COMMANDS`:**
   * Sau khi cho phép `\immini`, `tkz-euclide`, `\doC`, `\tau`, v.v., cần kiểm tra phân tách ranh giới an toàn: macro nào là macro hiển thị/hình vẽ an toàn, macro nào có khả năng chứa đáp án ẩn.
   * Kiểm tra bóc tách `\True`, `\loigiai`, `\hdan`, `\shortans` lồng nhau, comment, escaped braces.

4. **J4 — Đo lường độ mượt UI (Responsiveness):**
   * Đo lường frame-time p50/p95/p99 bằng công cụ Qt event timer, không suy đoán cảm tính.

5. **J5 — Kiểm thử nghiệm thu đầu cuối (E2E Teacher Acceptance):**
   * Toàn bộ luồng từ nhập TeX -> sửa -> xuất đề -> kiểm tra ZIP độc lập -> biên dịch PDF.
