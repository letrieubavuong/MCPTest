# MCPTest — PHASE L.1: Real-World Validation & LaTeX Conversion Hardening

## Vai trò và mục tiêu
Bạn là Codex, làm việc trực tiếp trong repository `letrieubavuong/MCPTest` trên nhánh làm việc hiện tại. Đọc mã nguồn thực tế và báo cáo Phase K/L trước khi sửa. Mục tiêu: biến hai tab **Câu hỏi trùng** và **Thu thập từ Web** từ bản có tính năng thành công cụ ổn định, có thể kiểm chứng với dữ liệu giáo viên thật. **Không** mở thêm module lớn, không phá hợp đồng xuất đề Phase K, không tự động xóa/nhập dữ liệu, không thay đổi cơ chế pdfLaTeX.

## L0 — Baseline và truy vết
1. Ghi HEAD SHA, phiên bản, Python/Qt/TeX, cấu trúc DB, các command build/test; xác minh commit `ce45cc1` hoặc ghi rõ khác biệt nếu HEAD đã thay đổi.
2. Đọc `application/dedup.py`, `application/web_import.py`, `scraping/{fetcher,html_to_latex}.py`, toàn bộ `scraping/adapters/`, UI hai tab, `application/exams.py`, `parsing/latex.py`, `docs/Packages/{MAPClass.cls,ex_test.sty}` nếu có.
3. Chạy toàn bộ pytest hiện có (không chỉ test Phase K/L). Lưu log, phân loại lỗi nền và lỗi mới. Không tự nhận PASS nếu chưa chạy.
4. Tạo `docs/PHASE_L1_BASELINE.md` có bảng traceability từ yêu cầu → code → test → kết quả.

## L1 — Chuyển HTML/MathJax/KaTeX/MathML sang pdfLaTeX an toàn và đúng ngữ nghĩa (P0)
1. Viết lại pipeline converter có trạng thái **text/math**, không thay Unicode toán thành macro math bên ngoài math mode. Các ký hiệu `∈, ≤, ≥, √, ∑, ∫, π, α, ±, ×, °` phải sinh TeX hợp lệ; ví dụ `x ∈ ℝ`, `y ≥ 5`, `30°`, `m²`, `H₂O`. Tránh `$` lồng, delimiter lỗi, mất backslash, escaping `% & # _ { } ~ ^ \\` trong văn bản.
2. Phân biệt `<sup>/<sub>` trong văn bản, công thức, đơn vị và hóa học; không xuất `^{...}`/`_{...}` trực tiếp trong text mode. Với trường hợp không thể xác định, giữ nguyên hoặc đánh dấu cần duyệt thay vì đoán sai.
3. Dùng parser HTML dạng cây (BeautifulSoup/lxml nếu dependency hợp lệ) cho KaTeX, MathJax và markup lồng; xử lý KaTeX annotation có nhiều lớp `<span>`, không dùng regex non-greedy làm parser cấu trúc chính. Hỗ trợ MathML phổ biến (`mfrac`, `msup`, `msub`, `msubsup`, `msqrt`, `mroot`, `mfenced`, `mtable`) và cảnh báo rõ khi không hỗ trợ.
4. Xử lý tiếng Việt với pdfLaTeX (T5/UTF-8 theo cấu hình thực tế), HTML entities, dấu xuống dòng, danh sách, bảng, URL và ảnh. Không làm biến dạng nội dung toán/hóa.
5. Tạo corpus >= 60 ca gồm Toán 6–12, KHTN 6–9, Vật lí 10–12, Hóa học, công thức, phân số, mũ/chỉ số, ma trận/bảng, hình ảnh, TikZ có sẵn, Unicode. Golden tests so sánh TeX kỳ vọng và compile **pdfLaTeX thật** ít nhất 20 ca đại diện, kiểm tra PDF tồn tại và log không lỗi nghiêm trọng. Không đánh đồng 'compile OK' với 'đúng ngữ nghĩa': bổ sung đối chiếu thủ công 10 ca.
6. Không tự ý bật `--shell-escape`, không cho nội dung HTML chèn preamble hoặc lệnh file I/O nguy hiểm. Cách ly đầu vào trước khi đưa vào TeX, cảnh báo khi có macro không an toàn.

## L2 — Kiểm thử adapter với nguồn web thực và tuân thủ (P0/P1)
1. Audit VietJack, Tech24, Loigiaihay: URL/domain chính xác, selectors, cấu trúc HTML, câu hỏi, đáp án, lời giải, ảnh, bảng. Phân biệt website được hỗ trợ thực tế với generic fallback.
2. Chỉ truy cập trang công khai khi robots.txt, điều khoản và quyền sử dụng cho phép. Không vượt CAPTCHA, đăng nhập, paywall, rate-limit; không sao chép/phân phối nội dung trái phép. Nếu không được phép truy cập, ghi `BLOCKED` và dùng fixture được phép sử dụng, **không** báo đã test live.
3. Với mỗi nguồn được phép, chọn >= 5 URL đa dạng (trắc nghiệm, đúng/sai, tự luận, ảnh, toán), lưu metadata URL/ngày/loại và **kết quả thống kê**, không commit nguyên văn nội dung có bản quyền. Đối chiếu thủ công ít nhất 10 câu mỗi nguồn nếu khả thi: đề bài, 4 phương án, vị trí đúng, lời giải, công thức, ảnh; báo precision/recall hoặc số đúng/tổng, số cần duyệt.
4. Adapter phải trả về trạng thái rõ ràng: `supported`, `generic_fallback`, `blocked`, `parse_failed`, `partial`, `needs_review`; không tuyên bố hỗ trợ hoàn chỉnh chỉ dựa trên fixture tự tạo.
5. Xử lý redirect, DNS rebinding, địa chỉ IPv4/IPv6 private, timeout, response quá lớn, content-type lạ, ảnh ngoài domain, URL tương đối, lazy-loaded `data-src`/`srcset`, trang thay DOM, request hủy. Bảo vệ SSRF ở cả request chính lẫn tải ảnh; không chặn UI thread.
6. Nếu ảnh không tải được: đánh dấu câu chưa hoàn chỉnh, không im lặng bỏ ảnh và không cho auto-verify.

