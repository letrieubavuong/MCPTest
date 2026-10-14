# MCPTest — PHASE K: Chuẩn hóa cấu trúc đề thi MAPClass/ex_test, xáo mã đề và kiểm thử đầu-cuối

## 0. Vai trò và phạm vi
Bạn là Codex, phụ trách sửa **mã nguồn thực** trong repository `letrieubavuong/MCPTest` trên nhánh hiện hành. Trước tiên kiểm tra HEAD, `MAPClass.cls`, `ex_test.sty` thực tế và các module exam/question bank/import/export/tests. Không suy đoán cú pháp của class; tìm định nghĩa thật của `\TieudeT`, `\PhanI`, `\PhanII`, `\PhanIII`, `\PhanTL`, `cauhoiTN`, `cauhoiDS`, `cauhoiTLN`, `cauhoiTL`. Nếu file class/style không có trong repo, yêu cầu/định vị dependency chuẩn, không tự định nghĩa giả để che lỗi. Giữ pdfLaTeX làm engine chính. Không phá dữ liệu hiện có; cần migration an toàn nếu thay schema. Sửa từ domain model, builder, serializer, UI đến test; không chỉ thay chuỗi xuất TeX.

## 1. HỢP ĐỒNG CẤU TRÚC ĐỀ THI BẮT BUỘC
Phần thân đề, sau preamble/document setup tương thích MAPClass, phải được sinh theo đúng thứ tự, chỉ sinh phần có câu hỏi nếu template cho phép (cấu hình rõ ràng):

```tex
\TieudeT{TIÊU ĐỀ BÀI THI}
\PhanI
\begin{cauhoiTN}{De01}
% Các câu hỏi môi trường ex có \choice
\end{cauhoiTN}
\PhanII
\begin{cauhoiDS}{De01}
% Các câu hỏi môi trường ex có \choiceTF (hoặc biến thể đã được chứng thực)
\end{cauhoiDS}
\PhanIII
\begin{cauhoiTLN}{De01}
% Các câu hỏi môi trường ex có \shortans
\end{cauhoiTLN}
\PhanTL
\begin{cauhoiTL}{De01}
% Các câu hỏi tự luận môi trường ex, không chứa choice/choiceTF/shortans
\end{cauhoiTL}
```

`De01` là **tham số môi trường** theo chuẩn class thực tế; không mặc định đó là mã hiển thị trên giấy nếu class dùng nó cho mục đích khác. Kiểm tra quy tắc giá trị hợp lệ và thiết kế mapping mã đề rõ ràng (`De01`, `De02`, ...) nếu được class hỗ trợ; không hardcode mọi đề là `De01`. Không bọc `\begin{ex}` lặp, không làm rơi `\loigiai`, hình TikZ, `\includegraphics`, `\immini`, bảng, macro chuyên môn. Không chèn lệnh đánh số câu thủ công khi môi trường tự đánh số. Nếu class cần reset counter giữa phần/mã đề, làm đúng theo định nghĩa class.

## 2. QUY TẮC XÁO ĐỀ — BẤT BIẾN
- **Phần I — MCQ (`\choice`)**: cho phép xáo thứ tự câu hỏi trong chính Phần I; cho phép xáo thứ tự các phương án A/B/C/D **cùng nội dung và cờ đáp án đúng `\True`**, không làm thay đổi tính đúng của đáp án. Câu có lựa chọn không phải 4 đáp án hoặc macro phức tạp: parser phải chứng minh có thể xáo an toàn; nếu không thì giữ nguyên hoặc chặn với thông báo, không sửa regex mù.
- **Phần II — Đúng/sai (`\choiceTF`, `\choiceTFt` nếu hỗ trợ)**: **CHỈ xáo thứ tự các câu hỏi trong phần**. Tuyệt đối **không xáo thứ tự các mệnh đề a,b,c,d**, không hoán đổi cờ đúng/sai, không biến đổi nội dung từng ý. Đáp án đúng/sai vẫn theo vị trí gốc của bốn mệnh đề.
- **Phần III — Trả lời ngắn (`\shortans`)**: chỉ xáo thứ tự câu hỏi trong phần; không xáo nội dung đáp án hoặc tham số tùy chọn của `\shortans`.
- **Phần tự luận**: mặc định **giữ nguyên thứ tự** như người dùng chọn/sắp xếp, không tự xáo; chỉ thay đổi nếu sau này có tùy chọn nghiệp vụ riêng được người dùng chấp thuận.
- Không bao giờ chuyển câu giữa các phần khi xáo. Không xáo câu chứa ràng buộc nhóm/phụ thuộc (ví dụ cùng dữ kiện, câu nối tiếp) nếu không có metadata và thuật toán bảo toàn nhóm. Ghi nhận nguyên nhân không xáo.
- Xáo đa mã đề bằng PRNG có seed xác định; cùng seed + cùng snapshot dữ liệu + cùng version thuật toán => kết quả tái lập. Mỗi mã đề có seed/manifest và bảng ánh xạ `question_id`, thứ tự câu, thứ tự phương án, đáp án mới. Tránh hai mã đề trùng hoàn toàn nếu có đủ khả năng hoán vị; cảnh báo nếu không thể tạo đủ mã đề khác nhau. Không dựa vào global random state.

