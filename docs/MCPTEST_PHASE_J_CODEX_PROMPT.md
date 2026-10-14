# MCPTest — PHASE J: Production Readiness & Teacher Workflow

## Vai trò và phạm vi
Bạn là Codex, kỹ sư chịu trách nhiệm hoàn thiện MCPTest (Python, PySide6, SQLite, pdfLaTeX, ex_test.sty, MAPClass.cls).
Repository: https://github.com/letrieubavuong/MCPTest
Baseline tham chiếu: `ac1c0b033999c88ce3d5e2628f1a75ff9f007587` (kiểm tra HEAD thực tế trước khi làm).
Đọc `docs/PHASE_I_REAL_WORLD_VALIDATION_REPORT.md`, `docs/PHASE_I_BENCHMARK_REPORT.md`, các test Phase B–I, và kiểm tra mã hiện tại trước khi sửa. Không giả định mọi kết luận trong báo cáo là đã được chứng minh.

**Mục tiêu:** trải nghiệm dùng thật của giáo viên với ngân hàng 1.000–10.000 câu, đặc biệt lần mở đầu, preview, xuất đề và bảo toàn dữ liệu. Không thêm tính năng lớn, không đổi kiến trúc, không tích hợp KaTeX vào production trong phase này.

## J0 — Baseline và phép đo tái lập
1. `git status`, branch, HEAD; kiểm tra trạng thái working tree. Không ghi đè thay đổi người dùng.
2. Chạy test suite; ghi số passed/failed/skipped và môi trường (Windows, Python, Qt, TeX distribution).
3. Lập bộ dữ liệu test có thể tái tạo từ mẫu TeX thật trong repo; nếu không có đủ thì dùng bộ dữ liệu tổng hợp có ghi nhãn rõ ràng, không gọi đó là dữ liệu người dùng thật.
4. Báo cáo baseline tại `docs/PHASE_J_BASELINE.md`.

## J1 — Render lần đầu: ưu tiên viewport và không khóa UI
Vấn đề: báo cáo Phase I đo cold compile trung bình ~2,61 giây/câu. 200 câu nếu xử lý tuần tự có thể rất lâu.
- Audit luồng `ui/pages/library.py`, `ui/main_window.py`, `ui/jobs.py`, `preview/compiler.py`, `preview/thumbnails.py`.
- Thiết lập hàng đợi render ưu tiên: câu trong viewport > câu vừa chọn > prefetch vùng lân cận > tác vụ nền.
- Dedupe job theo cache key; một key không được biên dịch nhiều lần đồng thời.
- Giới hạn concurrency phù hợp để không gây nghẽn CPU/RAM/TeX; mặc định thận trọng và có thể cấu hình.
- Hủy tác vụ chưa chạy khi đổi bộ lọc/chế độ; không hiển thị kết quả cũ khi revision hoặc selection đã thay đổi.
- Khi cache miss: placeholder và trạng thái chờ; UI không block; lỗi có retry và thông báo có ích.
- Chỉ thử batch compilation trong nhánh thử nghiệm nếu chứng minh được cắt trang chính xác, không lẫn câu, tương thích TikZ/asset/preamble; không thay thế pipeline ổn định khi chưa đạt.
- Không tự động render toàn bộ 10.000 câu lúc mở ứng dụng.

## J2 — Một chuẩn crop duy nhất
Hiện có logic crop ở `preview/compiler.py` và `ThumbnailManager.render_and_cache()`.
- Tạo một hàm dùng chung (hoặc một module chuyên biệt) tính bounding box từ text blocks, vector drawings và raster image info; clipping, padding, trang rỗng và trang nhiều trang.
- Đảm bảo không cắt mất dấu tiếng Việt, nhãn TikZ, mũi tên, ảnh PNG/JPG, công thức cao/thấp.
- Tách rõ preview toàn trang và thumbnail câu hỏi; tránh lấy nhầm trang đầu nếu một câu dài nhiều trang.
- Tạo golden-image tests với ngưỡng sai khác hợp lý; lưu fixture, không phụ thuộc font/TeX bất định mà không ghi rõ.
- Bổ sung test với ảnh nhúng, `tkz-euclide`, bảng biểu, tiếng Việt và nhiều trang.

