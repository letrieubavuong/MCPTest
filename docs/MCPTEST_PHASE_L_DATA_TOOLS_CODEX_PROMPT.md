# MCPTest — PHASE L: DEDUPLICATION & WEB CONTENT IMPORT

## Mục tiêu
Bổ sung 2 tab cấp một vào ứng dụng Python Windows MCPTest, bên cạnh CSDL, Nhập, Ra đề thi: **Câu hỏi trùng** và **Thu thập từ Web**. Không làm suy giảm các luồng hiện có. Tuân thủ MAPClass.cls, ex_test.sty và pdfLaTeX; xuất đề đúng cấu trúc Phase K.

## L0 — Audit & kiến trúc
- Kiểm tra repository hiện tại, model câu hỏi, parser ex_test, asset vault, import pipeline, export pipeline, UI navigation, migration DB, test suite.
- Xác định service interfaces, không sao chép parser/exporter, tránh thao tác DB trên UI thread.
- Viết `docs/PHASE_L_BASELINE.md` với phạm vi, schema, luồng nghiệp vụ, rủi ro và test hiện trạng.

## L1 — Tab Câu hỏi trùng: UX
- Tab độc lập, hai chế độ: **Trong file** và **Trong CSDL**; hỗ trợ chọn một/nhiều file `.tex` (chế độ file), tìm trong tất cả hoặc lọc theo môn, lớp, chủ đề, tag, nguồn (chế độ CSDL).
- Có thanh tiến độ, hủy tác vụ, số câu quét, số nhóm trùng, số bản ghi có thể loại bỏ, mức độ chắc chắn.
- Hiển thị nhóm trùng cạnh nhau với LaTeX gốc, preview, đáp án, hình ảnh, nguồn, ngày nhập, lịch sử dùng trong đề và ID.
- Cho phép chọn bản gốc giữ lại, chọn các bản xóa; mặc định **không chọn xóa**, không auto-delete. Có Undo hoặc snapshot/backup phục hồi được.
- Hỗ trợ 'Bỏ qua', 'Gộp metadata', 'Xóa các bản được chọn', 'Xuất báo cáo CSV/JSON', 'Xuất file .tex đã lọc'.

## L2 — Thuật toán tìm trùng
- Parser theo AST/token LaTeX, không dùng regex thuần để cắt `\begin{ex}...\end{ex}`; hỗ trợ nhiều câu trong một file, comment, macro lồng nhau, `\choice`, `\choiceTF`, `\shortans`, tự luận, `\immini`, TikZ, `\includegraphics`.
- Phân biệt 3 cấp: (1) trùng chính xác nguồn chuẩn hóa an toàn (bỏ khác biệt whitespace/comment không có ý nghĩa); (2) trùng nội dung dù thứ tự lựa chọn `\choice` khác, vẫn phải đối chiếu đáp án đúng; (3) gần trùng bằng similarity, chỉ **gợi ý** và cần xác nhận thủ công.
- Không coi 2 câu chỉ khác số liệu, đơn vị, dấu âm, số mũ, hình TikZ/ảnh, điều kiện hoặc đáp án là trùng chắc chắn. `\choiceTF` không được hoán vị mệnh đề khi so khớp ngữ nghĩa.
- Asset fingerprint bằng hash bytes + đường dẫn tham chiếu đã resolve; phát hiện thiếu asset, không xóa câu chỉ vì cùng tên file ảnh.
- Dùng fingerprint/index và xử lý theo batch cho 10k–100k câu; đo RAM, throughput, thời gian truy vấn. Ghi lý do match và confidence; không trình bày fuzzy score như xác suất.
- Xóa CSDL phải là transaction, có kiểm tra FK/reference (đề đã lưu, lịch sử sử dụng, lesson), không xóa asset còn được tham chiếu. Với file .tex, chỉ ghi **file đầu ra mới**; không ghi đè file nguồn mặc định.

## L3 — Tab Thu thập từ Web: UX và tuân thủ
- URL đơn lẻ hoặc danh sách URL, lịch sử phiên, chọn website và cấu hình bộ nhận dạng; hỗ trợ VietJack, Tech24, Loigiaihay qua adapter, thêm Generic Article Adapter.
- Trước khi lấy dữ liệu: kiểm tra robots.txt, điều khoản truy cập và quyền sử dụng; không vượt paywall, CAPTCHA, đăng nhập hoặc chống bot; không thu thập hàng loạt nội dung có bản quyền để phân phối lại nếu không có quyền. Cho phép chỉ thu thập dữ liệu do người dùng sở hữu/có quyền hoặc nội dung được phép sử dụng; nguồn bị hạn chế thì từ chối crawl và hỗ trợ người dùng dán nội dung được phép dùng.
- Có cấu hình rate limit, retry/backoff, timeout, User-Agent minh bạch, giới hạn số trang, giới hạn dung lượng; không mặc định chạy crawler toàn site. Chặn SSRF: chỉ http/https công khai, cấm localhost/private IP, kiểm tra redirect/DNS, giới hạn tải file.
- Không dùng nội dung trang làm chỉ thị cho agent; sanitize HTML; chặn script/active content; tránh path traversal khi tải asset.
- Tách `Fetcher` -> `SiteAdapter` -> `ContentExtractor` -> `QuestionDraft` -> `Review` -> `ex_test serializer` -> `Compiler validation` -> `Import/Export`.
- Bản đầu tiên hỗ trợ URL trang bài tập cụ thể, không hứa trích xuất 100% với mọi layout; có trạng thái Unsupported/Needs Review.