## 3. PHÂN LOẠI VÀ MÔ HÌNH DỮ LIỆU
Tách rõ `question_type`: MCQ / TRUE_FALSE / SHORT_ANSWER / ESSAY. Xác định bằng parser LaTeX nhận biết ngoặc lồng, comment, macro, môi trường, chứ không dựa vào substring/regex đơn giản. Phân biệt macro trong lời giải, nội dung verbatim, TikZ, comment với macro điều khiển loại câu. Nếu một câu có nhiều marker mâu thuẫn, đưa vào danh sách cần xử lý, không tự phân loại sai. Tôn trọng type đã lưu, nhưng xác minh trước export; UI cho phép giáo viên sửa loại và cảnh báo mismatch. Giữ UUID/source/revision/assets. Có thể lưu nhóm câu không được tách/xáo.

## 4. BUILDER / UI
- Builder chia 4 phần có nhãn rõ: Phần I Trắc nghiệm; Phần II Đúng/Sai; Phần III Trả lời ngắn; Phần Tự luận. Hiển thị số câu, thứ tự và trạng thái hợp lệ từng phần.
- Kéo-thả/sắp xếp câu **trong cùng phần**, thêm/xóa/chuyển phần có xác nhận và kiểm tra type; thao tác chọn thẻ không gọi dựng lại toàn bộ `sync_cards()`; cập nhật state tại chỗ và đo latency.
- Cài đặt số mã đề, seed, xáo thứ tự câu MCQ/TF/shortans, xáo phương án MCQ; tự luận giữ nguyên. Nút xem trước từng mã đề, bảng đáp án tương ứng; UI thể hiện rõ TF không xáo mệnh đề.
- Cho phép ẩn phần rỗng theo cấu hình nhưng bảo đảm cú pháp class; không sinh tiêu đề/section rỗng ngoài ý muốn. Tiêu đề lấy từ trường nhập và escape/validate LaTeX theo chính sách rõ ràng (không biến title thành injection).

## 5. SERIALIZER VÀ XUẤT ĐỀ
Tạo một serializer duy nhất sinh cấu trúc trên, dùng chung cho PDF/TeX/ZIP, student/teacher và từng mã đề. Không có nhiều nhánh xuất sinh cấu trúc khác nhau. Xuất từng mã đề vào thư mục riêng (`De01/`, `De02/`, ...) với `de-hoc-sinh.tex/pdf`, `de-giao-vien.tex/pdf` và `answer-key` tương ứng; tên file chính xác có thể theo convention hiện hữu, nhưng mapping phải nhất quán. ZIP portable có assets và class/style phụ thuộc hợp lệ; dùng đường dẫn tương đối; không lộ lời giải/đáp án trong bản học sinh, kể cả file phụ trợ, log, manifest public hoặc macro tùy chỉnh. Tách manifest nội bộ và gói phát cho học sinh nếu cần. Kiểm tra đáp án sau xáo dựa trên AST/metadata, không suy đoán chữ cái cũ. Với `\choiceTF` giữ vector đáp án bốn ý, với shortans giữ nguyên giá trị và cú pháp. Xuất answer key giáo viên dễ đối chiếu theo mã đề và số câu. Cảnh báo khi nội dung có thể tiết lộ đáp án qua text/hình (không hứa phát hiện tự động mọi trường hợp).

## 6. KẾ HOẠCH TRIỂN KHAI
**K0 — Audit:** Xác định định nghĩa macro/môi trường từ MAPClass.cls/ex_test.sty, truy dấu các điểm xây đề, phân loại, xáo, xuất, UI; lập `docs/PHASE_K_BASELINE.md` và bảng khác biệt actual vs required. Chụp mẫu TeX/PDF hiện tại.

