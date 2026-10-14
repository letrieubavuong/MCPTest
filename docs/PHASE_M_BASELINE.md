# MCPTest — BÁO CÁO AUDIT & ĐO ĐẠC BASELINE (PHASE M0)

**Dự án:** MCPTest (LaTeX Question Studio)  
**Tài liệu tham chiếu:** `docs/MCPTEST_PHASE_M_LESSON_WORKSPACE_REDESIGN_CODEX_PROMPT.md`  
**Mục tiêu:** Kiểm toán hiện trạng tab **Bài giảng**, đo đạc hiệu năng và định hướng kiến trúc cho toàn bộ Phase M0–M6.  
**Ngày thực hiện:** 14/10/2026.

---

## 1. Sơ đồ cấu trúc giao diện hiện tại & Đo đạc kích thước

### 1.1. Bố cục 3 vùng hiện thời
```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Top Bar: BÀI GIẢNG / Lý thuyết · Dạng toán · Ví dụ · Vận dụng                                         │
│ [Combo Chọn Bài] [Tạo bài mới v] [Lưu bài] [Xem trước F5] [Xuất TeX+PDF] [Thao tác khác v]             │
│ [Tên bài giảng: QLineEdit                                   ] [Toán 12 • 4 mục] [Rev 1] [Thông tin]   │
├──────────────────────┬────────────────────────────────────────────────┬────────────────────────────────┤
│ CỘT TRÁI (250px)     │ CỘT GIỮA (760px - Tabbed)                      │ CỘT PHẢI (360px - Cố định)     │
│ - OUTLINE NỘI DUNG   │ ┌────────────────────────────────────────────┐ │ THƯ VIỆN CÂU HỎI               │
│   (QTreeWidget)      │ │ Tab [Soạn thảo] | Tab [Xem trước (PDF)]    │ │ - Tìm kiếm QLineEdit           │
│ - CẤU TRÚC 3 THƯ MỤC │ ├────────────────────────────────────────────┤ │ - Bộ lọc: Môn, Khối, Chủ đề,   │
│   TỆP NGUỒN          │ │ Formatting: B I U M Undo Redo WYSIWYG ¶    │ │   Loại câu, Nhận thức        │
│   (LyThuyet/DangToan/│ │ Tên mục: QLineEdit                         │ │ - Bảng kết quả (QTableWidget)│
│    BTVD/ manifest)   │ │ Chính sách: Hiện đầy đủ / Chỉ đề / Riêng tư│ │ - Chèn vào: [BTVD / Ví dụ]   │
│ - [Chốt file]        │ │ Editor: LatexEditor / VisualLatexEditor    │ │ - [Chèn câu đã chọn]         │
│   [Liên kết toàn bài]│ │ Ghi chú riêng giáo viên (QPlainTextEdit)   │ │ - Trích lọc ngẫu nhiên       │
│ - Loại mục & Toolbar │ └────────────────────────────────────────────┘ │                                │
└──────────────────────┴────────────────────────────────────────────────┴────────────────────────────────┘
```

### 1.2. Đo đạc & Artifacts màn hình gốc
- **Độ phân giải 1366×768 (Laptop giáo viên phổ biến):**
  - Cột trái: 250px
  - Cột giữa: ~750px (chia đôi nếu chuyển tab; khi soạn thảo thì ẩn hoàn toàn PDF)
  - Cột phải: ~360px (bị thư viện ngân hàng chiếm cố định 1/3 màn hình)
  - Ảnh chụp baseline: `artifacts/lesson-workspace/baseline_lesson_page_1366x768.png`
- **Độ phân giải 1920×1080 (Màn hình Desktop):**
  - Không gian cột giữa dư dả nhưng vẫn buộc giáo viên chuyển tab qua lại để xem PDF compiled.
  - Ảnh chụp baseline: `artifacts/lesson-workspace/baseline_lesson_page_1920x1080.png`

---

## 2. Danh sách vấn đề và điểm nghẽn nghiệp vụ giáo viên (Friction Points)

1. **Tab "Soạn thảo" tách rời "Xem trước (PDF)":**
   - Giáo viên không thể vừa gõ công thức hoặc chỉnh sửa ví dụ vừa thấy trang PDF render song song.
   - Mỗi lần bấm xem trước, giao diện nhảy sang Tab thứ 2, làm mất ngữ cảnh dòng đang soạn.

2. **Hai lớp điều hướng cạnh tranh gây bối rối:**
   - Cột trái vừa có Cây Outline sư phạm (Lý thuyết → Dạng toán → Ví dụ → Bài tập), vừa có hộp "CẤU TRÚC 3 THƯ MỤC TỆP NGUỒN" với các file `LyThuyet/theory.tex`, `DangToan/dang-01.tex`, `BTVD/bai-tap-van-dung.tex`.
   - Giáo viên chỉ muốn soạn bài giảng logic, không muốn bị ép phải hiểu manifest hay quy tắc gán tệp nguồn nội bộ. Lớp tệp nguồn này cần được đưa vào chế độ **Nâng cao / Thu gọn**.

