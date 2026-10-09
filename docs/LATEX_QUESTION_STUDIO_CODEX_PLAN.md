# LATEX QUESTION STUDIO — KẾ HOẠCH VÀ ĐẶC TẢ CHO CODEX

> Trạng thái: Bản đặc tả ban đầu. **Chưa khảo sát được mã nguồn local MCPTest2020.** Codex phải hoàn thành Phase 00 trước khi chốt thiết kế và viết mã.

## 1. Mục tiêu

Xây dựng ứng dụng desktop Windows quản lý ngân hàng câu hỏi LaTeX bằng **Python**, giao diện và trải nghiệm tương tự **Visual Studio Code**. Ứng dụng phục vụ nhập hàng loạt, phân loại, chỉnh sửa, xem trước, tìm kiếm, phát hiện câu trùng, tạo đề và xuất LaTeX/PDF.

**Dự án tham khảo (chỉ đọc ở Phase 00):**

```text
D:\OneDrive\B - MCPTEST 2020\MCPTest2020
```

Không được tự nhận đã khảo sát dự án khi chưa truy cập và đọc mã nguồn thực tế.

## 2. Yêu cầu cốt lõi

### 2.1. Ngân hàng câu hỏi
- Tổ chức theo môn, khối, chương, bài, chủ đề, nhãn, nguồn, mức độ nhận thức (nhận biết, thông hiểu, vận dụng, vận dụng cao).
- Hỗ trợ trắc nghiệm 4 phương án, đúng/sai, trả lời ngắn, tự luận; cho phép mở rộng theo cấu trúc thực tế từ MCPTest2020.
- Lưu nguyên vẹn LaTeX gốc; quản lý đáp án, lời giải, tài nguyên, lịch sử phiên bản.
- Câu hỏi là thực thể độc lập với file nhập; ghi lại nguồn file và đợt nhập.

### 2.2. Nhập dữ liệu
- Nhập một file `.tex`, nhiều file hoặc cả thư mục, có tiến trình và khả năng hủy.
- Tách nhiều môi trường `ex` trong cùng file, xử lý ngoặc lồng nhau và macro riêng.
- Nhận biết `\choice`, `\choiceTF`, `\choiceTFt`, `\shortans`, `\loigiai`, `\True`, `listEX`, `tikzpicture`, `\includegraphics` khi hiện diện.
- Không chỉ dùng regex để parse LaTeX: cần tokenizer/scanner có nhận biết comment, escaped brace, nested brace và environment.
- Câu không parse được phải đưa vào hàng chờ xử lý, lưu nguyên văn và báo lỗi có vị trí; không âm thầm bỏ qua.
- Có chế độ xem trước kết quả nhập, thống kê câu mới/trùng/lỗi trước khi ghi DB.

### 2.3. Biên tập và preview
- Editor có syntax highlighting, line number, tìm/thay thế, undo/redo, tab, phím tắt, tự hoàn thành các macro phổ biến.
- Preview **một câu được chọn**; giữ bố cục LaTeX thực tế, kể cả TikZ và ảnh.
- pdfLaTeX là engine mặc định, tương thích `MAPClass.cls`, `ex_test.sty` và các phụ thuộc đã xác minh.
- Cache preview theo hash của source + preamble + assets + engine/config. Khi cache còn hợp lệ phải hiển thị ngay, không biên dịch lại.
- Biên dịch trong tiến trình riêng với timeout, hủy tác vụ, log và báo lỗi theo dòng; không khóa giao diện.
- Dùng tài liệu standalone/tối giản khi tương thích; nếu không, có fallback được kiểm thử. Không giả định mọi câu đều biên dịch standalone thành công.

### 2.4. Tìm kiếm và tạo đề
- SQLite FTS5 cho văn bản và metadata; bộ lọc theo môn/lớp/chương/bài/loại/mức độ/nhãn.
- Phát hiện trùng chính xác theo nội dung chuẩn hóa; gần trùng chỉ gợi ý, không tự xóa.
- Tạo đề thủ công và theo ma trận; chọn câu không lặp; xáo thứ tự câu và phương án nhưng bảo toàn đáp án `\True`.
- Xuất `.tex`, PDF, đáp án/lời giải; ghi nhận lịch sử tạo đề và danh sách ID câu.

## 3. Giao diện kiểu VS Code

