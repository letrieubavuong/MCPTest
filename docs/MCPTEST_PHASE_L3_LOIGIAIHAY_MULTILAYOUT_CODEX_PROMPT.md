# MCPTest — Phase L.3: Loigiaihay Multi-layout Extraction & Exam Fidelity

## Bối cảnh
MCPTest đã có `LoigiaihayAdapter`, nhưng phải xử lý nhiều kiểu trang trên cùng domain, không chỉ HTML fixture tự tạo. Giữ nguyên nghiệp vụ Phase K (MAPClass/ex_test, pdfLaTeX) và các biện pháp an toàn Phase L/L.1/L.2.

## URL nghiệm thu bắt buộc
1. https://loigiaihay.com/giai-sbt-khoa-hoc-tu-nhien-9-bai-36-khai-quat-ve-di-truyen-hoc-trang-97-98-99-ket-noi-tri-thuc-a174817.html
2. https://loigiaihay.com/de-thi-giua-ki-1-khtn-9-ket-noi-tri-thuc-de-so-2-a173750.html
3. Hồi quy URL Tech12h: https://tech12h.com/bai-hoc/trac-nghiem-khtn-9-ket-noi-bai-5-khuc-xa-anh-sang

## Thực tế đã quan sát trên trang công khai
- URL 1: Bài tập đánh số 36.1 đến 36.9, kèm 'Phương pháp giải' và 'Lời giải chi tiết'; bài 36.5 có bảng 7 nhận định Đúng/Sai, không phải một câu choiceTF bốn ý.
- URL 2: Phần I có 16 MCQ; Phần II có 3 câu đúng/sai, mỗi câu 4 nhận định; Phần III có 3 câu trả lời ngắn, một số có nhiều tiểu ý a/b/c/d. Nội dung câu hỏi xuất hiện lại trong phần 'Lời giải và đáp án'. Có hình minh họa ở một số câu.
- Các số lượng trên là mốc kiểm thử theo nội dung trang đã quan sát; nếu website thay đổi, ghi rõ snapshot, ngày và sai khác.

## L3.0 — Baseline và chẩn đoán
- Checkout HEAD, kiểm tra thay đổi chưa commit, chạy full pytest. Không sửa dữ liệu thật.
- Ghi HTTP status, final URL, content type, charset, byte count, fetch elapsed, robots/copyright policy, DOM selector, số block trích xuất. Không ghi cookie/token.
- Thu thập HTML snapshot hợp lệ để regression, lưu hash và provenance. Không vượt CAPTCHA/paywall/robots hoặc hạn chế kỹ thuật. Nếu không được phép tải, hỗ trợ người dùng dán HTML/nội dung có quyền sử dụng.

## L3.1 — Nhận diện layout theo nội dung, không chỉ domain
- Refactor `scraping/adapters/loigiaihay.py` thành dispatcher và các extractor: `SBTExerciseExtractor` và `ExamPaperExtractor`, có fallback Generic kèm cảnh báo.
- Tách article content khỏi menu, quảng cáo, related posts, widget, navigation, footer.
- Không dựa duy nhất vào regex 'Câu N'; SBT có dạng '36.1', '36.2'..., đề thi có 'PHẦN I/II/III' và số câu reset mỗi phần.
- Gắn `source_url`, `source_section`, `source_question_number`, `dom_locator`, `extraction_confidence`, `source_snapshot_hash`, `fetched_at` cho từng draft.

## L3.2 — SBT: tách câu và lời giải
- Mỗi bài 36.1–36.9 phải là đơn vị câu hỏi riêng, giữ thứ tự, nội dung đề, hình/bảng, 'Phương pháp giải', 'Lời giải chi tiết'.
- Phân loại tự luận/MCQ/TF/shortans dựa trên cấu trúc thực, không tự suy diễn.
- Bài 36.5 có bảng 7 nhận định: giữ bảng nguyên vẹn trong `ex` tự luận hoặc một model bảng nhận định hỗ trợ số hàng tùy ý; KHÔNG ép vào `\choiceTF` 4 ý, KHÔNG xóa 3 hàng.
- Nếu muốn tách bảng thành nhiều câu, yêu cầu giáo viên thao tác thủ công và xác nhận.

