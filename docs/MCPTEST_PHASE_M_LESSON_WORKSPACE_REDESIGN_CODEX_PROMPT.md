# MCPTest — PHASE M: TÁI THIẾT KẾ TAB SOẠN BÀI GIẢNG

> Prompt triển khai trực tiếp cho Codex trong VS Code. Repository: https://github.com/letrieubavuong/MCPTest. Mục tiêu: làm cho tab **Bài giảng** thực sự hữu dụng với giáo viên Toán 6–12, KHTN 6–9, Vật lí 10–12; không chỉ đổi màu, thêm nút hoặc ghép câu hỏi thành đề.

## 0. Quy tắc làm việc bắt buộc

1. Đọc mã nguồn hiện tại trước khi sửa: `src/latex_question_studio/ui/lesson_page.py`, `ui/lesson_dialog.py`, `ui/wysiwyg.py`, `application/lessons.py`, `application/assets.py`, `preview/compiler.py`, persistence và toàn bộ `tests/test_lesson*.py`, `tests/test_phase_g_lesson_editor.py`.
2. Đọc `docs/18_LESSON_AUTHORING_SPEC.md`, `docs/19_LESSON_IMPLEMENTATION_REPORT.md`, `docs/LESSON_FILE_MODEL_REPORT.md`, `docs/LESSON_TAB_IMPLEMENTATION_REPORT.md`; phân biệt tính năng có thật với tính năng mới được mô tả.
3. Chụp màn hình/ghi lại luồng thao tác thực tế trước khi sửa, lập danh sách vấn đề và regression baseline. Không tuyên bố UI đã tốt chỉ từ unit test.
4. Giữ tương thích **Windows + Python + PySide6 + SQLite + pdfLaTeX**, `MAPClass.cls`, `ex_test.sty`, TikZ, `\includegraphics`, `\immini`. Không yêu cầu XeLaTeX, LuaLaTeX, cloud, API trả phí.
5. **Không phá dữ liệu bài giảng cũ.** Giữ nguyên hoặc migration có backup, rollback, kiểm thử mở bản cũ và tái xuất; bảo toàn revision, pinned questions, file manifest (`LyThuyet`, `DangToan`, `BTVD`), assets, export snapshots.
6. Không tự động sửa macro TeX không hiểu; phải bảo toàn source và báo cần kiểm tra. Không dùng WYSIWYG làm mất code TikZ hoặc môi trường tùy chỉnh.
7. Làm từng phase, test, commit/push và báo SHA. Không đánh dấu hoàn tất nếu chưa chạy thử thao tác giáo viên thực tế.

## 1. Vấn đề được xác nhận từ audit repo

- `lesson_page.py` đang dùng ba vùng: outline bên trái, giữa là tab **Soạn thảo/Xem trước PDF**, ngân hàng câu hỏi cố định bên phải. Giáo viên phải chuyển tab để soạn và xem; panel ngân hàng chiếm chỗ khi không dùng.
- Có hai lớp điều hướng cạnh tranh: cây block và file nguồn `LyThuyet/DangToan/BTVD`; người dùng phải hiểu cả hai để sửa một bài.
- Tạo bài từ mẫu chủ yếu sinh tiêu đề/khối trống; chưa có luồng viết nhanh lý thuyết → phương pháp → ví dụ → luyện tập.
- Có `VisualLatexEditor` nhưng chưa chứng minh round-trip với macro phức tạp/TikZ; không được coi là editor trực quan hoàn thiện.
- Đặc tả `docs/18_LESSON_AUTHORING_SPEC.md` yêu cầu import tài liệu TeX cũ, drag/drop, cross-reference; báo cáo triển khai trước đây xác nhận chưa hoàn thiện.
- Bài giảng cần tiến trình sư phạm; không áp cấu trúc đề thi Phase K cho mọi bài giảng.

## 2. Định nghĩa sản phẩm đích

### 2.1. Danh sách bài giảng

