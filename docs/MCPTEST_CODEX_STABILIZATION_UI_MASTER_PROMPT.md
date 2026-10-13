# MCPTest — MASTER PROMPT CHO CODEX

## Vai trò và mục tiêu
Bạn là kỹ sư trưởng Python/PySide6, LaTeX/ex_test/MAPClass, SQLite và UX ứng dụng giáo dục. Làm việc trực tiếp trong repository MCPTest hiện tại. Mục tiêu: **ổn định nghiệp vụ xuất đề thi, hoàn thiện quản lý câu hỏi, nâng chất lượng UI/UX, tối ưu preview** mà không làm hỏng dữ liệu cũ.

**Lưu ý:** Những nhận định dưới đây xuất phát từ đợt review commit `69be3fa` (13/10/2026). Trước khi sửa, phải `git fetch`, kiểm tra HEAD và đọc lại mã hiện tại; nếu đã có thay đổi thì đối chiếu thay vì áp dụng máy móc. Không reset, force-push, xóa thay đổi người dùng, hay ghi đè dữ liệu.

## Nguyên tắc bất biến
1. MCPTest là ứng dụng **quản lý ngân hàng câu hỏi, ra đề thi, soạn bài giảng**, không phải IDE. VS Code chỉ tham khảo bảng màu sáng/tối, icon, tương phản; không sao chép bố cục IDE.
2. Giữ Python, PySide6, SQLite, `ex_test`, `MAPClass`, pipeline pdfLaTeX và tài nguyên LaTeX gốc. Không chuyển kiến trúc sang web app.
3. Bảo toàn dữ liệu và backward compatibility; migration phải có rollback/backup. Không tự sửa nội dung câu hỏi gốc trong DB khi xuất đề.
4. Không báo thành công nếu thao tác thiếu dependency, không biên dịch được, hoặc có nguy cơ lộ đáp án.
5. Mỗi phase phải có test tự động, kiểm thử thủ công với dữ liệu thực, ảnh chụp UI nếu có thay đổi giao diện, báo cáo và commit riêng.
6. Tránh mở rộng phạm vi ngoài yêu cầu. Không bổ sung nhiều nút, toolbar hoặc QGroupBox vô ích.

## Phase A — Baseline và kiểm toán (bắt buộc trước khi sửa)
- Ghi nhận HEAD, branch, working tree, cấu trúc module, phiên bản DB, test hiện có.
- Chạy test suite phù hợp, ghi rõ PASS/FAIL/SKIP và lý do; xác định có pdfLaTeX, MAPClass.cls, ex_test.sty hay không.
- Lập bảng mapping luồng: chọn câu → sinh snapshot → xáo đáp án → xuất học sinh/giáo viên/đáp án → PDF/TeX/ZIP.
- Đọc và kiểm tra kỹ `application/exams.py`, `application/lessons.py`, `parsing/latex.py`, `preview/compiler.py`, `ui/exam_dialog.py`, `ui/pages/library.py`, `ui/question_editor_dialog.py`, `ui/main_window.py`.
- Viết `docs/PHASE_A_BASELINE.md`, nêu lỗi tái hiện được, mức độ, test đang thiếu. Không kết luận bug chỉ từ suy đoán.

## Phase B — An toàn xuất đề học sinh (P0)
- Review toàn bộ `student_source`, logic tách `\True`, `\loigiai`, `\hdan`, `\shortans` và fallback trong `application/exams.py`.
- Không dùng regex không cân bằng ngoặc để xóa lời giải. Sử dụng scanner/parser có xử lý ngoặc lồng nhau, comment, dấu escape, optional args, môi trường liên quan và macro tùy chỉnh đã được hỗ trợ.
- Khi parser gặp lỗi hoặc không xác minh được nội dung học sinh đã loại sạch đáp án/lời giải: **fail closed**. Trả lỗi rõ câu hỏi ID, macro, vị trí, gợi ý sửa; không xuất bản học sinh âm thầm.
- Phân biệt chế độ học sinh, giáo viên, đáp án. Không để `\True` hoặc nội dung giải lộ qua các đường xuất khác nhau.
- Bảo đảm không mất nội dung đề hợp lệ, không xóa nhầm hình nằm trong thân đề. Tài nguyên chỉ xuất hiện trong lời giải không được đưa vào bundle học sinh nếu không cần.
- Tạo regression tests: `\loigiai` lồng 3–5 tầng, nhiều `\choice`, `\choiceTF`, `\shortans`, `\hdan`, macro tùy chỉnh, ngoặc lỗi, comment, escaped braces, nhiều câu liên tiếp, ảnh lời giải, `\begin{ex}`/`\begin{bt}`.
- So sánh TeX và PDF xuất ra: đề học sinh không chứa marker bí mật/đáp án; đề giáo viên giữ đủ lời giải. Không chỉ test chuỗi, phải kiểm thử biên dịch nếu môi trường hỗ trợ.