## J3 — An toàn đề học sinh sau mở rộng macro
Tập trung `application/lessons.py` (`STUDENT_COMMANDS`, `student_source`) và `application/exams.py`.
- Kiểm toán macro mới được allowlist ở commit `ac1c0b0`, đặc biệt `\immini`, các macro MAPClass và `tkz-euclide`.
- Không mặc định macro an toàn chỉ vì tên nằm trong allowlist. Phân biệt lệnh trình bày, lệnh khai báo/định nghĩa và macro có khả năng chứa đáp án.
- Với macro định nghĩa bởi người dùng hoặc chưa phân tích được: fail closed có thông báo cụ thể, không âm thầm bỏ qua và không vô hiệu hóa toàn bộ macro hợp lệ một cách tùy tiện.
- Kiểm tra lời giải/đáp án trong tham số tùy chọn, macro lồng nhau, comment, escaped braces, `\choiceTF`, `\shortans`, `\loigiai`, `\hdan`, asset chỉ xuất hiện trong lời giải.
- So sánh source học sinh và PDF đầu ra; xác minh teacher export vẫn đầy đủ.
- Thêm regression tests cho từng lỗi tìm được; không tuyên bố 'an toàn tuyệt đối'.

## J4 — Đo UI responsiveness đúng cách
- Benchmark thực tế: 1.000 câu, 10.000 câu (có thể tổng hợp, ghi rõ), viewport 1366×768, 1600×900, 1920×1080; nếu hỗ trợ thì Windows scaling 125%/150%.
- Tách các chỉ số: thời gian mở ứng dụng, thời gian hiện danh sách, time-to-first-thumbnail, thời gian hiển thị thumbnail 20/50/100 câu, độ trễ tìm kiếm/lọc, peak RAM, tốc độ cuộn và thời gian frame p50/p95/p99.
- Không suy luận 60 FPS từ tổng thời gian render 100 câu; đo frame-time bằng công cụ Qt hoặc phương pháp đo có mô tả rõ.
- Test nhanh chuyển chế độ Card/List, chọn hàng loạt, chỉnh sửa câu rồi quay lại thư viện; kiểm tra invalidation cache và đồng bộ trạng thái.
- Tạo ảnh chụp UI thật và ghi vị trí artifact.

## J5 — E2E teacher acceptance
Tạo kịch bản sử dụng liên tục trên dữ liệu test: import TeX (có TikZ/ảnh) → phân loại → tìm kiếm → sửa → preview → chọn câu → sinh ít nhất 2 mã đề → export student/teacher/answer key → ZIP → giải nén vào thư mục khác → biên dịch PDF → kiểm tra nội dung.
- Kiểm tra dữ liệu gốc và revision không bị thay đổi ngoài ý muốn.
- Kiểm tra dedupe, path traversal, asset hashing, thiếu dependency và lỗi compiler.
- Kiểm tra đóng/mở ứng dụng giữa chừng, hủy export, cache corruption, mất quyền ghi, thiếu TeX engine.
- Thực hiện sao lưu/khôi phục DB test và kiểm tra checksum/record count.
- Dùng đường dẫn tạm, không chạm dữ liệu thực của người dùng.

## J6 — Release và báo cáo trung thực
- Chạy toàn bộ tests, ghi output; không tự ý xóa/skip test lỗi để báo PASS.
- Build EXE Windows, smoke test khởi động/đóng, xác minh không kèm dữ liệu người dùng hoặc secret.
- Báo cáo tại `docs/PHASE_J_PRODUCTION_READINESS_REPORT.md`: thay đổi theo file, lỗi P0/P1/P2, phép đo trước/sau, dữ liệu test và phương pháp, ảnh UI, tests pass/fail/skip, hạn chế còn lại, SHA và hướng dẫn nghiệm thu thủ công.
- Mỗi phần commit riêng với thông điệp rõ ràng; push `origin/main` chỉ khi không có xung đột và test bắt buộc đạt. Không force-push.

## Tiêu chí nghiệm thu bắt buộc
- Không crash, không race khi đổi trang/lọc liên tục hoặc đóng ứng dụng lúc đang render.
- Không render toàn bộ thư viện khi mở; ưu tiên câu đang nhìn thấy, không có duplicate jobs.
- Preview và thumbnail không mất hình/chữ, kết quả cache không bị stale sau chỉnh sửa.
- Student PDF/TeX không lộ đáp án trong bộ test phức tạp; lỗi không phân tích được phải chặn xuất và chỉ rõ nguyên nhân.
- Không có tác vụ biên dịch nặng chạy trực tiếp trên UI thread.
- Mọi số liệu benchmark phải kèm script, đầu vào, môi trường và phương pháp tái lập.
- Không tuyên bố 'hoàn thành' nếu chưa có bằng chứng. Báo cáo những tiêu chí chưa đạt.

## Cách thực thi
Làm tuần tự J0→J6; ưu tiên sửa P0 trước. Có thể tự tiếp tục giữa các bước đã được yêu cầu. Sau mỗi bước, chạy test liên quan, commit có ý nghĩa, và cuối cùng báo cáo commit SHA, kết quả nghiệm thu cùng danh sách rủi ro chưa giải quyết.
