# MCPTest — Phase L.2: Tech12h Adapter & Real-Page Import Reliability

## Mục tiêu
Sửa luồng thu thập dữ liệu để xử lý được URL kiểm thử cụ thể:
`https://tech12h.com/bai-hoc/trac-nghiem-khtn-9-ket-noi-bai-5-khuc-xa-anh-sang`

Không đánh đồng **tech12h.com** với **tech24.vn**. Tái sử dụng pipeline fetch → parse → staging → review → ex_test → Phase K export. Không ghi CSDL trước khi giáo viên duyệt; không vượt CAPTCHA, đăng nhập hoặc hạn chế truy cập.

## L2.0 — Chẩn đoán chính xác lỗi
1. Chạy ứng dụng trên Windows với URL nêu trên. Ghi rõ HTTP status, redirect chain, content-type, response length, encoding, robots decision, timeout, số lượng block câu hỏi và số câu trích xuất; tránh ghi token/cookie.
2. Phân biệt lỗi fetch, lỗi adapter selection, lỗi selector, lỗi chuyển HTML → LaTeX, lỗi ảnh, lỗi xuất pdfLaTeX.
3. Tạo fixture HTML từ nội dung được phép truy cập, loại bỏ dữ liệu không cần thiết; không commit nguyên bài có bản quyền. Nếu site không cho phép thu thập, chỉ dùng fixture do người dùng cung cấp hoặc nội dung được cấp quyền.
4. Có thông báo UI riêng cho timeout, 403/429, robots disallow, trang không có câu hỏi, trang thay đổi cấu trúc.

## L2.1 — Adapter Tech12h riêng
- Tạo `src/latex_question_studio/scraping/adapters/tech12h.py` với `Tech12hAdapter`, đăng ký trong adapter registry trước GenericAdapter.
- `can_handle()` kiểm tra hostname chính xác `tech12h.com` hoặc subdomain hợp lệ, không nhầm tech24.vn.
- Tìm vùng nội dung trắc nghiệm, bỏ navigation/ads/sidebar/footer, tách từng `Câu N:` và 4 lựa chọn A–D, kể cả lựa chọn nằm trong thẻ li/p/div lồng nhau.
- Bảo toàn thứ tự câu và phương án; nhận diện đáp án chỉ khi có tín hiệu chắc chắn từ markup thực tế. Không suy đoán đáp án từ định dạng heading `h6` khi chưa kiểm chứng DOM/semantics.
- Giữ công thức gốc, chỉ số dưới/trên, ký hiệu góc/độ, hình ảnh và URL nguồn; cảnh báo khi một lựa chọn chỉ có ảnh hoặc thiếu dữ liệu.
- Nếu đáp án không chắc chắn, đặt `needs_review` và `correct_choice=None`, không tự đánh dấu `\True`.
- Không tự nhập phần đáp án/lời giải ẩn hoặc nội dung bị hạn chế truy cập.

## L2.2 — HTML/Math/Assets
- Sử dụng parser DOM thực thay regex cho cấu trúc lồng nhau. Ưu tiên annotation LaTeX của KaTeX/MathJax; không trộn hai bản hiển thị và bản accessibility gây lặp công thức.
- Chuyển ký hiệu toán ngoài math mode thành LaTeX hợp lệ; kiểm tra `\textsuperscript`, `\textsubscript` trong văn bản, và `$...$` trong toán.
- Tải ảnh qua cùng policy SSRF/robots/timeout, giới hạn kích thước/MIME, cache theo hash, thay placeholder bằng `\includegraphics` đường dẫn tương đối; không để `[IMG:...]` lọt vào đề xuất.
- Khi ảnh bị lỗi, giữ câu trong staging và hiển thị cảnh báo, không báo xuất thành công.

## L2.3 — UI staging và xuất chuẩn
- Giao diện báo: số câu nhận diện, số MCQ hợp lệ, câu thiếu đáp án, câu thiếu ảnh, câu biên dịch lỗi.
- Cho phép chỉnh sửa nội dung, phương án, đáp án, lời giải, ảnh trước khi xác nhận.
- Mỗi câu xuất theo `\begin{ex} ... \choice ... \loigiai{...} \end{ex}`.
- Khi xuất đề: `\TieudeT{...}`, `\PhanI`, `\begin{cauhoiTN}{De01}` ... `\end{cauhoiTN}`. Không xáo đáp án khi chưa có đáp án xác thực. Tuân thủ toàn bộ quy tắc Phase K.
- Kiểm tra pdfLaTeX thật bằng MAPClass/ex_test và ZIP độc lập; lưu log lỗi theo câu.

## L2.4 — Kiểm thử và nghiệm thu
1. Test nhận diện đúng `tech12h.com`, không nhận `tech24.vn`, không chấp nhận hostname giả mạo.
2. Test 25 câu có đánh số, đủ 4 phương án, công thức, câu có hình, đáp án thiếu/chưa chắc chắn, đáp án chính xác; không gán nhầm `\True`.
3. Test HTML lồng nhau, whitespace, Unicode, lazy image `data-src/srcset`, MathJax/KaTeX/MathML, thay đổi selector, duplicate UI text.
4. Test HTTP 200/403/429/timeout/redirect/robots; không né hạn chế site.
5. Chạy thử URL được cung cấp nếu được phép, lưu kết quả đo thực; nếu không truy cập được thì ghi `NOT VERIFIED`, không báo đã hỗ trợ thực tế.
6. Chạy regression toàn repo, build Windows, smoke test giao diện, kiểm tra không hỏng Phase K/L/L.1.

## Báo cáo và bàn giao
- Commit theo từng phần, push GitHub; không force-push.
- Tạo `docs/PHASE_L2_TECH12H_REPORT.md`: nguyên nhân gốc, ảnh chụp/log chẩn đoán đã loại thông tin nhạy cảm, số câu trích xuất thực tế, số câu cần duyệt, số câu thiếu ảnh, kết quả biên dịch, các hạn chế, SHA cuối.
- Chỉ công bố PASS cho URL thật khi đã xác nhận trên HTML thực được phép sử dụng, kiểm tra thủ công mẫu câu và xuất PDF thành công.