## Phase C — Portable export đáng tin cậy (P0)
- Loại bỏ `except Exception: pass` trong `copy_class_dependencies` và các điểm nuốt lỗi quan trọng trên đường xuất.
- Kiểm tra trước khi export: đường dẫn class, package, preamble, assets, quyền ghi, engine; kết quả có `ok`, danh sách file, lỗi và cảnh báo.
- Khi người dùng chọn portable ZIP, phải đảm bảo `MAPClass.cls`, `ex_test.sty`, hình ảnh, các file `\input`/`\include` liên quan và hướng dẫn biên dịch được đóng gói đầy đủ theo profile đang sử dụng. Không khẳng định “100%” nếu chưa kiểm chứng.
- Tránh path traversal, file đè ngoài thư mục, tên file trùng, tham chiếu thiếu, và phụ thuộc vào đường dẫn tuyệt đối trên máy phát triển.
- Export ra staging folder, xác minh rồi atomic finalize nếu khả thi; khi thất bại không để lại bundle nửa vời mang nhãn thành công.
- Test giải nén ZIP sang thư mục tạm độc lập, biên dịch lại TeX, kiểm tra manifest/hash và nội dung PDF. Test tình huống thiếu class, thiếu asset, lỗi quyền ghi, tên file Unicode.

## Phase D — Nghiệp vụ ra đề (P1)
- Tách **Ra đề nhanh** và **Ra đề theo ma trận** trên UI, dùng chung service backend.
- Ra đề nhanh: chọn lớp/môn → lọc/chọn câu → cấu hình cơ bản → preview A4 → xuất.
- Ra đề theo ma trận: số câu theo dạng thức/mức độ/chủ đề, seed tái lập, phân bổ không trùng, cảnh báo thiếu câu, cấu hình nhiều mã đề.
- Kiểm tra xáo lựa chọn giữ đúng `\True`, đúng đáp án, lời giải và không làm hỏng TeX/TikZ.
- Preview tiêu đề `\TieudeT` chỉ là bản mô phỏng UI; bản PDF biên dịch là nguồn chuẩn. Tránh dùng giao diện nền tối cứng trong Light Theme.
- Trạng thái xuất: đang làm, thành công, cảnh báo, lỗi; có thể hủy tác vụ; UI không đơ.
- Test snapshot reproducibility, uniqueness, 4 loại câu, export học sinh/giáo viên/đáp án, nhiều mã đề, missing dependencies.

## Phase E — Hoàn thiện UI ngân hàng câu hỏi (P1)
- Áp dụng **light modern** mặc định: nền sáng, chữ rõ, accent xanh; dark mode tùy chọn, dùng token chung.
- Thiết kế như **ứng dụng quản lý thư viện giáo dục**, không như VS Code: phân loại bên trái khi cần, nội dung câu hỏi ở trung tâm, preview/thuộc tính mở theo ngữ cảnh; cho phép ẩn/thu gọn panel.
- Hỗ trợ hai chế độ: danh sách mật độ cao và thẻ thumbnail; thanh tìm kiếm nổi bật; filter theo môn, lớp, chương, bài, dạng, độ khó, trạng thái, tài nguyên.
- Có chọn nhiều câu, chuyển phân loại, gắn nhãn, thêm vào đề, xóa/lưu trữ có xác nhận. Phân biệt rõ action chính và action phụ.
- Editor chuyên sâu mở khi cần; không mặc định hiển thị code LaTeX trên mọi thẻ.
- Refactor `main_window.py` và `pages/library.py` theo trách nhiệm: view, controller/presenter, state, actions, preview/cache. Không refactor toàn dự án chỉ để giảm số dòng.
- Đồng bộ ngay sau khi lưu: thẻ, tìm kiếm, taxonomy, metadata, cache invalidation. Không mất vị trí cuộn và bộ lọc khi quay lại.
- Kiểm tra UI ở 1366×768, 1600×900, 1920×1080, scale Windows 125%/150%; không nút bị che, tràn chữ, panel chồng, modal quá lớn.
- Chụp ảnh thật từng trạng thái: rỗng, có dữ liệu, đang tải, lỗi render, câu dài, câu có hình, chọn nhiều câu. So sánh mockup, báo rõ điểm chưa đạt.

