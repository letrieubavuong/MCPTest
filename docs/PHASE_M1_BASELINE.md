# MCPTest — BÁO CÁO THIẾT LẬP BASELINE PHASE M.1 (M1.0)

**Dự án:** MCPTest (`LaTeX Question Studio`)  
**Tài liệu tham chiếu:** [`docs/MCPTEST_PHASE_M1_LESSON_RELIABILITY_CODEX_PROMPT.md`](file:///c:/Lap%20trinh%20Android/MCPTest2027/MCPTest/docs/MCPTEST_PHASE_M1_LESSON_RELIABILITY_CODEX_PROMPT.md)  
**Mục tiêu:** Thiết lập điểm xuất phát có thể tái lập (reproducible baseline) cho Phase M.1 — Lesson Reliability & Real-World Acceptance.  
**Thời điểm ghi nhận:** 15/10/2026.

---

## 1. THÔNG SỐ MÔI TRƯỜNG & PHIÊN BẢN

| Thông số | Giá trị xác thực trên hệ thống |
|---|---|
| **Git Reference HEAD** | `58cd9d99723bf2157a9497e7486e902b9e28bf6f` (`58cd9d9`) |
| **Active Git Branch** | `phase-m1-lesson-reliability` (tách từ `main` sạch tại commit `58cd9d9`) |
| **Hệ điều hành (OS)** | Microsoft Windows 11 (`Microsoft Windows NT 10.0.26100.0 AMD64`) |
| **Python** | Python 3.14.6 (`tags/v3.14.6:c63aec6, Jun 10 2026, 10:26:10 [MSC v.1944 64 bit (AMD64)]`) |
| **PySide6 / Qt** | PySide6 6.11.2 (Qt runtime 6.11.2, Qt compiled 6.11.2) |
| **TeX Engine** | pdfTeX 3.141592653-2.6-1.40.29 (TeX Live 2026), kpathsea 6.4.2 |
| **Cơ sở dữ liệu** | SQLite 3 (`data/studio.db`), **Schema user_version = 19** |
| **Trạng thái Working Tree** | Clean trước khi bắt đầu nhiệm vụ M1.0 |

---

## 2. KẾT QUẢ KIỂM THỬ BAN ĐẦU (TEST SUITE BASELINE)

### 2.1. Kiểm thử toàn bộ hệ thống (Full Pytest Regression Suite)
- **Nguồn xác minh:** `artifacts/build-current/tests.xml` (từ cổng kiểm soát build chất lượng `scripts/build.ps1`).
- **Tổng số test:** **400 / 400 PASSED** (100% Đạt)
- **Failures:** 0
- **Errors:** 0
- **Skipped:** 0
- **Thời gian chạy:** 1187.49 giây (~19 phút 47 giây)

### 2.2. Nhóm kiểm thử chuyên biệt Bài giảng (Lesson Test Suite)
- **Lệnh thực thi:**
  ```powershell
  .\.venv\Scripts\python.exe -m pytest tests/test_lessons.py tests/test_lesson_creation.py tests/test_lesson_files.py tests/test_phase_g_lesson_editor.py tests/test_legacy_lesson_importer.py tests/test_phase_m_lesson_workspace.py -v
  ```
- **Kết quả:**
  ```text
  tests/test_lessons.py .........                                          [ 32%]
  tests/test_lesson_creation.py ......                                     [ 53%]
  tests/test_lesson_files.py .....                                         [ 71%]
  tests/test_phase_g_lesson_editor.py ....                                 [ 85%]
  tests/test_legacy_lesson_importer.py .                                   [ 89%]
  tests/test_phase_m_lesson_workspace.py ...                               [100%]
  ======================== 28 passed in 69.74s (0:01:09) ========================
  ```
- **Tổng số test bài giảng:** 28 / 28 PASSED.
- **Failures:** 0, **Skipped:** 0.

### 2.3. Nhóm kiểm thử Soạn thảo WYSIWYG & Đồng bộ Formula
- **Lệnh thực thi:**
  ```powershell
  .\.venv\Scripts\python.exe -m pytest tests/test_wysiwyg.py tests/test_wysiwyg_formula_input.py -v
  ```
- **Kết quả:** 31 / 31 PASSED (trong đó 24 test WYSIWYG core và 7 test Formula Input).

---

## 3. ĐO ĐẠC HIỆU NĂNG GIAO DIỆN & TÀI NGUYÊN (UI PERFORMANCE BASELINE)

Được đo lường tự động trên luồng làm việc thực tế với bài giảng KHTN 9 (gồm 3 khối cấu trúc: Lý thuyết với hình vẽ TikZ, Dạng toán phương pháp giải và Ví dụ mẫu có lời giải chi tiết):

| Chỉ số hiệu năng | Kết quả đo được (Baseline) | Ghi chú kỹ thuật |
|---|---|---|
| **Thời gian mở bài giảng (Open Lesson)** | **17.40 ms** | Tải cấu trúc cây khối, metadata và khởi tạo outline |
| **Thời gian lưu bài giảng (Save Lesson)** | **8.91 ms** | Lưu transaction SQLite vào bảng `lessons` & `lesson_revisions` |
| **Thời gian biên dịch & Render PDF (Preview)** | **3428.95 ms** (~3.43s) | Biên dịch qua pdfLaTeX với TikZ đa lớp + pdftoppm render ảnh |
| **Thời gian xuất gói bài giảng (Export Package)** | **2705.87 ms** (~2.71s) | Sinh `main.tex`, 3 thư mục `LyThuyet/`, `DangToan/`, `BTVD/` và compile |
| **Mức chiếm dụng bộ nhớ ban đầu (Start RSS)** | **43.38 MB** | Khi mới khởi tạo tiến trình Python + PySide6 |
| **Mức chiếm dụng bộ nhớ đỉnh (Peak RSS)** | **256.93 MB** | Sau khi tải UI, hiển thị QSplitter 3 cột và hoàn tất render PDF |

---

## 4. ẢNH CHỤP GIAO DIỆN THẬT (REAL UI SCREENSHOTS)

Các ảnh chụp màn hình được sinh trực tiếp từ giao diện thực tế của ứng dụng (không dùng mockup hình ảnh thay thế):

1. **Độ phân giải 1366 × 768 (Màn hình Laptop phổ biến):**  
   [`docs/images/lesson-workspace/m1_baseline_workspace_1366x768.png`](file:///c:/Lap%20trinh%20Android/MCPTest2027/MCPTest/docs/images/lesson-workspace/m1_baseline_workspace_1366x768.png)  
   *Mô tả:* Cột trái (Outline sư phạm) gọn gàng; Cột giữa (Editor soạn thảo TeX kèm thanh công cụ toán học); Cột phải (PDF Preview thời gian thực hiển thị hình vẽ TikZ tia khúc xạ).

2. **Độ phân giải 1920 × 1080 (Màn hình Desktop Full HD):**  
   [`docs/images/lesson-workspace/m1_baseline_workspace_1920x1080.png`](file:///c:/Lap%20trinh%20Android/MCPTest2027/MCPTest/docs/images/lesson-workspace/m1_baseline_workspace_1920x1080.png)  
   *Mô tả:* Không gian trải rộng tối ưu tỷ lệ 3 cột; các nút chèn sư phạm (`+ Lý thuyết`, `+ Dạng toán`, `+ Ví dụ`, `+ Bài tập`, `Bó dạng toán`) sẵn sàng thao tác nhanh.

---

## 5. SAO LƯU & XÁC MINH CƠ SỞ DỮ LIỆU FIXTURE SCHEMA 19

- **Tệp nguồn CSDL:** [`data/studio.db`](file:///c:/Lap%20trinh%20Android/MCPTest2027/MCPTest/data/studio.db)
- **Tệp sao lưu an toàn:** [`data/backup_schema19_baseline.db`](file:///c:/Lap%20trinh%20Android/MCPTest2027/MCPTest/data/backup_schema19_baseline.db)
- **Kích thước tệp sao lưu:** 483,328 bytes
- **Kết quả kiểm tra toàn vẹn (Integrity Check):** `ok`
- **Kiểm tra ràng buộc khóa ngoại (Foreign Key Check):** 0 vi phạm (`[]`)
- **Phiên bản Schema (PRAGMA user_version):** `19`
- **Số bảng dữ liệu được bảo toàn:** 29 bảng (bao gồm `lessons`, `lesson_revisions`, `lesson_exports`, `lesson_files`, `lesson_file_exercises`, `questions`, `taxonomy_nodes`, ...)
- **Xác minh khôi phục (Restore Verification):** Đã kiểm tra mở bản sao lưu và khôi phục vào vị trí độc lập, đọc lại đầy đủ 29 bảng và kiểm tra PRAGMA integrity đạt `ok`.

---

## 6. DANH SÁCH RỦI RO KỸ THUẬT PHÁT HIỆN CẦN GIẢI QUYẾT TRONG M1.1 - M1.4

1. **Rủi ro M1.1 (Importer):**
   - Chỉ số `coverage = min(100.0, max(50.0, ...))` trong `legacy_lesson_importer.py` đang che giấu tỷ lệ bảo toàn dưới 50%.
   - Parser heading regex không xử lý được ngoặc nhọn lồng nhau (ví dụ: `\section{Dạng 1: Tính $\sqrt{x^2+1}$}`).
   - Parser môi trường dùng regex non-greedy `.*?` có nguy cơ cắt nhầm môi trường lồng nhau.
   - Chưa hỗ trợ xử lý đệ quy `\input` / `\include` theo đường dẫn tương đối và phát hiện chu trình lặp (circular inclusion).
   - Thiếu cơ chế Dry-run import cho phép giáo viên duyệt trước các đoạn chưa map (unmapped raw blocks).
2. **Rủi ro M1.2 (Bảo mật học sinh & An toàn dữ liệu):**
   - Cần rà soát cơ chế fail-closed khi gặp macro không chuẩn nhằm ngăn chặn rò rỉ đáp án hoặc lời giải trong file TeX, file phụ, manifest và PDF học sinh.
3. **Rủi ro M1.3 (Trải nghiệm Workspace):**
   - Cần kiểm tra debounce/cancel preview job cũ để tránh tắc nghẽn giao diện khi gõ phím liên tục.
   - Drawer câu hỏi cần xử lý mượt mà khi ngân hàng mở rộng đến quy mô lớn.