**K1 — Domain + parser:** Chuẩn hóa 4 loại câu, phát hiện xung đột, nhóm câu, thứ tự và mapping; test parser với nested braces, comment, `\immini`, TikZ, `\choiceTFt`, `\shortans[...]{...}`, macro custom, UTF-8.

**K2 — Shuffle engine:** PRNG deterministic, đúng ma trận quyền xáo; AST-safe permutation MCQ, bảo toàn `\True`, đáp án và lựa chọn có macro phức tạp; không xáo TF statements; unit/property tests 100+ seeds, duplicates, group constraints.

**K3 — Serializer:** Sinh đúng bốn phần và các environment; title, empty parts, counters, DeXX; student/teacher, answer key; kiểm thử snapshot/golden-file so với cấu trúc chuẩn. Biên dịch thật qua pdfLaTeX với class/style thực, không thay bằng mock giả. Nếu thiếu dependency, báo blocker và không đánh dấu pass.

**K4 — Builder UI:** Bốn khu vực, chọn/sắp xếp câu, tùy chọn mã đề, preview theo mã đề, hiệu năng khi chọn câu; sửa `sync_cards()` tránh tái tạo widget hàng loạt. Kiểm tra 1366×768, 1600×900, 1920×1080, scaling 125/150% nếu có thể.

**K5 — Export E2E:** 1, 2, 4, 8 mã đề; cả 4 loại câu, TikZ, ảnh, bảng, công thức, bài có nhóm; ZIP di động giải nén thư mục khác và biên dịch độc lập; xác minh bản học sinh không chứa đáp án, bản giáo viên có answer key khớp từng câu. Regression dữ liệu đề cũ/migration.

**K6 — QA & Release:** pytest toàn bộ, test stress shutdown, benchmark chọn thẻ (p50/p95/max), benchmark tạo 4 mã đề 40–100 câu, Windows EXE smoke; tạo `docs/PHASE_K_EXAM_STRUCTURE_REPORT.md` kèm ảnh thật, log test, các TeX mẫu và SHA commit. Không tự tuyên bố production-ready khi còn P0/P1. Commit theo K0–K6, push không force, không làm mất thay đổi người dùng.

## 7. TIÊU CHÍ NGHIỆM THU BẮT BUỘC
1. Mỗi file đề có `\TieudeT`, `\PhanI/II/III/TL` và `cauhoiTN/DS/TLN/TL` đúng thứ tự, tham số mã đề hợp lệ theo class; 4 loại câu nằm đúng phần.
2. `\choice` xáo câu và đáp án an toàn; `\choiceTF` chỉ xáo câu, **không bao giờ xáo bốn ý**; `\shortans` chỉ xáo câu; tự luận không xáo.
3. Mỗi mã đề có đáp án khớp với PDF/TeX, tái lập được bằng seed; không rò rỉ đáp án trong gói học sinh.
4. Biên dịch pdfLaTeX thật thành công trên các bộ mẫu có hình TikZ/ảnh và câu hỏi chuẩn ex_test; ZIP portable hoạt động sau khi di chuyển thư mục.
5. Không phá đề cũ, câu hỏi cũ, revision, assets, hoặc tính năng bài giảng; test hồi quy pass.
6. UI thao tác chọn câu không tái tạo toàn bộ widget, không block event loop; báo cáo đo đạc trung thực, không gọi thời gian callback là FPS.
7. Nếu một điểm chưa xác minh được (đặc biệt macro class), nêu blocker chính xác, không tạo workaround giả hoặc tuyên bố đã xong.

## 8. KẾT QUẢ CẦN BÀN GIAO
- Mã nguồn + test + migration (nếu có) đã commit/push.
- `docs/PHASE_K_BASELINE.md`, `docs/PHASE_K_EXAM_STRUCTURE_REPORT.md`.
- Bộ mẫu `.tex`, PDF giáo viên/học sinh, answer keys cho De01–De04, gói ZIP portable, screenshot UI, log pytest/benchmark.
- SHA cuối, danh sách file thay đổi, những giới hạn chưa giải quyết.

**BẮT ĐẦU:** audit repo và file class/style trước; triển khai tuần tự K0–K6. Không chỉ soạn báo cáo hoặc UI mockup.