- **Activity Bar:** Thư viện, tìm kiếm, nhập dữ liệu, đề thi, cài đặt.
- **Explorer:** Cây môn/khối/chương/bài; số lượng câu; menu chuột phải.
- **Main Editor:** Nhiều tab câu hỏi; trạng thái chỉnh sửa chưa lưu; mở trực tiếp nguồn LaTeX.
- **Preview Pane:** Bên phải hoặc phía dưới, có thể dock/resize; hiển thị đúng câu đang chọn.
- **Bottom Panel:** Log biên dịch, lỗi parser, tác vụ nền, terminal tùy chọn.
- **Status Bar:** Trạng thái lưu, loại câu, engine, số câu, tiến trình.
- Dark/Light mode, phím tắt, lưu/khôi phục layout và tab mở gần nhất.
- Giao diện tiếng Việt; dùng Qt Model/View và lazy loading để tránh lag khi có nhiều câu.

## 4. Công nghệ đề xuất

| Hạng mục | Lựa chọn |
|---|---|
| Runtime | Python 3.12+ |
| UI | PySide6 / Qt 6 |
| Editor | QScintilla nếu phù hợp license và đóng gói; nếu không QPlainTextEdit tùy biến |
| DB | SQLite + SQLAlchemy + Alembic hoặc migration có kiểm soát |
| Search | SQLite FTS5 |
| Preview | pdfLaTeX + PyMuPDF |
| Background jobs | QProcess, QThreadPool, worker queue |
| Tests | pytest, pytest-qt |
| Packaging | PyInstaller Windows |

Không bắt buộc Internet cho các tính năng chính. TeX distribution là phụ thuộc ngoài cần phát hiện và hướng dẫn cấu hình.

## 5. Mô hình dữ liệu dự kiến (chờ Phase 00 xác minh)

- `subjects`, `grades`, `chapters`, `lessons`, `topics`
- `questions`: id, type, latex_source, solution, answer_data, difficulty, cognitive_level, source_hash, timestamps
- `question_tags`, `tags`, `question_assets`, `assets`
- `source_files`, `import_batches`, `import_items`
- `question_revisions`, `question_duplicates`
- `exam_papers`, `exam_questions`, `exam_versions`
- `compilation_cache`, `app_settings`

Lưu source LaTeX trong DB; file ảnh và tài nguyên ở thư mục quản lý theo hash/đường dẫn tương đối, không mặc định nhúng base64 vào SQLite. Đảm bảo khóa ngoại, transaction, index và migration.

## 6. Luồng nghiệp vụ

1. Người dùng chọn file/thư mục LaTeX.
2. Hệ thống scan và phân tích câu hỏi, liên kết assets.
3. Hiển thị preview nhập, lỗi, số câu và đề xuất phân loại.
4. Chuẩn hóa để so trùng; lưu bản gốc bất biến.
5. Ghi dữ liệu bằng transaction; có log và rollback khi lỗi.
6. Người dùng tìm, chọn, chỉnh sửa câu; preview từ cache hoặc biên dịch nền.
7. Chọn câu tạo đề; kiểm tra tính hợp lệ đáp án và xuất LaTeX/PDF.

## 7. Các phase triển khai

### Phase 00 — Khảo sát MCPTest2020 (BẮT BUỘC)
**Việc cần làm:**
1. Kiểm tra đường dẫn tồn tại; lập cây thư mục và nhận diện stack.
2. Đọc source để lập bản đồ module, class, chức năng và các entrypoint.
3. Xác định schema, format dữ liệu, quy trình nhập/xuất, tạo đề, đáp án, lời giải.
4. Tìm các mẫu LaTeX thực tế, macro tùy chỉnh, phụ thuộc `.cls`/`.sty`, TikZ và ảnh.
5. Xác định nghiệp vụ kế thừa, viết lại, chưa rõ; đối chiếu đặc tả này.
6. Lập migration mapping từ dữ liệu cũ sang schema đề xuất; không thay đổi dữ liệu gốc.

**Đầu ra:**
- `docs/00_MCPTEST_AUDIT.md`
- `docs/01_BUSINESS_REQUIREMENTS.md`
- `docs/02_DATABASE_DESIGN.md`
- `docs/03_PYTHON_ARCHITECTURE.md`
- `docs/04_UI_UX_SPEC.md`
- `docs/05_IMPLEMENTATION_PHASES.md`
- `docs/06_MIGRATION_STRATEGY.md`

**Nghiệm thu:** Mọi nhận định về MCPTest2020 dẫn nguồn file/class/method/schema thực tế; liệt kê điều chưa xác minh. **Không viết ứng dụng trong Phase 00.**