- Danh sách rõ ràng: tiêu đề, môn, lớp, chương/chủ đề, cập nhật, trạng thái nháp/đã phát hành; tìm kiếm/lọc/sắp xếp.
- CTA chính **Tạo bài giảng**, thứ cấp **Nhập bài giảng `.tex`**, **Nhân bản**, **Mở từ mẫu**.
- Form tạo nhanh tối thiểu: tên bài, môn/lớp, mẫu (Trống / Lý thuyết / Chuyên đề dạng toán / Phiếu luyện tập). Tùy chọn nâng cao thu gọn; không bắt người dùng cấu hình quá nhiều.

### 2.2. Workspace soạn bài thống nhất

- **Thanh đầu:** breadcrumb, tên bài, trạng thái lưu, Hoàn tác/Làm lại, Chèn nội dung, Chèn từ ngân hàng, Xem trước, Xuất.
- **Cột trái (thu gọn được):** *Mục lục bài giảng* theo cây sư phạm: Lý thuyết → Dạng toán → Phương pháp → Ví dụ → Bài tập. File nguồn nội bộ phải ẩn khỏi trải nghiệm mặc định; cung cấp chế độ **Tệp nguồn (nâng cao)** riêng khi cần. Không xóa mô hình file trong persistence.
- **Cột giữa:** biên tập khối được chọn. Tab `Nội dung` / `Mã LaTeX` khi có thể round-trip an toàn; nếu không, chỉ dùng mã nguồn kèm toolbar chèn macro. Có breadcrumb của khối, thuộc tính ngữ cảnh, đánh dấu lỗi ngay tại khối.
- **Cột phải (tùy chọn):** preview PDF cùng lúc với editor, có splitter, zoom, chọn khối/toàn bài, học sinh/giáo viên; tự động cập nhật có debounce hợp lý, nút compile thủ công và log lỗi. Khi cửa sổ nhỏ, có thể chuyển sang tab preview để không ép chiều rộng.
- **Ngân hàng câu hỏi:** mở dưới dạng drawer/panel tạm thời khi bấm **Chèn từ ngân hàng**; không luôn chiếm 1/3 màn hình. Giữ bộ lọc và selection trong phiên.
- Phong cách **sáng, hiện đại**, tương phản tốt, chữ dễ đọc, không nhồi biểu tượng hoặc dark panel không đồng bộ; có trạng thái trống, lỗi, đang lưu, đang compile.

### 2.3. Các khối biên tập

- Đoạn lý thuyết/TeX tự do; Định nghĩa/Định lý/Công thức/Chú ý; Dạng toán/Phương pháp; Ví dụ có đề và hướng dẫn/lời giải; Nhóm bài tập; Hình ảnh/TikZ; Ngắt trang; Nhóm/tiêu đề.
- Toolbar theo ngữ cảnh: công thức inline/display, phân số, căn, chỉ số, bảng, danh sách, `\begin{ex}`, `\loigiai`, chèn ảnh, chèn TikZ, chèn từ ngân hàng.
- Thao tác thêm khối trước/sau/con, nhân bản, di chuyển bằng nút và drag/drop **đổi cả cha lẫn thứ tự** nếu khả thi; giữ cây hợp lệ, không vòng lặp; có undo/redo.
- Chế độ source phải giữ nguyên nội dung người dùng viết; không tự động escape toàn bộ TeX thành văn bản.

## 3. Nghiệp vụ cốt lõi phải hoàn thiện

### A. Tạo và viết bài giảng nhanh

Một giáo viên phải làm được luồng sau trong một workspace:
1. Tạo bài `Khúc xạ ánh sáng – KHTN 9`.
2. Thêm lý thuyết về khúc xạ, công thức và một hình TikZ.
3. Thêm `Dạng 1: Nhận biết tia khúc xạ`, phương pháp giải, hai ví dụ có lời giải.
4. Thêm nhóm 6 câu luyện tập từ ngân hàng; thêm bài tập vận dụng/tự học.
5. Preview và xuất PDF học sinh/giáo viên + nguồn `.tex` di động.

Không bắt giáo viên tự quản lý file `theory.tex`/`dang-*.tex` để hoàn tất luồng này.

### B. Chèn câu từ ngân hàng