3. **Panel Ngân hàng chiếm dụng 1/3 màn hình:**
   - Trong phần lớn thời gian (soạn lý thuyết, viết lời giải ví dụ, trình bày phương pháp giải), giáo viên không cần tra cứu ngân hàng. Panel này chiếm 360px cố định, thu hẹp không gian soạn thảo.
   - Cần chuyển thành **Drawer / Trượt sang / Modal theo yêu cầu** khi bấm nút "Chèn từ ngân hàng".

4. **Thiếu nút chèn cấu trúc sư phạm nhanh:**
   - Giáo viên phải dùng dropdown "Loại mục" rồi bấm "Thêm mục cùng cấp / con".
   - Thiếu các nút trực quan ngữ cảnh cao: `+ Lý thuyết`, `+ Dạng toán & Phương pháp`, `+ Ví dụ`, `+ Nhóm bài tập`.

5. **Trải nghiệm biên tập TeX:**
   - Chế độ WYSIWYG có nguy cơ làm méo hoặc mất mã TikZ và macro đặc thù của `ex_test.sty`. Cần ưu tiên LaTeX Editor chuẩn với thanh công cụ chèn macro toán, công thức inline/display, phân số, căn, bảng, môi trường `ex`, `loigiai` và TikZ an toàn.

---

## 3. Bản đồ ánh xạ dữ liệu (Data Model Mapping)

| Thành phần Workspace mới | Mô hình dữ liệu hiện hữu (`document_json` & SQLite Schema 19) | Ghi chú tương thích |
|---|---|---|
| **Cây sư phạm bài giảng** | `doc['blocks']` (mỗi block có `id`, `parent`, `kind`, `title`, `source`, `policy`, `teacher_notes`, `assets`, `question`) | **100% tương thích.** Giữ nguyên cấu trúc cây cha con, không đổi ID. |
| **Phân loại tệp nguồn** | `doc['files']` và bảng SQLite `lesson_files`, `lesson_file_exercises` | **100% bảo toàn.** Tự động phân loại `theory` → `LyThuyet/`, `method` → `DangToan/`, `exercise` → `BTVD/`. |
| **Ghim câu hỏi ngân hàng** | `block['question'] = {'id', 'revision', 'snapshot', ...}` | Bảo toàn liên kết provenance, không sửa câu trong ngân hàng, cho phép override cục bộ trong bài. |
| **Tài nguyên ảnh / TikZ** | `block['assets']` và bảng `assets`, `question_assets` | Ánh xạ relative path an toàn, checksum SHA256. |
| **Mẫu bài giảng** | `LESSON_TEMPLATES`: `standard`, `methods`, `theory`, `worksheet`, `blank` | Mở rộng 4 mẫu thực tế đáp ứng GDPT 2018. |
| **Gói xuất Portable** | `service.export()` sinh `main.tex`, 3 thư mục con, PDF giáo viên/học sinh và `manifest.json` | Độc lập máy tính, không chứa đường dẫn tuyệt đối. |

---

## 4. Đo đạc Baseline Hiệu năng & Kiểm thử hiện tại

- **Bộ kiểm thử bài giảng hiện có:**
  - `tests/test_lessons.py` (9 tests)
  - `tests/test_lesson_creation.py` (6 tests)
  - `tests/test_lesson_files.py` (5 tests)
  - `tests/test_phase_g_lesson_editor.py` (4 tests)
  - **Kết quả Baseline:** `24/24 passed in 41.89s (100% PASS)`
- **Thời gian thao tác đo được (Baseline Measurements):**
  - Mở bài giảng có sẵn (load doc ~15 blocks): **< 25ms**
  - Chuyển mục trong outline: **< 15ms**
  - Gõ văn bản / TeX debounce autosave: **1500ms**
  - pdfLaTeX preview toàn bài (TeX Live 2026): **~1.2s - 2.8s**
  - Xuất gói di động đa thư mục: **~2.1s**

---

## 5. Kế hoạch hành động chi tiết (M1 – M6)

- **Phase M1:** Xây dựng khung giao diện 2/3 cột responsive (`QSplitter`), tách Drawer Ngân hàng câu hỏi, thanh Header bài giảng trực quan, thu gọn Tệp nguồn vào mục Nâng cao.
- **Phase M2:** Bộ công cụ biên tập sư phạm ngữ cảnh (`+ Lý thuyết`, `+ Dạng toán & Phương pháp`, `+ Ví dụ`, `+ Nhóm bài tập`), 4 mẫu bài thực tế, thao tác di chuyển Up/Down/Drag.
- **Phase M3:** Drawer chọn câu hỏi ngân hàng đa năng, gán vai trò (`Ví dụ`, `Luyện tập`, `Vận dụng`, `Về nhà`), pin revision, đường ống tài nguyên ảnh & TikZ.
- **Phase M4:** Preview PDF song song (Side-by-side) không giật lag, định vị lỗi biên dịch theo khối, xuất bản học sinh (bảo mật ẩn ghi chú/lời giải) và giáo viên.
- **Phase M5:** Trình nhập tài liệu `.tex` bài giảng truyền thống với bộ fallback Raw TeX block bảo toàn 100% nội dung lý thuyết.
- **Phase M6:** Tích hợp kiểm thử tự động toàn diện, xác thực E2E 3 môn (KHTN 9, Toán 8, Vật lí 10), regression toàn dự án và báo cáo nghiệm thu cuối cùng.
