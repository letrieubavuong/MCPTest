# BÁO CÁO NGHIỆM THU THỰC TẾ VÀ KIỂM TOÁN ĐỘC LẬP — PHASE I
**Dự án:** MCPTest (LaTeX Question Studio)  
**Phiên bản phát hành:** 0.5.2 (Win64)  
**Ngày thực hiện:** 13/10/2026  
**Baseline cam kết:** `313c91a6ef89a5f374738382ec900db523cc0d2e`  

---

## 1. TỔNG QUAN VÀ MỤC TIÊU KIỂM TOÁN

Phase I tập trung kiểm toán độc lập chất lượng và độ ổn định thực tế của MCPTest sau khi hoàn thành Phase A–H. Toàn bộ các thử nghiệm được thực hiện trên mã nguồn thực tế, dữ liệu LaTeX thực, đo lường RAM/latency thực tế và giao diện người dùng thực trên Windows, tuân thủ nghiêm ngặt nguyên tắc:
1. **Không viết lại kiến trúc, không xóa dữ liệu người dùng.**
2. **Không làm thay đổi nghiệp vụ đang hoạt động tốt.**
3. **Không bịa đặt số liệu hay dùng benchmark giả lập.**
4. **Không bỏ qua lỗi P0/P1.**

---

## 2. DANH SÁCH LỖI PHÁT HIỆN VÀ PHƯƠNG ÁN XỬ LÝ

| Mức độ | Vấn đề phát hiện | Nguyên nhân gốc rễ | Giải pháp kỹ thuật | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **P0** | Crash tiến trình do Heap Corruption (`0xc0000374`) trên Windows | `QThreadPool` worker (`RenderJob`, `CompileJob`) nắm giữ tham chiếu đối tượng C++ Qt khi luồng kết thúc hoặc khi GUI bị hủy | Thiết lập `setAutoDelete(False)`, ngắt kết nối an toàn các slot, dùng weakref và `QMetaObject.invokeMethod` để đồng bộ hủy tài nguyên an toàn (`src/latex_question_studio/ui/jobs.py` & `main_window.py`) | **ĐÃ KHẮC PHỤC TRIỆT ĐỂ** |
| **P1** | `sqlite3.OperationalError: unable to open database file` | Thư mục cha chứa tệp CSDL chưa tồn tại khi khởi chạy ở đường dẫn mới hoặc môi trường tạm | Bổ sung `self.path.parent.mkdir(parents=True, exist_ok=True)` ngay trong `Database.connect()` (`src/latex_question_studio/persistence/database.py`) | **ĐÃ KHẮC PHỤC TRIỆT ĐỂ** |
| **P1** | Ước lượng thiếu RAM cache Thumbnail | `_ram_usage` chỉ tính dung lượng WebP/PNG nén (~20–50 KB), bỏ qua `QPixmap` giải mã trong RAM (`w * h * 4`, ~0.5–2 MB/ảnh) | Triển khai 2-tier memory tracking: cộng dồn `w * h * 4` vào bộ nhớ RAM, kích hoạt giải phóng LRU nghiêm ngặt khi chạm ngưỡng 128 MiB (`src/latex_question_studio/preview/thumbnails.py`) | **ĐÃ KHẮC PHỤC TRIỆT ĐỂ** |
| **P2** | Bounding Box cắt mất dấu Tiếng Việt, mũi tên TikZ và ảnh raster | `Compiler.render` chỉ lấy bbox từ nét vẽ vector, thiếu `get_image_info()` và không có lề an toàn | Bổ sung bbox ảnh nhúng raster và lề an toàn padding `(-14, -14, 14, 14)` điểm ảnh trước khi crop pixmap (`src/latex_question_studio/preview/compiler.py`) | **ĐÃ KHẮC PHỤC TRIỆT ĐỂ** |
| **P2** | Thẻ câu hỏi lỗi không hiển thị chi tiết và thiếu nút Thử lại | Render thất bại hiển thị icon chung mà không có nút thao tác nhanh | Bổ sung `cardErrorBadge` và button `retry_btn` ("Thử lại") ngay trên thẻ câu hỏi ở thư viện (`src/latex_question_studio/ui/pages/library.py`) | **ĐÃ KHẮC PHỤC TRIỆT ĐỂ** |
| **P2** | Tranh chấp tệp ghi log trên Windows giữa các tiến trình | Nhiều tiến trình kiểm thử đồng thời truy cập `preview.log` gây `WinError 32` | Phân lập thư mục tạm trong build script và chạy chuỗi kiểm thử tuần tự an toàn | **ĐÃ KHẮC PHỤC TRIỆT ĐỂ** |

---

## 3. DANH SÁCH FILE THAY ĐỔI TRONG PHASE I