- Search, filter môn/lớp/chủ đề/dạng/loại/nhận thức, xem thumbnail/PDF, tick nhiều câu, chỉ định vai trò `Ví dụ`, `Luyện tập`, `Vận dụng`, `Về nhà`, chọn vị trí chèn chính xác.
- Pin question ID + revision + source snapshot + assets; không tự thay câu khi ngân hàng thay đổi. Cho override cục bộ không sửa ngân hàng; hiển thị diff nếu nguồn có revision mới.
- Giữ nguyên thứ tự được chọn, không xáo câu/đáp án mặc định. Cảnh báo trùng, cho phép lặp có chủ đích. Trích lọc theo số lượng phải có preview và báo thiếu nguồn.
- Hỗ trợ MCQ, TF, short answer, essay, hình/TikZ, `\immini`, lời giải; không để mất tài nguyên khi chuyển máy.

### C. Preview, compile, lỗi và xuất

- Preview khối hoặc toàn bài; chọn bản học sinh/giáo viên, PDF nhiều trang, zoom, trang trước/sau, hủy compile; không khóa UI trong quá trình pdfLaTeX.
- Khi lỗi TeX: hiển thị lỗi dễ hiểu, file/dòng và **định vị khối tương ứng**, có log gốc; không báo thành công nếu không có PDF hợp lệ.
- Chính sách theo từng khối: hiện đầy đủ, chỉ đề, gợi ý, khoảng trống, chỉ giáo viên. Ví dụ mẫu có thể công khai lời giải; ghi chú riêng giáo viên tuyệt đối không có trong nguồn học sinh.
- Xuất `main.tex` + dependencies/assets + PDF + manifest, thư mục ZIP di động, không có đường dẫn tuyệt đối tới máy soạn; kiểm tra compile lại từ thư mục khác.
- Bản đã phát hành bất biến, có revision/snapshot; thay đổi bản nháp không sửa bản đã xuất.

### D. Nhập `.tex` bài giảng cũ

- Hỗ trợ chọn file `.tex` và dependency cùng thư mục, phân tích `\section`, `\subsection`, nội dung tự do, `\begin{ex}`, `\includegraphics`, TikZ, `\input` (giới hạn an toàn), macro tùy chỉnh.
- Phần parser chưa hiểu phải đưa vào **Raw TeX block** giữ nguyên source và vị trí; không bỏ lý thuyết ngoài `ex`.
- Có màn hình preview cấu trúc, kiểm tra asset, xác nhận trước khi nhập; so sánh coverage số đoạn/byte hoặc AST node để phát hiện mất nội dung.
- Đối với macro phụ thuộc package chưa có, giữ nguyên source và cảnh báo; không âm thầm sửa.

### E. Autosave và an toàn dữ liệu

- Debounce autosave, dirty state rõ ràng, Save/Discard/Cancel khi đóng; Ctrl+S; undo/redo, recovery sau crash; không ghi đè chỉnh sửa khi chọn khối/chuyển bài.
- Test concurrency, cancellation, stale preview, SQLite transaction, migration/backup/restore, unicode tiếng Việt.

## 4. Kế hoạch triển khai

### M0 — Audit + đo baseline
- Ghi sơ đồ luồng hiện tại, ảnh chụp màn hình, các thao tác bất tiện, các test cũ; đo thời gian mở bài, đổi khối, gõ, preview, export; lập `docs/PHASE_M_BASELINE.md`.
- Lập bảng mapping model cũ → workspace mới, xác định migration cần thiết. Không viết lại persistence khi chưa chứng minh cần.

### M1 — Thiết kế UI/UX và skeleton
- Hoàn thiện màn danh sách + workspace 2/3 cột responsive; outline thống nhất, file source advanced, bank drawer; trạng thái empty/loading/error; light theme.
- Chụp screenshot các trạng thái ở 1366×768 và 1920×1080. Tránh cắt nút, scroll lồng khó dùng.

### M2 — Editor sư phạm
- Toolbar chèn khối, chỉnh cấu trúc, di chuyển, nhân bản, undo/redo; editor TeX an toàn; kiểm thử round-trip nếu có visual mode.
- Tạo 4 mẫu thực tế: Lý thuyết, Chuyên đề dạng toán, Phiếu bài tập, Bài giảng trống. Mẫu phải chứa gợi ý cấu trúc hữu ích nhưng không tự bịa nội dung kiến thức.

