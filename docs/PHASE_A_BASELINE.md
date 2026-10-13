# BÁO CÁO KIỂM TOÁN VÀ BASELINE HỆ THỐNG — PHASE A
**Thời điểm lập:** 13/10/2026  
**Dự án:** MCPTest (LaTeX Question Studio)  
**Tác giả:** Kỹ sư trưởng hệ thống  

---

## 1. Thông tin Baseline Git & Môi trường

| Thuộc tính | Giá trị ghi nhận |
| :--- | :--- |
| **Git Commit HEAD** | `69be3fac1cd920db8b6d70e90840b4197e0bf83b` |
| **Branch** | `main` (Up to date với `origin/main`) |
| **Working Tree** | Sạch sẽ, không có thay đổi dở dang (uncommitted) |
| **Hệ điều hành** | Windows 11 Pro 64-bit |
| **Python Runtime** | Python 3.14.6 |
| **Qt / PySide6** | PySide6 6.11.2 (Qt compiled 6.11.2) |
| **Database Engine** | SQLite (Schema PRAGMA `user_version` = 19) |
| **LaTeX Engine** | TeX Live 2026: `C:\texlive\2026\bin\windows\pdflatex.EXE` (Đã xác minh hoạt động) |
| **Tài nguyên Lớp & Gói**| `docs/Class/MAPClass.cls`, `docs/Packages/ex_test.sty`, `default_profile/` (Có sẵn đầy đủ) |

---

## 2. Kết quả Chạy Toàn Bộ Test Suite (Baseline)

- **Tổng số test thu thập:** 180 tests (trong 34 file kiểm thử).
- **Passed:** 169 tests.
- **Failed:** 11 tests.
- **Skipped:** 0 tests.
- **Thời gian chạy:** 358.43s (~6 phút).

### Phân tích chi tiết 11 lỗi tái hiện được (Reproducible Failures):

1. **Nhóm Menu & Điều hướng CSDL Cũ (`tests/test_curriculum.py` — 8 lỗi):**
   - `test_csdl_menu_chapter_order_and_lesson_navigation`
   - `test_math6_structure_practice_order_and_navigation`
   - `test_khtn7_schema9_upgrade_and_menu`
   - `test_math7_upgrade_structure_navigation_and_metadata`
   - `test_grade8_schema11_upgrade_intro_and_menu`
   - `test_grade9_upgrade_structure_order_and_navigation`
   - `test_upper_curricula_upgrade_membership_and_navigation`
   - `test_senior_curricula_upgrade_navigation_and_tree_icons`
   - **Nguyên nhân cốt lõi:** Phương thức `MainWindow.refresh_curriculum_menu(nodes)` hiện đang để thân hàm là `pass`, dẫn đến việc các thuộc tính truy cập menu phân cấp (`window.math10_menu`, `window.physics11_menu`, v.v.) không được khởi tạo.

2. **Nhóm Menu Catalog Động (`tests/test_stabilization.py` — 1 lỗi):**
   - `test_external_catalog_coexists_and_dynamic_menu`
   - **Nguyên nhân:** Cùng nguyên nhân trên (`window.newbook_menu` không được tạo khi nạp catalog mới).

3. **Thiếu Metadata Khán giả trong Gói Export (`tests/test_portable_exports.py` — 1 lỗi):**
   - `test_exam_portable_zip_has_manifest_and_no_solution_for_student`
   - **Nguyên nhân:** File `manifest.json` trong bundle/zip thiếu trường bắt buộc `'audience': 'student'` (hoặc `'teacher'`).

4. **Nguyên tắc An Toàn Fail-Closed khi có Macro Lạ (`tests/test_stabilization.py` — 1 lỗi):**
   - `test_student_unknown_macro_rejected_instead_of_exposing_answer`
   - **Nguyên nhân:** Khi gặp macro chưa được chứng nhận (`\MyAnswer{private}`), hàm `ExamService.content` vô tình bắt ngoại lệ `ValueError` khiến hệ thống tiếp tục xuất mà không cảnh báo lỗi chặn (fail-closed).

---

## 3. Bảng Mapping Luồng Nghiệp Vụ Ra Đề & Xuất Bản

