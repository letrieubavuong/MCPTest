# MCPTest — Phase J.7: Hardening & Release Candidate 0.5.3

## Bối cảnh và phạm vi
- Repository: `https://github.com/letrieubavuong/MCPTest`
- Baseline đã kiểm tra: `3823579764f7413d7a3b635d82033ffc6cbb9eac` (Phase J6).
- Nhiệm vụ: sửa lỗi thực tế, bổ sung regression và đóng gói RC. Không viết lại các Phase A–J, không tự tuyên bố Production Ready.
- Môi trường mục tiêu: Windows, Python/PySide6, pdfLaTeX, ex_test, MAPClass, TikZ, tiếng Việt.
- Trước khi sửa: `git status`, `git log -5`, đọc `docs/PHASE_J_PRODUCTION_READINESS_REPORT.md` và mã nguồn hiện tại. Nếu HEAD khác baseline, đối chiếu diff và tránh ghi đè thay đổi mới.

## J.7.1 — P0: Chống mất tín hiệu khi nhiều câu chia sẻ một thumbnail key
File trọng tâm: `src/latex_question_studio/preview/queue.py`, `ui/pages/library.py`.

Hiện tại `enqueue()` bỏ qua yêu cầu mới nếu key đã nằm trong `_active` hoặc `_pending`, trong khi kết quả hoàn thành chỉ gắn với một `question_id`. Hai câu có nội dung và tài nguyên giống nhau có thể dùng chung key nhưng đều phải nhận được kết quả.

Yêu cầu:
1. Thiết kế subscriber registry theo render key, mỗi subscriber mang `question_id`, `revision`, source identity và trạng thái viewport nếu cần.
2. Khi pending/active đã có key, đăng ký subscriber mới thay vì bỏ qua; nâng priority theo yêu cầu cao nhất.
3. Khi render thành công/thất bại, phát tín hiệu đến tất cả subscriber còn hợp lệ; không cập nhật widget đã bị xóa hoặc revision đã thay đổi.
4. Xử lý cancel theo subscriber hoặc generation; không để kết quả cũ ghi đè kết quả câu mới sau filter/search/navigation.
5. Nếu cache đã có ảnh, ưu tiên trả kết quả nhanh mà không biên dịch lại.
6. Dọn subscriber, pending, active và signal connection để tránh memory leak.
7. Không tạo `QPixmap` ngoài GUI thread.

Tests bắt buộc: 2 ID cùng key pending; 2 ID cùng key active; kết quả success/failure fan-out; một subscriber bị hủy; revision thay đổi; filter đổi trong khi render; 100 lần enqueue trùng key chỉ compile một lần; không rò bộ nhớ sau lặp nhiều lần.

## J.7.2 — P0: Shutdown an toàn với pdfLaTeX đang chạy
File trọng tâm: `preview/queue.py`, `preview/compiler.py`, `ui/jobs.py`, `ui/main_window.py`.

Hiện tại `shutdown()` chờ `waitForDone(1000)` trong khi biên dịch có thể kéo dài hơn. Cần ngăn race khi cửa sổ và QObject bị hủy trước khi worker kết thúc.

Yêu cầu:
1. Rà soát vòng đời QObject, signal, QRunnable/Job, QThreadPool và subprocess pdfLaTeX.
2. Có cancellation token rõ ràng, ngừng nhận request mới ngay khi shutdown.
3. Hủy tiến trình con pdfLaTeX đúng cách khi người dùng đóng ứng dụng; dọn file tạm có kiểm soát.
4. Không phát callback cập nhật UI sau khi receiver đã bị hủy; không block GUI vô hạn.
5. Nếu chưa thể dừng worker tức thì, thực hiện quy trình đóng an toàn và có timeout hợp lý; không dùng `waitForDone(1000)` như bằng chứng worker đã kết thúc.
6. Giữ nguyên cảnh báo lưu dữ liệu chưa lưu trong `closeEvent`; khi người dùng chọn Cancel, không shutdown worker hoặc đóng ứng dụng.
7. Không sử dụng `terminate()` tùy tiện với QThread; xử lý process tree trên Windows nếu thực sự cần.

Tests: đóng app lúc idle; lúc compile đang chạy; lúc pending 100 job; lúc có tab chưa lưu và chọn Cancel/Save/Discard; đóng-mở lại 20 lần; không crash, không orphan `pdflatex.exe`, không mất dữ liệu.

## J.7.3 — P1: Đo frame-time trung thực và kiểm tra UI
File: `scripts/benchmark_phase_j_ui.py`, `docs/PHASE_J_BENCHMARK_RESULTS.json` và các test liên quan.

Báo cáo cũ ghi p95=17.13 ms, p99=17.33 ms, 14/40 frame >16 ms và 0 frame >33 ms. Không được suy diễn '60 FPS ổn định' từ các con số này.

