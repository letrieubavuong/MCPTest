# MCPTest — Phase M.1: Lesson Reliability & Real-World Acceptance

## Vai trò và mục tiêu
Bạn là Codex đang làm việc trên repository `letrieubavuong/MCPTest`. Tiếp tục từ Phase M (commit tham chiếu `fbba8c1cbf4c7b5137679e151ea606df3bbab32b`), nhưng **kiểm tra HEAD trước khi sửa**. Mục tiêu là sửa các rủi ro mất nội dung, lỗi nhập/xuất LaTeX và độ tin cậy của workspace Bài giảng; không thêm tính năng ngoài phạm vi hoặc chỉ thay đổi giao diện hình thức.

**Ràng buộc:** Windows, Python/PySide6/SQLite, TeX Live **pdfLaTeX**, `MAPClass.cls`, `ex_test.sty`, TikZ, `\includegraphics`; không bắt buộc XeLaTeX/LuaLaTeX; bảo toàn DB schema 19, bài giảng cũ, pinned revisions, snapshot và thư mục `LyThuyet/`, `DangToan/`, `BTVD/`. Không được sửa dữ liệu người dùng trực tiếp trong quá trình test. Làm việc trên branch riêng, commit theo từng mục và chỉ push khi test đạt.

## Bằng chứng audit cần xác minh
- `src/latex_question_studio/application/legacy_lesson_importer.py`: `coverage = min(100.0, max(50.0, ...))` che giấu tỷ lệ bảo toàn dưới 50%; cách đếm ký tự không chứng minh round-trip.
- Parser heading dùng regex `\\section...\{(?P<title>[^}]+)\}` không xử lý ngoặc lồng nhau.
- Parser môi trường dùng regex `\\begin{...}(.*?)\\end{...}` có nguy cơ cắt sai môi trường lồng nhau; chưa chứng minh xử lý `\input`, `\include`, macro và tài nguyên phụ thuộc.
- `docs/PHASE_M_LESSON_WORKSPACE_REPORT.md` báo 28/28 test bài giảng, **không đồng nghĩa** full-suite regression hay kiểm thử tài liệu thật.
- Kiểm tra `lesson_page.py`, `lessons.py`, `ui/wysiwyg.py`, compiler, AssetStore, migrations và tests liên quan trước khi thiết kế sửa.

## M1.0 — Baseline có thể tái lập
1. Ghi HEAD SHA, Python/PySide6/TeX Live/pdfLaTeX, OS, trạng thái working tree; lập `docs/PHASE_M1_BASELINE.md`.
2. Chạy toàn bộ `pytest` và nhóm bài giảng riêng; báo số pass/fail/skip, thời gian và lỗi nguyên văn, không suy diễn.
3. Mở và chụp giao diện thật ở 1366×768 và 1920×1080 (không dùng ảnh mockup thay ảnh app); đo thời gian mở bài, lưu, preview, export, peak RSS.
4. Sao lưu DB fixture schema 19 và xác minh restore trước migration.

## M1.1 — Importer an toàn, bảo toàn nguồn
1. Thay chỉ số coverage giả bằng phép đo trung thực: byte/segment provenance, danh sách đoạn được map, đoạn raw chưa map, dependency chưa giải quyết. Tỷ lệ có thể là 0%, không dùng floor 50%; chỉ báo 100% khi có bằng chứng đầy đủ.
2. Thiết kế tokenizer/scanner cân bằng ngoặc và môi trường LaTeX (hoặc parser đã kiểm chứng) để nhận diện `\section`, `\subsection`, `\subsubsection`, `\begin{ex}`, `\begin{vidu}`, `\begin{vd}`, `\begin{bt}`, `\loigiai`, các môi trường lồng nhau; bỏ qua comment/escaped delimiters đúng ngữ cảnh. Không dùng regex non-greedy làm parser tổng quát.
3. Giữ nguyên source chưa hiểu trong raw blocks kèm source span/line, warning và review; tuyệt đối không bỏ âm thầm lý thuyết, preamble, macro, bảng, TikZ, hình, lời giải hoặc thứ tự.
4. Hỗ trợ `\input`/`\include` theo relative path, chuỗi phụ thuộc nhiều cấp, phát hiện vòng lặp, missing file, path traversal, file ngoài thư mục được phép, BOM/encoding; cho giáo viên quyết định khi không thể resolve. Không chạy shell escape hoặc code không tin cậy.
5. Asset staging: sao chép PNG/JPG/PDF và đường dẫn tương đối có dấu/khoảng trắng, thư mục con; hash/checksum, kiểm tra file thiếu, xử lý `\graphicspath` khi khả thi. Không tự thay tham chiếu mơ hồ. TikZ giữ source và dependency.
6. Tạo **dry-run import**: thống kê khối, cảnh báo, preview nguồn và các đoạn chưa map; chỉ commit sau khi giáo viên xác nhận; transaction rollback khi lỗi. Không ghi đè tài liệu đã có.
7. Thêm round-trip kiểm chứng: nhập → lưu → đóng/mở → xuất `.tex`/ZIP → biên dịch pdfLaTeX; đối chiếu các segment nội dung quan trọng và asset checksums. Nếu không thể bảo toàn đầy đủ, gắn `needs_review`, không quảng bá thành công.