### Mã nguồn chính (`src/`):
- `src/latex_question_studio/ui/jobs.py`: Xử lý triệt để memory corruption và giải phóng job thread pool.
- `src/latex_question_studio/ui/main_window.py`: Quản lý lifecycle luồng render nền và xử lý tín hiệu retry.
- `src/latex_question_studio/persistence/database.py`: Tự động tạo thư mục CSDL cha, đảm bảo tính bền vững.
- `src/latex_question_studio/preview/thumbnails.py`: Quản lý 2-tier RAM cache (uncompressed pixmap `w*h*4`), LRU eviction 128 MiB, bảo vệ asset gốc.
- `src/latex_question_studio/preview/compiler.py`: Padding an toàn `(-14, -14, 14, 14)`, tính toán bbox ảnh raster từ `get_image_info()`.
- `src/latex_question_studio/ui/pages/library.py`: Nút retry và badge lỗi biên dịch trên question card.

### Kiểm thử tự động (`tests/`):
- `tests/test_phase_i_thumbnail_ram.py`: 4 tests xác thực định mức RAM giải mã, LRU eviction và `clear_cache()`.
- `tests/test_phase_i_thumbnail_quality.py`: 4 tests xác thực padding, nhúng hình ảnh, TikZ và PDF chất lượng cao.
- `tests/test_phase_i_ui_acceptance.py`: 3 tests nghiệm thu UI ở 3 độ phân giải (1366×768, 1600×900, 1920×1080), Card/List mode.
- `tests/test_phase_i_exam_workflow.py`: 2 tests kiểm thử toàn bộ luồng tạo đề Toán, KHTN, Vật lý, an toàn đề thi học sinh và ZIP độc lập.

### Công cụ đo kiểm & Báo cáo (`scripts/` & `docs/`):
- `scripts/benchmark_phase_i3.py`: Đo kiểm 200 câu LaTeX thực tế.
- `scripts/capture_phase_i5_ui.py`: Chụp ảnh giao diện thật ở các độ phân giải.
- `scripts/prototype_katex_eval.py`: Đo kiểm prototype và tính khả thi KaTeX.
- `docs/PHASE_I_BASELINE.md`: Báo cáo hiện trạng Phase I.1.
- `docs/PHASE_I_BENCHMARK_REPORT.md`: Báo cáo chi tiết benchmark Phase I.3.
- `docs/KATEX_EVALUATION_REPORT.md`: Báo cáo đánh giá độc lập kiến trúc KaTeX Phase I.7.

---

## 4. KẾT QUẢ KIỂM THỬ TỰ ĐỘNG TOÀN DIỆN (PYTEST)

- **Tổng số ca kiểm thử:** **226 / 226 PASSED (100%)**
- **Thời gian thực thi:** 833.28 giây (~13 phút 53 giây)
- **Số bài test thất bại (Failed):** 0
- **Số bài test bỏ qua (Skipped):** 0

### Phân rã kết quả theo các nhóm module:
1. **Kiểm toán Phase I mới:** 13/13 PASSED
   - `test_phase_i_thumbnail_ram.py`: 4 passed
   - `test_phase_i_thumbnail_quality.py`: 4 passed
   - `test_phase_i_ui_acceptance.py`: 3 passed
   - `test_phase_i_exam_workflow.py`: 2 passed
2. **Độ ổn định & An toàn đề thi (Phase B–H):** 33/33 PASSED
   - `test_phase_b_student_safety.py`: 4 passed
   - `test_phase_c_portable_export.py`: 4 passed
   - `test_phase_d_exam_builder.py`: 6 passed
   - `test_phase_e_library_ui.py`: 6 passed
   - `test_phase_f_thumbnail_perf.py`: 4 passed
   - `test_phase_g_lesson_editor.py`: 4 passed
   - `test_phase_h_release_integrity.py`: 5 passed
3. **Trình soạn thảo WYSIWYG & Công thức Toán:** 31/31 PASSED
4. **Nhập dữ liệu, Phân loại & Cấu trúc đề:** 15/15 PASSED
5. **Cơ sở dữ liệu, Phiên bản & Di chuyển dữ liệu:** 11/11 PASSED (`test_persistence.py`)
6. **Các bài kiểm tra tích hợp khác:** 123/123 PASSED

---

## 5. BENCHMARK RENDER THUMBNAIL THỰC TẾ (PHASE I.3)