Yêu cầu:
1. Định nghĩa ngưỡng 16.67 ms (60 Hz), 33.33 ms (30 Hz), 100 ms (freeze), ghi tỷ lệ vượt từng ngưỡng.
2. Đo tối thiểu 300 frame trên 3 lần chạy, ở 1k và 10k câu, cold và warm cache; có tương tác cuộn thật và mở/đóng thẻ.
3. Ghi p50/p95/p99/max, CPU, RSS, TTFT, số job đang chạy và cấu hình máy.
4. Phân biệt `frame interval`, `paint duration`, `event-loop latency`; không gọi interval là thời gian render GPU.
5. Dùng thời gian đo thực, không chèn `sleep` để tạo số liệu đẹp; nếu dùng pacing timer thì giải thích ảnh hưởng của nó.
6. Lưu dữ liệu thô (CSV/JSON) và script tái lập. Không chỉnh sửa kết quả benchmark bằng tay.
7. Ảnh chụp phải phản ánh kích thước thực tế; ghi nhận rõ 1920x1061 nếu không đạt 1920x1080. Thử DPI 100%, 125%, 150% khi môi trường hỗ trợ.
8. Báo cáo kết quả đúng thực tế; nếu không đạt mục tiêu, nêu bottleneck và phương án tiếp theo.

## J.7.4 — P1: Nghiệm thu nghiệp vụ và tính toàn vẹn đề
1. Dùng bộ dữ liệu LaTeX thật, gồm `\choice`, `\choiceTF`, `\shortans`, `\dapso`, `\dapsoTL`, `\loigiai`, `\immini`, TikZ, `tkz-euclide`, `\includegraphics`, `siunitx`.
2. Xuất đề học sinh và giáo viên; kiểm tra nội dung `.tex`, PDF và portable ZIP sau giải nén tại thư mục độc lập.
3. Kiểm tra macro tùy chỉnh: không mặc định coi macro an toàn chỉ vì có trong allowlist; đánh giá định nghĩa macro hoặc chặn khi không xác minh được.
4. Kiểm tra thay đổi asset/preamble/engine làm invalidation thumbnail chính xác.
5. Thử nhập trùng, sửa câu, tìm kiếm, phân loại, chọn hàng loạt, tạo nhiều mã đề, soạn bài giảng đa tệp.
6. Không thay đổi dữ liệu ngân hàng thật; sử dụng bản sao dữ liệu và sao lưu trước migration.

## J.7.5 — Regression, build RC và báo cáo
1. Chạy toàn bộ pytest, không sửa test chỉ để đạt PASS.
2. Bổ sung test race condition và E2E; ghi số PASS/FAIL/SKIP thực tế.
3. Build Windows RC 0.5.3, chạy smoke test thực trên EXE; nếu không có môi trường Windows, ghi NOT VERIFIED, không giả lập PASS.
4. Kiểm tra gói không chứa dữ liệu người dùng, secret, token hoặc đường dẫn máy phát triển.
5. Kiểm tra SHA-256, kích thước, khả năng giải nén và chạy độc lập (vẫn cần pdfLaTeX theo cấu hình ứng dụng).
6. Ghi lại ảnh UI và log thử nghiệm; chỉ đưa artifact vào Git nếu phù hợp dung lượng và không chứa dữ liệu riêng tư.
7. Tạo `docs/PHASE_J7_HARDENING_REPORT.md` với: root cause, files changed, tests, raw benchmarks, screenshots, remaining risks, RC status, commit SHA, link artifact nếu đã phát hành thực sự.
8. Commit theo nhóm J7.1–J7.5, push `main` sau khi kiểm tra; không force push và không xóa dữ liệu.

## Điều kiện nghiệm thu
- Hai hoặc nhiều câu cùng key đều nhận kết quả, nhưng chỉ có một compile job cho key đó.
- Đóng app trong khi compile không crash, không orphan process, không mất cảnh báo lưu.
- Báo cáo benchmark không có kết luận mâu thuẫn với dữ liệu thô.
- Student export không lộ đáp án trong bộ test thực tế; không tự động bỏ qua lỗi macro.
- Full regression PASS; Windows EXE smoke test PASS nếu có môi trường.
- Chỉ ghi 'Release Candidate ready' sau khi tất cả tiêu chí bắt buộc được kiểm chứng. Nếu còn lỗi P0, dừng phát hành và báo cáo chính xác.

## Cách báo cáo tiến độ
Sau mỗi nhóm công việc: tóm tắt thay đổi, test đã chạy, lỗi còn lại, SHA commit. Kết thúc: gửi HEAD mới nhất và nội dung `docs/PHASE_J7_HARDENING_REPORT.md`. Không báo cáo hoàn tất chỉ vì đã tạo tài liệu.