### Phase 01 — Skeleton và hạ tầng
- Khởi tạo package, cấu hình, logging, DB migrations, dependency injection đơn giản, test CI local.
- Cửa sổ PySide6 chạy được; DB khởi tạo và mở lại an toàn.
- **Nghiệm thu:** smoke test mở app, CRUD mẫu, migration và pytest pass.

### Phase 02 — VS Code shell
- Activity Bar, Explorer, tab editor, Preview dock, Bottom Panel, Status Bar.
- Dock resize, theme, command shortcuts, lưu layout.
- **Nghiệm thu:** chuyển màn, mở/đóng tab, khôi phục layout, không crash.

### Phase 03 — LaTeX parser và import
- Scanner/tokenizer, parser ex_test, asset resolver, import batch, preview lỗi.
- Corpus test lấy từ MCPTest2020 và mẫu do người dùng cung cấp.
- **Nghiệm thu:** round-trip bảo toàn source; không mất câu im lặng; báo lỗi đúng vị trí.

### Phase 04 — Thư viện và phân loại
- CRUD, tree hierarchy, metadata, revision, gắn nhãn, backup cơ bản.
- **Nghiệm thu:** quản lý và khôi phục dữ liệu đúng sau khởi động lại.

### Phase 05 — Editor, pdfLaTeX và cache preview
- Syntax highlight, snippets, compile worker, PDF-to-image, cache invalidation.
- **Nghiệm thu:** câu toán, trắc nghiệm, TikZ, includegraphics được preview nếu dependency hợp lệ; lỗi được báo, UI không treo.

### Phase 06 — Search và dedup
- FTS5, lọc nâng cao, hash chuẩn hóa, phát hiện gần trùng và thao tác hợp nhất có xác nhận.
- **Nghiệm thu:** tìm đúng dữ liệu, không xóa câu tự động.

### Phase 07 — Đề thi
- Chọn câu, ma trận, xáo đáp án, kiểm tra `\True`, xuất đề/đáp án/lời giải.
- **Nghiệm thu:** đối chiếu đáp án trước/sau xáo; file PDF compile được trên corpus kiểm thử.

### Phase 08 — Hiệu năng và ổn định
- Lazy load, pagination, background queue, giới hạn cache, benchmark import/search/preview.
- **Nghiệm thu:** benchmark bằng bộ dữ liệu lớn thực tế; không khóa UI khi import hoặc compile.

### Phase 09 — EXE và bàn giao
- PyInstaller, cấu hình pdfLaTeX, backup/restore, tài liệu sử dụng và troubleshooting.
- **Nghiệm thu:** chạy EXE trên Windows sạch có TeX distribution được cấu hình; không cần Python cài riêng.

## 8. Quy tắc làm việc của Codex

1. **Phase 00 chỉ đọc** đường dẫn MCPTest2020; tuyệt đối không sửa/xóa/move file tại đó.
2. Làm từng phase, không tự động chuyển phase tiếp theo khi chưa có kết quả nghiệm thu.
3. Mỗi phase phải báo cáo: file thay đổi, kiến trúc, test đã chạy, kết quả, vấn đề tồn tại, hướng xử lý.
4. Không giả định cú pháp `MAPClass.cls`/`ex_test.sty` trước khi đọc bản thực tế.
5. Mọi chuyển đổi câu hỏi phải bảo toàn LaTeX gốc, đáp án, lời giải, TikZ và assets.
6. Không tự động xóa câu trùng, không ghi đè dữ liệu nguồn.
7. Ưu tiên tính đúng đắn dữ liệu và trải nghiệm editor trước các tính năng phụ.
8. Tất cả thay đổi database phải có migration và phương án backup/rollback.

## 9. Prompt khởi động Codex

> Hãy đọc toàn bộ file `LATEX_QUESTION_STUDIO_CODEX_PLAN.md`. Thực hiện **chỉ Phase 00**: khảo sát read-only dự án `D:\OneDrive\B - MCPTEST 2020\MCPTest2020`, lập đủ 7 tài liệu trong `docs/`, chỉ rõ chứng cứ source cho mỗi kết luận. Nếu không truy cập được đường dẫn, dừng và báo lỗi, không suy đoán. Không sửa dự án tham khảo, không bắt đầu code Phase 01. Cuối cùng tóm tắt nghiệp vụ nên kế thừa, rủi ro migration và các quyết định cần người dùng xác nhận.