### So sánh với Benchmark cũ (Phase F):
- **Phase F (Cũ):** Dùng cùng 1 ảnh mẫu SVG cho 200 câu giả lập. Chỉ đo được tốc độ I/O đĩa cục bộ, hoàn toàn không phản ánh chi phí biên dịch pdfLaTeX và dựng ảnh PyMuPDF.
- **Phase I.3 (Thực tế):** Sử dụng **200 câu hỏi LaTeX nội dung thật** thuộc 8 nhóm phân loại:
  1. Công thức toán học (`\frac`, `\sqrt`, `\int`, ma trận)
  2. Trắc nghiệm 4 lựa chọn (`\choice`)
  3. Đúng / Sai (`\choiceTF`)
  4. Trả lời ngắn (`\shortans`)
  5. Có hình ảnh nhúng (`\includegraphics`)
  6. Hình vẽ TikZ và `tkz-euclide`
  7. Bảng biểu số liệu (`tabular`)
  8. Macro chuyên biệt chuẩn MAPClass

### Bảng số liệu đo lường thực tế:
| Chỉ số đo lường | Giá trị thực nghiệm | Ghi chú |
| :--- | :--- | :--- |
| **Tỷ lệ biên dịch thành công** | **200 / 200 (100%)** | Không có câu hỏi nào lỗi cú pháp |
| **Thời gian biên dịch pdfLaTeX** | **2,606.58 ms / câu** (trung bình) | TikZ/Bảng: 3,800–4,500 ms; Công thức: ~1,800 ms |
| **Thời gian chuyển PDF → Ảnh (PyMuPDF)** | **29.54 ms / câu** | Độ phân giải cao, khử răng cưa |
| **Thời gian mã hóa WebP** | **32.91 ms / câu** | Tối ưu nén lossless/near-lossless |
| **Độ trễ đọc Cold Disk Cache** | **9.66 ms / ảnh** | Lần đầu nạp từ ổ cứng |
| **Độ trễ đọc Hot RAM Cache** | **0.05 ms / ảnh (50 µs)** | Nhanh hơn Cold Cache **193 lần** |
| **Thời gian hiển thị 20 câu đầu** | **39.0 ms** | Đạt chuẩn phản hồi UI mượt mà |
| **Thời gian hiển thị 50 câu** | **89.8 ms** | Không gây giật lag luồng giao diện |
| **Thời gian hiển thị 100 câu** | **180.2 ms** | Nạp tức thì khi cuộn trang |
| **Dung lượng cache 200 câu (WebP)** | **3.44 MB** | Tiết kiệm **23.9%** so với PNG (4.52 MB) |
| **Peak RAM đo được của ứng dụng** | **130.18 MB** | Bộ thu dọn LRU 128 MiB hoạt động chính xác |

---

## 6. NGHIỆM THU GIAO DIỆN VÀ ẢNH CHỤP THỰC TẾ (PHASE I.5)

Ứng dụng đã được kiểm tra trên các độ phân giải tiêu chuẩn:
- **1366 × 768** (Laptop phổ thông)
- **1600 × 900** (Màn hình trung bình)
- **1920 × 1080** (Màn hình Full HD)

### Bằng chứng ảnh chụp thực tế (Artifacts):
1. `artifacts/phase_i5_library_1366x768_cards.png`: Chế độ Thẻ (Card view) ở 1366×768 — hiển thị đầy đủ thông tin, thẻ câu hỏi thoáng, nút phân loại và xem trước hiển thị rõ nét.
2. `artifacts/phase_i5_library_1366x768_list.png`: Chế độ Danh sách (Compact list) ở 1366×768 — mật độ hiển thị cao, dễ dàng quản lý số lượng lớn câu hỏi.
3. `artifacts/phase_i5_library_1600x900_search_filter.png`: Bộ lọc đa tiêu chí và ô tìm kiếm FTS ở 1600×900 — cây phân loại môn học/khối lớp phản hồi nhanh.
4. `artifacts/phase_i5_library_1920x1080_full_overview.png`: Toàn cảnh ngân hàng câu hỏi ở độ phân giải 1920×1080 — thiết kế Light theme hiện đại, không mô phỏng bố cục VS Code, thanh công cụ không bị đè nút.

---

## 7. NGHIỆM THU NGHIỆP VỤ THỰC TẾ (PHASE I.6)

Thực hiện kiểm thử luồng nghiệp vụ hoàn chỉnh với bộ dữ liệu môn Toán, Vật lý, KHTN:
1. **Chống trùng lặp:** Tự động phát hiện hash trùng khớp khi nhập lại cùng một tệp TeX; không tạo bản ghi rác.
2. **Bảo tồn nội dung gốc:** Tách biệt hoàn toàn `source` gốc trong CSDL và bản dựng; chỉnh sửa có tạo revision tăng dần.
3. **Bảo mật tuyệt đối đề thi học sinh:**
   - Trong tệp `de-thi-hoc-sinh.tex`, toàn bộ macro `\True`, khối `\loigiai{...}`, `\hdan{...}` và đáp án `\shortans` đều bị loại bỏ hoàn toàn khỏi phần thân đề thi.
   - Preamble đề thi học sinh được bổ sung các macro ghi đè an toàn (`\renewcommand{\True}{}`).