## L3 — Độ chính xác tìm câu trùng và an toàn dữ liệu (P0/P1)
1. Tạo bộ dữ liệu có nhãn >= 300 cặp gồm: trùng nguyên văn; khác khoảng trắng/comment; hoán vị `\\choice` và `\\True`; `\\choiceTF` thay vị trí mệnh đề (phải **không** coi là hoán vị tương đương); khác số liệu/dấu âm/lũy thừa; khác hình/TikZ/asset; khác lời giải; gần trùng nhưng không trùng; câu lồng `\\immini`.
2. Đánh giá precision, recall, false-positive theo 3 cấp; mức gợi ý similarity không được tự động xóa. Trường hợp ảnh khác, số khác, đáp án đúng khác phải được cảnh báo rõ.
3. Quét file `.tex` đơn/multiple và SQLite 1k/10k/50k câu bằng dataset tổng hợp có seed, đo thời gian, RAM peak, khả năng cancel, UI responsiveness. Tránh thuật toán O(n²) toàn cục: blocking/candidate generation trước khi so sánh fuzzy.
4. Mọi thao tác xóa phải xác nhận, có backup/transaction/rollback, bảo vệ FK đề thi/bài giảng; kiểm tra chọn primary, gộp metadata, xử lý nhiều câu trùng theo nhóm. File nguồn bất biến; xuất `<name>_dedup.tex` và xác minh số câu giữ lại, asset paths, compile pdfLaTeX.
5. Cân nhắc câu trùng có cùng nội dung nhưng khác metadata/độ khó/nguồn: mặc định gợi ý gộp, không xóa không thể phục hồi.

## L4 — Staging, UX và liên kết Phase K (P1)
1. Tab Web: nhập URL/dán HTML, tiến độ, cancel, thông báo nguồn/robots, số câu trích xuất, số câu thiếu ảnh/đáp án, editor LaTeX + preview PDF, duyệt từng câu, không cho 'duyệt tất cả' với câu thiếu thông tin hoặc compile lỗi.
2. Tab trùng: lọc theo phạm vi/loại/môn, đối chiếu hai cột có highlight khác biệt, giải thích lý do trùng và độ tin cậy, thao tác giữ/xóa minh bạch; tránh block UI.
3. Tích hợp `QuestionDraft` → CSDL và Phase K: kiểm tra đủ `\\choice` 4 đối số, `\\choiceTF` giữ nguyên thứ tự, `\\shortans` đáp số, tự luận; `\\TieudeT`, `\\PhanI/II/III/TL`, các môi trường `cauhoiTN/DS/TLN/TL` và `De01...`. Xuất bản học sinh/giáo viên/đáp án độc lập; ZIP tự chứa class/style/assets và thư mục `Loigiai` khi cần.
4. E2E từ URL/HTML hợp lệ → staging → chỉnh sửa → duyệt → lưu DB → chọn câu → 4 mã đề → compile từng mã bằng pdfLaTeX → mở ZIP tại thư mục khác và compile lại. Đảm bảo câu lỗi không làm mất các câu hợp lệ.

## L5 — Regression, nghiệm thu và release
1. Chạy **toàn bộ** test suite, unit/integration/E2E, test Qt offscreen và test Windows EXE thực tế. Không sửa test để che lỗi.
2. Stress test đóng app trong khi đang fetch, tải ảnh, parse 10k câu, compile TeX; bảo đảm không treo/worker truy cập QObject đã hủy, không mất dữ liệu.
3. Báo cáo `docs/PHASE_L1_REAL_WORLD_VALIDATION_REPORT.md`: HEAD trước/sau, commit, danh sách file sửa, ma trận PASS/FAIL/BLOCKED, URL đã test (không chứa dữ liệu riêng tư), số câu kiểm tra, benchmark p50/p95 và peak RAM, compile log, lỗi còn lại, hướng dẫn tái hiện.
4. Commit tách theo L0–L5, push khi được phép; không force push. Không báo 'Production Ready' nếu chưa thử nguồn thật hợp lệ, chưa chạy regression hoặc còn P0.

## Tiêu chí nghiệm thu bắt buộc
- Không còn lỗi macro toán ngoài math mode với corpus chuẩn; PDF biên dịch được bằng **pdfLaTeX**.
- Không bỏ sót hình/đáp án mà vẫn tự đánh dấu câu hợp lệ.
- Không nhầm hoán vị `\\choiceTF` thành câu trùng tương đương; không xóa tự động.
- Đo thực tế hiệu năng 10k và 50k câu, không treo UI, có thể hủy.
- Báo cáo trung thực live test vs fixture test; tuân thủ website và bản quyền.
- Phase K không hồi quy: đúng bốn phần, xáo đúng loại câu, 4 mã đề và đáp án.
- Có log chứng minh toàn bộ test suite và Windows EXE smoke test.

## Lệnh thực thi
Hãy triển khai lần lượt L0→L5, sửa trực tiếp code, tạo test, chạy và ghi log; không chỉ viết kế hoạch. Khi hoàn thành cung cấp SHA cuối, tóm tắt thay đổi, PASS/FAIL/BLOCKED, báo cáo và hướng dẫn dùng thử với 1 file `.tex` thực tế và 1 URL được phép truy cập.