## Phase F — Thumbnail và preview hiệu năng (P1)
- Giữ pdfLaTeX làm nguồn chuẩn cho bản in và preview đầy đủ.
- Cache thumbnail file riêng, không Base64 trong SQLite; DB chỉ lưu key/metadata nếu cần. Key tính từ LaTeX source + asset hashes + preamble/profile + engine + render options.
- Render lazy chỉ các item trong viewport/near viewport; worker nền có cancellation và chống stale result. Không tạo một QWebEngineView cho mỗi câu.
- WebP có kiểm tra độ sắc nét công thức, fallback PNG; giữ tỷ lệ, không làm méo hình; cache disk giới hạn mặc định 1 GiB, RAM khoảng 128 MiB, LRU và cơ chế clear cache an toàn. Những con số là cấu hình khởi điểm, phải benchmark.
- Preview lớn có chất lượng riêng; thumbnail không được dùng làm bản in. Không xóa asset gốc khi clear cache.
- Benchmark với ít nhất 200 câu thực: câu text/math, ảnh, TikZ, macro MAPClass; đo first render, scroll FPS/latency, RAM, cache hit, kích thước disk.
- **KaTeX chỉ là prototype thử nghiệm tùy chọn**, không tích hợp vào sản phẩm nếu chưa đo độ chính xác. Có thể dùng 1 web view cho quick preview; parser chuyển `ex_test` sang HTML, không cố render TikZ bằng KaTeX; fallback pdfLaTeX khi unsupported. Không thêm dependency nặng nếu lợi ích không rõ.

## Phase G — Soạn bài giảng và hồi quy (P2)
- Xác minh mô hình bài giảng nhiều file: `theory.tex`, `dang-XX-*.tex`, `bai-tap-van-dung.tex`, `main.tex` qua `\input`; thứ tự, rename, import/export, asset refs.
- UI bài giảng giống Document Editor: outline bên trái, canvas tài liệu/preview chính, thuộc tính theo ngữ cảnh; không ép layout ngân hàng sang bài giảng.
- Test end-to-end với bài giảng có nhiều dạng, câu hỏi ngân hàng, hình TikZ, Unicode và macro MAPClass.

## Phase H — Kiểm thử release và bàn giao
- Chạy full tests; ghi PASS/FAIL/SKIP, không báo “all pass” khi còn skip quan trọng.
- Kiểm thử build Windows EXE và ZIP; thử trên môi trường Windows sạch nếu có điều kiện, nêu rõ nếu chưa thử.
- Kiểm tra DB migration, backup/restore, dữ liệu 1k/10k/50k câu (có thể dùng dữ liệu sinh giả để benchmark), import không trùng, quyền truy cập file.
- Tạo `docs/MCPTEST_STABILIZATION_FINAL_REPORT.md`: commit từng phase, file thay đổi, lỗi đã sửa, test log, benchmark trước/sau, ảnh UI, rủi ro còn lại, các bước người dùng cần thử.

## Quy trình thực hiện bắt buộc
1. Bắt đầu bằng Phase A; trình bày kế hoạch ngắn, sau đó triển khai lần lượt B → C → D → E → F → G → H.
2. Ưu tiên P0 trước. Nếu phát hiện vấn đề ảnh hưởng dữ liệu hoặc lộ đáp án, dừng tính năng mới và xử lý trước.
3. Mỗi phase: tái hiện lỗi → viết regression test → sửa code → chạy test → tự review diff → commit rõ ràng → cập nhật báo cáo.
4. Không xóa test lỗi để lấy PASS, không thay thế kiểm thử thực bằng screenshot giả, không tuyên bố tính năng hoàn thành khi chỉ dựng UI.
5. Trước khi push, xác nhận remote/branch; không force push. Nếu thiếu quyền push, cung cấp commit SHA và lệnh để người dùng thực hiện.
6. Khi kết thúc, trả lời tiếng Việt: `PHASE | Trạng thái | Commit | Tests | Ảnh UI | Rủi ro`, và nêu công việc tiếp theo.

**Bắt đầu ngay Phase A và tiếp tục các phase trong phạm vi môi trường/quyền hiện có; không chờ xác nhận lại trừ khi gặp quyết định nghiệp vụ không thể tự suy ra hoặc thao tác phá hủy dữ liệu.**