## M1.2 — An toàn dữ liệu và bản học sinh
1. Kiểm tra pinned question revision, local overrides, autosave khi đổi bài/đóng app, undo/redo, sửa đồng thời và restore; không cập nhật ngược ngân hàng ngoài thao tác chủ động.
2. Kiểm tra policy theo khối `full`/`question`/`private` cho ví dụ, bài tập, shortans, TF, tự luận. Bản học sinh có thể giữ lời giải ví dụ công khai theo cấu hình, nhưng phải loại ghi chú riêng/đáp án bị ẩn khỏi **source, file phụ, manifest và PDF**, không chỉ ẩn bằng macro.
3. Với macro chưa chứng nhận hoặc không thể chứng minh loại lời giải an toàn: **fail closed**, báo vị trí khối và cho sửa; không xóa bừa macro tùy chỉnh làm hỏng nội dung.
4. Export không ghi đè bản đã phát hành; snapshot/checksum/revision bất biến; sao lưu/khôi phục đầy đủ bài, assets và bản phát hành.

## M1.3 — Trải nghiệm workspace thực tế
1. Test chuỗi thao tác bằng GUI thật: tạo bài → lý thuyết → dạng toán → ví dụ → chèn nhiều câu từ ngân hàng → ảnh/TikZ → preview → save/reopen → xuất học sinh/giáo viên.
2. Kiểm tra splitter 1366×768, 1920×1080 và scale 125%/150%: không mất nút quan trọng, không che editor; trạng thái ẩn/hiện preview được giữ hợp lý.
3. Preview phải không chặn UI, debounce/hủy job cũ, báo lỗi compile có line/block và không hiển thị PDF lỗi thời như bản mới.
4. Drawer câu hỏi: tìm kiếm/filter/multi-select, vị trí chèn đúng khối, giữ thứ tự sư phạm, không xáo ngẫu nhiên ngoài yêu cầu, cảnh báo lặp; kiểm tra 1k/10k câu và latency.
5. Nếu `VisualLatexEditor` không hỗ trợ round-trip macro/TikZ/ex_test thì chỉ cho phép thao tác an toàn, hiển thị cảnh báo rõ và không tự viết lại source.

## M1.4 — Bộ fixture tài liệu thật và kiểm thử hồi quy
- Tạo fixture có quyền sử dụng hoặc do dự án tự biên soạn, tối thiểu:
  - Toán 8: công thức, `align`, bảng, tiêu đề có macro và ngoặc lồng nhau.
  - KHTN 9: TikZ khúc xạ, `\includegraphics` từ thư mục con, chú thích và tiếng Việt.
  - Vật lí 10: nhiều file `\input`, hình đồ thị, ví dụ `\loigiai`, `ex_test`.
  - Một tài liệu có môi trường lồng nhau; một tài liệu thiếu ảnh; một tài liệu có `\input` vòng lặp; một tài liệu macro không nhận diện; một file hỏng cú pháp.
- Viết test unit/parser, property/metamorphic nếu phù hợp, integration DB/AssetStore, GUI smoke, pdfLaTeX compile thật và regression **toàn repo**.
- Không dùng fixture quá đơn giản để chứng minh nhập được tất cả file LaTeX. Phân biệt `passed`, `partial/needs_review`, `blocked`, `failed`.

## Tiêu chí nghiệm thu bắt buộc
1. Không mất âm thầm bất kỳ segment nguồn nào: mapped hoặc raw/needs_review có trace.
2. Coverage không giả tạo; test cố tình làm mất 70% nội dung phải báo chính xác, không được 100% hay floor 50%.
3. Nested environment và heading brace-balanced có unit tests; `\input` nhiều cấp và cycle/missing file có test.
4. Ít nhất ba bài giảng đại diện biên dịch bằng **pdfLaTeX** sau export và sau di chuyển thư mục; checksum ảnh đúng.
5. Bản học sinh không rò lời giải/ghi chú riêng trong `.tex`, assets phụ hoặc PDF; test âm tính.
6. Schema 19 cũ mở/lưu/restore được; không thay đổi snapshot đã phát hành.
7. Full pytest báo kết quả thật, không chỉ 28 bài giảng; nếu fail/skip ghi rõ nguyên nhân.
8. GUI smoke có ảnh chụp thật 1366×768 và 1920×1080; không nhận ảnh render giả.
9. Không có P0/P1 chưa xử lý trong phạm vi; nếu còn, báo `BLOCKED` thay vì hoàn thành.

## Quy trình commit và bàn giao
- Tách commit: `M1.0 baseline`, `M1.1 parser/coverage`, `M1.2 safety`, `M1.3 UX`, `M1.4 tests/report`.
- Không sửa test để né lỗi; không xóa dữ liệu hay đổi cấu trúc DB khi chưa có migration/backup.
- Viết `docs/PHASE_M1_LESSON_RELIABILITY_REPORT.md` gồm: HEAD trước/sau, bảng issue P0/P1/P2, root cause, file/line sửa, bảng testcase + pass/fail/skip, số liệu performance, ảnh thật, đường dẫn artifacts, compile logs, danh sách hạn chế và SHA commit.
- Commit và push theo chính sách repo; nếu không thể chạy Windows/pdfLaTeX hoặc không có fixture thực, nói rõ chưa kiểm chứng và dừng ở trạng thái phù hợp.

**Ưu tiên:** tính đúng và bảo toàn dữ liệu > bảo mật tài liệu học sinh > khả năng sử dụng > hiệu năng > hình thức. Không tự tuyên bố “100% tương thích” nếu thiếu bằng chứng.