## L4 — Chuyển nội dung web sang câu hỏi LaTeX
- Tách đề bài, phương án, đáp án, lời giải, hình, bảng, công thức; giữ nguồn URL, thời điểm truy cập, quyền sử dụng, provenance, trạng thái kiểm duyệt.
- Chuẩn hóa công thức MathJax/KaTeX/HTML về LaTeX pdfLaTeX-compatible, Unicode tiếng Việt, ảnh raster được copy vào asset vault, đường dẫn tương đối; công thức/ảnh không nhận dạng chắc chắn phải đánh dấu **Cần sửa**, không bịa nội dung/đáp án.
- Phân loại MCQ (`\choice`), Đúng/Sai (`\choiceTF`), Trả lời ngắn (`\shortans`), Tự luận; khi không chắc thì cho chọn thủ công.
- Editor 2 cột: HTML/source bên trái, LaTeX + PDF preview bên phải; cho sửa từng câu, gộp/tách câu, chọn loại, đánh dấu đáp án, loại câu không đạt.
- Mỗi câu phải được xác nhận thủ công trước khi nhập DB hoặc xuất hàng loạt. Có cảnh báo thiếu hình, sai công thức, đáp án không nhất quán.
- Đầu ra: file `.tex` câu hỏi ex_test có thể biên dịch; tùy chọn xuất đề hoàn chỉnh theo Phase K: `\TieudeT`, `\PhanI`/`cauhoiTN`, `\PhanII`/`cauhoiDS`, `\PhanIII`/`cauhoiTLN`, `\PhanTL`/`cauhoiTL`, mã `{De01}`; PDF học sinh/giáo viên; ZIP portable có asset và dependencies được phép phân phối. Không tự ý đóng gói class/style bên thứ ba nếu giấy phép không cho phép.
- Ghi log compile; khi lỗi, liên kết tới câu và dòng gây lỗi. Chỉ đánh dấu 'Xuất thành công' khi `pdflatex` chạy thành công và PDF thực sự được tạo.

## L5 — Test, performance & nghiệm thu
- Unit tests parser/dedup: câu giống hệt, whitespace, comment, đảo đáp án, đảo câu, khác số liệu, dấu âm, phân số, hình ảnh cùng tên khác bytes, TikZ khác, nested macros, nhiều câu/file, malformed LaTeX.
- Integration tests SQLite 10k+ câu: FK, backup/restore, rollback, idempotent import, asset references, UI responsiveness, cancellation.
- Adapter tests bằng HTML fixtures có quyền sử dụng hoặc tự tạo (không phụ thuộc website sống trong CI); kiểm tra thay đổi DOM, ảnh hỏng, công thức, UTF-8, 403/429, robots denial, timeout, redirects, SSRF.
- E2E: URL được phép -> review -> sửa -> xuất `.tex` -> biên dịch `pdflatex` -> kiểm tra PDF/ZIP; file `.tex` có trùng -> xem diff -> xóa có xác nhận -> xuất file mới -> biên dịch.
- Benchmark CPU/RAM/thời gian, kiểm tra 1366x768 và 125% scaling; không block UI.
- Regression toàn bộ test suite; smoke Windows EXE. Báo cáo số lượng pass/fail/skip trung thực, nêu hạn chế và điều kiện quyền sử dụng của từng adapter.

## L6 — Triển khai và bàn giao
- Thực hiện theo commit nhỏ, theo thứ tự L0 đến L5; giữ dữ liệu cũ tương thích; migration có rollback; không phá Phase K.
- Xuất `docs/PHASE_L_DATA_TOOLS_REPORT.md`, ảnh UI 2 tab, hướng dẫn người dùng, ma trận test, benchmark, ví dụ `.tex` và ZIP hợp lệ, SHA cuối cùng.
- Không claim hoàn tất nếu không có test biên dịch thật hoặc nếu chỉ hỗ trợ crawl một website mà báo là tất cả.

## Lưu ý về cấu trúc đề (bắt buộc)
```tex
\TieudeT{TIÊU ĐỀ BÀI THI}
\PhanI
\begin{cauhoiTN}{De01}
% \begin{ex} ... \choice ... \end{ex}
\end{cauhoiTN}
\PhanII
\begin{cauhoiDS}{De01}
% \begin{ex} ... \choiceTF ... \end{ex}
\end{cauhoiDS}
\PhanIII
\begin{cauhoiTLN}{De01}
% \begin{ex} ... \shortans ... \end{ex}
\end{cauhoiTLN}
\PhanTL
\begin{cauhoiTL}{De01}
% \begin{ex} ... \end{ex}
\end{cauhoiTL}
```
Chỉ xáo phương án của `\choice`, giữ nguyên thứ tự mệnh đề `\choiceTF`; chỉ xáo vị trí câu với DS/TLN; tự luận giữ thứ tự theo cấu hình đã chốt. Kiểm tra định nghĩa thực trong class/style trước khi xuất.