4. **Giữ nguyên tài nguyên minh họa:**
   - Cả đề giáo viên và học sinh đều bảo tồn nguyên vẹn các khối TikZ và tệp ảnh đính kèm (`assets/<sha256>.png`).
5. **Gói ZIP độc lập (Portable Bundle):**
   - Đóng gói đầy đủ tệp TeX, thư mục `assets/` và `manifest.json`.
   - Giải nén sang thư mục độc lập khác kiểm tra khớp 100% mã hash SHA256 từng tài nguyên.

---

## 8. ĐÁNH GIÁ ĐỘC LẬP VỀ KATEX (PHASE I.7)

Theo phân tích chi tiết trong `docs/KATEX_EVALUATION_REPORT.md`:
- **Ưu điểm của KaTeX:** Render công thức toán đơn lẻ trong vài mili-giây trên Web/DOM.
- **Nhược điểm chí mạng:**
  1. **Không hỗ trợ TikZ và `tkz-euclide`** (thành phần cốt lõi của ngân hàng câu hỏi môn Toán và Vật lý Việt Nam).
  2. **Không tương thích bộ macro `ex_test.sty` và `MAPClass.cls`** dùng trong các kỳ thi.
  3. **Tăng kích thước bản cài:** Cần tích hợp Chromium / `QtWebEngine` làm tăng kích thước bộ cài thêm **>120 MB** và chiếm thêm **>180 MB RAM**.
  4. **Lệch chuẩn WYSIWYG:** Bản preview KaTeX sẽ không khớp với bản in PDF thật của pdfLaTeX.
- **Khuyến nghị kiến trúc:** **Giữ nguyên pdfLaTeX làm single source of truth**, tận dụng cache thumbnail WebP + PyMuPDF cực nhanh (đáp ứng hiển thị trong 0.05 ms từ RAM). Không tích hợp KaTeX vào ứng dụng chính.

---

## 9. ĐÓNG GÓI BẢN PHÁT HÀNH WINDOWS & SMOKE TEST (PHASE I.8)

Tiến trình build tự động qua `scripts/build.ps1 -PackageRelease` đã hoàn thành xuất sắc:
- **Tệp thực thi:** `dist/0.5.2/LaTeXQuestionStudio/LaTeXQuestionStudio.exe`
  - SHA256: `bc8080b5506e4113bf30102d777cc0df52ce889cb0b299fac70a4876a8fa4b86`
  - Subsystem: Windows GUI (PE Subsystem 2, hoàn toàn không bật cửa sổ Console đen).
  - Icon: 10 kích thước hợp lệ tích hợp sẵn.
- **Gói Release ZIP:** `release/LaTeXQuestionStudio-0.5.2-win64.zip`
  - Dung lượng: **77,499,547 bytes (~73.9 MB)**
  - SHA256: `5fc270d058bfe432c155454ace7223426d3fcb7cd558c2aef57394d7efc667a2`
- **Kết quả Smoke Test:**
  - `integrity`: `ok`
  - `schema`: `19`
  - `taxonomy_nodes`: `641`
  - `ui_modules_current`: `true` (20/20 modules)
  - `all_modules_current`: `true` (41/41 modules)
  - `bundled_user_database`: `false` (sạch sẽ, không dính CSDL người dùng thử nghiệm)
  - `bundled_secret_config`: `false`

---

## 10. RỦI RO CÒN LẠI VÀ HƯỚNG DẪN VẬN HÀNH

1. **Phụ thuộc môi trường TeX cục bộ:** Để biên dịch các câu hỏi có gói TikZ đặc thù chưa có trong bundle, máy tính giáo viên cần cài sẵn bản phân phối TeX (MiKTeX hoặc TeX Live). Ứng dụng đã có cơ chế tự động nhận diện `pdflatex` trong PATH và hướng dẫn cài đặt nếu thiếu.
2. **Kích thước CSDL lớn:** Sau khi nhập trên 50,000 câu hỏi, khuyến nghị người dùng sử dụng tính năng "Tối ưu bộ nhớ đệm" định kỳ trong mục Cài đặt.

---

## 11. KẾT LUẬN

Phase I đã được hoàn thành 100% từ I.1 đến I.8, đạt mọi tiêu chí đề ra về độ ổn định, quản lý bộ nhớ RAM, chất lượng hình ảnh xem trước, an toàn đề thi và đóng gói phát hành thực tế.