## L3.3 — Đề thi: section-aware parser và answer join
- Phân tích 'Đề bài' thành phần I, II, III; 'Lời giải và đáp án' thành answer/solution source, không tạo thêm câu hỏi.
- ID ghép câu phải là `(part, ordinal)` hoặc DOM/source ID ổn định, tuyệt đối không chỉ dùng `Câu 1` vì mỗi phần đánh số lại.
- Phần I: 16 MCQ 4 phương án, xác định `\True` từ đáp án có nguồn, không đoán; thiếu/đáp án mâu thuẫn => `needs_review`.
- Phần II: 3 câu `\choiceTF`, giữ chính xác thứ tự 4 nhận định; trích xuất vector đúng/sai từ lời giải nếu đủ bằng chứng, không nhầm nhãn 'Đúng/Sai' giao diện là đáp án.
- Phần III: 3 câu trả lời ngắn; giữ nguyên tiểu ý a/b/c/d và đáp án tương ứng. Nếu `\shortans` một ô không biểu diễn được nhiều đáp số, giữ câu ở dạng tự luận hoặc yêu cầu giáo viên chọn chuyển đổi; không mất tiểu ý.
- Ảnh thuộc câu nào phải giữ thuộc câu đó; tải qua pipeline asset hợp lệ, đường dẫn tương đối portable; phát hiện ảnh lỗi, không âm thầm bỏ qua.

## L3.4 — HTML/Math to pdfLaTeX
- Preserve MathJax, KaTeX annotation, MathML, unicode, đơn vị SI, chỉ số dưới/trên, bảng và hình.
- Tránh tạo `^`, `_`, `\le`, `\in` ngoài math mode; escape `%`, `&`, `#`, `$` đúng ngữ cảnh; giữ tiếng Việt T5/pdfLaTeX.
- Mọi macro chưa hỗ trợ cần cảnh báo cụ thể và có editor chỉnh tay, không âm thầm thay công thức.
- Xuất câu hỏi dạng `\begin{ex}...\end{ex}`; dùng `\choice`, `\choiceTF`, `\shortans`, `\loigiai` đúng kiểu.
- Khi xuất đề theo Phase K: `\TieudeT`, `\PhanI` + `cauhoiTN`, `\PhanII` + `cauhoiDS`, `\PhanIII` + `cauhoiTLN`, `\PhanTL` + `cauhoiTL`; giữ quy tắc xáo riêng từng loại.

## L3.5 — UX staging và kiểm duyệt
- Hiển thị URL, layout, số câu theo loại, số câu thiếu đáp án, số ảnh thiếu, lỗi biên dịch.
- Hiển thị đối chiếu DOM/source vs LaTeX preview theo từng câu, cho phép sửa và đánh dấu verified từng câu; mặc định needs_review.
- Không nhập DB nếu chưa verified; không báo export success nếu pdflatex thất bại; không ghi đè file nguồn.
- Có chức năng 'chỉ lấy đề', 'lấy đề và lời giải', tránh trùng từ answer section.
- Không thu thập hàng loạt nội dung có bản quyền khi chưa có quyền; không vượt hạn chế truy cập; ghi nguồn/provenance cho mỗi câu.

## L3.6 — Kiểm thử, tiêu chí nghiệm thu
- Integration với snapshot DOM thật được phép sử dụng, có kiểm thử cập nhật khi HTML thay đổi; không chỉ fixture đơn giản tự chế.
- URL SBT: đúng 9 bài đánh số 36.1–36.9, không mất bảng 7 nhận định, lời giải gắn đúng bài.
- URL đề: đúng 16 MCQ + 3 TF + 3 short-answer theo nội dung quan sát; không nhân đôi câu ở phần lời giải; mỗi TF 4 nhận định đúng thứ tự; mỗi short answer giữ đủ tiểu ý.
- Kiểm tra nội dung có ảnh: file có tồn tại, đóng gói ZIP portable, biên dịch pdfLaTeX từ thư mục khác thành công.
- Tests negative: missing answers, duplicate question numbers across sections, invalid MathML, image 404, malformed HTML, network timeout, redirect/SSRF, denied robots, wrong encoding, mixed MathJax.
- Chạy full pytest, benchmark UX, test Windows EXE, regression Phase K, Phase L/L.1/L.2.
- Báo cáo `docs/PHASE_L3_LOIGIAIHAY_REPORT.md` có bảng từng URL: HTTP/robots, câu dự kiến/thực tế, loại câu, thiếu ảnh, đáp án chưa rõ, compile status, log errors, commit SHA. Nếu trang không truy cập hợp lệ được thì báo blocked, không fake success.
- Commit và push theo nhóm việc; không tuyên bố hoàn thành nếu chưa chạy URL thật và kiểm tra biên dịch.

## Chỉ dẫn thực hiện
Tự đọc kiến trúc hiện có, dùng lại parser/AssetStore/Compiler/ExamService, tránh duplicate logic và không làm hỏng schema CSDL. Ưu tiên correctness, provenance, khả năng phục hồi, an toàn dữ liệu. Không tự ý thay đổi định nghĩa MAPClass/ex_test.