### M3 — Bank picker + asset pipeline
- Drawer chọn nhiều câu, pin revision, override, role, duplicate warning, selection recipe; import ảnh/TikZ và đảm bảo portability.

### M4 — Preview + export an toàn
- PDF side-by-side, log lỗi định vị khối, teacher/student policy, ZIP portable, snapshot và bảo mật đáp án.

### M5 — Import TeX legacy
- Nhập bài có lý thuyết ngoài `ex`, macro tùy chỉnh, `\input`, ảnh/TikZ; raw fallback và báo coverage. Không yêu cầu hỗ trợ mọi macro ngay lập tức, nhưng tuyệt đối không mất nội dung.

### M6 — E2E giáo viên + Windows RC
- Chạy **toàn bộ** pytest, không chỉ test mới; kiểm thử EXE Windows với TeX Live/pdfLaTeX thật; kiểm tra dữ liệu bài giảng trước nâng cấp, sau nâng cấp, backup/restore.
- E2E tối thiểu 3 bài: KHTN 9 Khúc xạ ánh sáng (TikZ), Toán 8 đa thức (công thức + nhiều dạng toán), Vật lí 10 chuyển động (đồ thị TikZ, nhóm bài tập); xuất bản học sinh/giáo viên và compile ZIP ở thư mục khác.
- Stress 100+ khối, 200+ câu được tham chiếu; UI không đứng khi thao tác, autosave không mất dữ liệu. Ghi latency p50/p95/p99, không tự gọi event-dispatch time là FPS.

## 5. Tiêu chí nghiệm thu (không được nới)

1. Giáo viên tạo → soạn → chèn câu → xem PDF → xuất bản hoàn chỉnh **không cần thao tác trực tiếp với manifest hoặc file source nội bộ**.
2. Có thể xem editor và PDF **cùng lúc** trên màn hình đủ rộng; panel ngân hàng chỉ mở khi cần.
3. Đóng/mở bài giữ đúng nội dung, cây, thứ tự, pinned revision, ảnh, ghi chú và trạng thái lưu.
4. Nội dung `\choice`, `\choiceTF`, `\shortans`, tự luận và TikZ không bị biến đổi ngoài ý muốn; không xáo đáp án trong bài giảng.
5. PDF học sinh không chứa ghi chú riêng hoặc đáp án được đặt ẩn, kể cả trong `.tex` và file phụ.
6. Nhập `.tex` cũ không làm mất đoạn lý thuyết ngoài câu hỏi; raw fallback giữ nguyên macro lạ.
7. Gói xuất portable compile được bằng pdfLaTeX trên Windows; không tham chiếu đường dẫn tuyệt đối máy soạn.
8. Không làm mất bài cũ khi migration/restore; regression toàn bộ dự án PASS hoặc nêu chính xác lỗi còn lại.
9. Chụp screenshot trước/sau, báo cáo thao tác thực tế; không chỉ báo số test.

## 6. Deliverables và báo cáo

- Code + tests + migration (nếu cần), commit/push theo M0–M6.
- `docs/PHASE_M_BASELINE.md` và `docs/PHASE_M_LESSON_WORKSPACE_REPORT.md`.
- Screenshot UI desktop và video/GIF ngắn (nếu công cụ có thể), logs biên dịch thực, danh sách case import, thời gian thao tác.
- Báo cáo theo bảng: yêu cầu, file sửa, test, kết quả, bằng chứng, tồn đọng P0/P1/P2; commit SHA cuối cùng.
- Không ghi "hoàn thành 100%" nếu còn tính năng giả lập, thiếu kiểm thử thực tế, mất dữ liệu hoặc chỉ đổi giao diện.

## 7. Chỉ dẫn thực thi cuối

Bắt đầu M0 ngay. Sau đó triển khai M1–M6 theo thứ tự; không chờ xác nhận cho các quyết định kỹ thuật thông thường, nhưng **không tự thay đổi định dạng bài giảng/semantics hoặc xóa dữ liệu cũ**. Ưu tiên trải nghiệm giáo viên và tính ổn định hơn số lượng nút/tính năng. Sau mỗi phase, chạy test liên quan và commit. Cuối cùng chạy regression toàn bộ, build/smoke Windows, push và gửi báo cáo kèm SHA.