```
[1. CHỌN CÂU HỎI]
  ├── Thủ công: manual_ids = [q1, q2, ...]
  └── Ma trận: Bipartite matching không chồng lặp (scope, type, level, count)
         │
         ▼
[2. SINH SNAPSHOT & XÁO ĐÁP ÁN (ExamService.generate)]
  ├── Validate & parsed(latex_source)
  ├── shuffled_question: Xáo hoán vị A, B, C, D (giữ nguyên \True ở vị trí mới)
  ├── Asset discovery: Gom toàn bộ ảnh \includegraphics vào snapshot['assets']
  ├── Duplicate detection: So sánh chuỗi kiểm tra trùng lặp
  └── Lưu snapshot vào SQLite: exam_papers, exam_versions, exam_questions
         │
         ▼
[3. XỬ LÝ NỘI DUNG TÀI LIỆU (ExamService.content)]
  ├── CHẾ ĐỘ HỌC SINH (solutions=False):
  │     ├── Scanner/Group-based stripping: Loại bỏ sạch \True, \loigiai, \hdan, \shortans
  │     └── FAIL-CLOSED: Bất kỳ macro lạ/không chứng nhận -> Ném ValueError lập tức
  ├── CHẾ ĐỘ GIÁO VIÊN (solutions=True):
  │     └── Giữ nguyên source, chèn \loigiai{solution} nếu chưa có
  └── CHẾ ĐỘ ĐÁP ÁN (answer_only=True):
        └── Trích xuất mã đáp án chuẩn A, B, C, D
         │
         ▼
[4. ĐÓNG GÓI VÀ BIÊN DỊCH XUẤT BẢN]
  ├── ① File PDF:
  │     └── Gọi Compiler.compile -> pdflatex chạy trong thư mục tạm có TEXINPUTS
  ├── ② Thư mục Bundle tự trị:
  │     ├── Sao chép MAPClass.cls, Packages/ex_test.sty
  │     ├── Thư mục assets/ chứa ảnh câu hỏi
  │     ├── Script bien-dich.bat & HUONG_DAN_BIEN_DICH.txt
  │     └── manifest.json chứa sha256 và audience
  ├── ③ Gói nén Portable ZIP:
  │     └── Nén toàn bộ bundle kèm main.tex alias cho Overleaf
  └── ④ File TeX Standalone:
        └── Nhúng Preamble tự trị
```

---

## 4. Kiểm Toán Module & Rủi Ro Cần Xử Lý Trước Khi Sang Phase Kế Tiếp

| Module | Hiện trạng | Rủi ro phát hiện | Mức độ |
| :--- | :--- | :--- | :--- |
| `application/exams.py` | Đã hỗ trợ `export_bundle` và `export_zip` | Nuốt lỗi `except Exception: pass` trong copy dependencies; `manifest.json` thiếu `audience`; Fallback regex làm hỏng lồng ngoặc; chưa fail-closed chuẩn | **P0** (Xử lý tại Phase B & C) |
| `application/lessons.py` | `student_source` bóc tách lời giải | Cần bao phủ đủ các macro định dạng chuẩn bài thi Bộ GD (`\haidong`, `\bondong`, `\loai`, `\dapan`) | **P0** (Xử lý tại Phase B) |
| `parsing/latex.py` | Bộ phân tích `commands`, `group`, `ParsedQuestion` | Cần bổ sung test case ngoặc lồng 3–5 tầng, comment chứa dấu ngoặc, escaped braces | **P0** (Xử lý tại Phase B) |
| `preview/compiler.py` | Chạy `pdflatex` với cache SHA-256 | Cần đảm bảo xử lý triệt để file lock trên Windows khi cleanup thư mục tạm | **P0** (Đã giải quyết bằng `ignore_cleanup_errors`) |
| `ui/main_window.py` | Cấu trúc Shell và Quản lý Pages | `refresh_curriculum_menu` đang để trống làm gãy 9 tests điều hướng CSDL | **P1** (Khôi phục logic menu không gây rối UI) |
| `ui/exam_dialog.py` | Studio xuất bản Bước 5 | Cần hỗ trợ đa luồng xuất không làm đơ UI, báo cáo lỗi biên dịch chi tiết | **P1** (Xử lý tại Phase D) |

---

## 5. Kế Hoạch Triển Khai Tiếp Theo

1. **Khôi phục ngay tính đúng đắn của Menu CSDL** trong `main_window.py` để đưa test suite về trạng thái xanh.
2. **Triển khai Phase B (P0):** Hoàn thiện bảo mật xuất đề học sinh, loại bỏ hoàn toàn regex ngoặc, bảo đảm nguyên tắc fail-closed, viết regression test chuyên sâu.
3. **Triển khai Phase C (P0):** Hoàn thiện portable bundle/zip, loại bỏ nuốt lỗi, kiểm tra toàn vẹn hash và staging atomic finalize.
4. **Triển khai Phase D → H** tuần tự theo đúng chỉ thị.
