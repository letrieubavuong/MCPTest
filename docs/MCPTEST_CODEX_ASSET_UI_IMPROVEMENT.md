# CODEX MASTER PROMPT — MCPTest: LaTeX Asset Integrity & Question Bank UX

Repository: https://github.com/letrieubavuong/MCPTest

## Mục tiêu

Cải thiện ứng dụng ngân hàng câu hỏi LaTeX Python/PySide6 hiện tại theo hai ưu tiên P0:
1. Câu hỏi đã nhập thành công phải độc lập với đường dẫn hình ảnh/tài nguyên nguồn, kể cả khi người dùng di chuyển, đổi tên hoặc xóa thư mục nguồn.
2. Giao diện nhập, kiểm tra và quản lý câu hỏi phải dễ sử dụng, ưu tiên preview đã render, phát hiện và sửa tài nguyên thiếu ngay trong UI.

**Không viết lại ứng dụng, không thay đổi nghiệp vụ đúng, không làm mất dữ liệu.**

## Thực trạng cần xác minh trong code

- `application/importing.py`: `ImportService.stage()` hiện sao chép file được tìm thấy vào `data_dir/assets` với tên dựa trên SHA-256; resolver tìm ảnh chủ yếu theo `path.parent / reference`, thử `.pdf/.png/.jpg/.jpeg` khi không có đuôi.
- `persistence/database.py`: đã có `assets`, `question_assets`.
- `preview/compiler.py`: có logic thay thế tham chiếu `\includegraphics` để biên dịch bằng bản nội bộ, cache preview và `-no-shell-escape`.
- `application/exams.py`: đã gom tài nguyên ảnh khi tạo đề.
- `ui/main_window.py`: có preview bất đồng bộ, kiểm soát kết quả cũ.

Kiểm tra lại HEAD vì code có thể đã thay đổi. Không coi các nhận xét trên là kết luận tuyệt đối cho phiên bản mới.

## Quy tắc bất biến

1. Giữ nguyên nội dung LaTeX gốc, lưu mapping tài nguyên tách biệt; không rewrite phá hủy nguồn.
2. Không dùng đường dẫn tuyệt đối của máy nhập làm phụ thuộc runtime sau khi nhập thành công.
3. Asset identity dựa trên SHA-256 nội dung, không dựa trên tên file. Hai ảnh cùng tên khác nội dung phải là hai asset khác nhau.
4. Nhiều câu dùng chung ảnh được phép tham chiếu cùng asset; không xóa asset khi còn bất kỳ liên kết, revision, snapshot hoặc bản xuất cần dùng.
5. Không nhập câu với trạng thái “sẵn sàng” nếu thiếu phụ thuộc bắt buộc; cho phép lưu nháp/cần sửa nếu người dùng chọn.
6. Không sửa đáp án, lời giải, TikZ, metadata, liên kết chương/bài hiện hữu.
7. Không tự động chạy mã từ nguồn nhập; duy trì `-no-shell-escape`, kiểm soát path traversal, symlink, kích thước file và phạm vi thư mục được cấp phép.
8. Bảo toàn khả năng biên dịch pdfLaTeX và tương thích MAPClass/ex_test; không tuyên bố PASS nếu chưa kiểm thử thực tế.
9. Không tự động commit/push; không ghi đè thay đổi chưa commit.

## PHASE 0 — Audit và lập kế hoạch ngắn

- Kiểm tra Git HEAD, working tree, schema/migrations và test hiện có.
- Truy vết toàn bộ luồng `source .tex -> parse -> stage -> confirm -> asset store -> preview -> exam export -> backup/restore`.
- Liệt kê các điểm có thể mất ảnh, sai ảnh, phụ thuộc đường dẫn gốc, lưu asset rác, thiếu liên kết hoặc lỗi khi chuyển máy.
- Tạo `docs/ASSET_UX_AUDIT.md` với file/hàm, bằng chứng, mức P0/P1/P2 và kế hoạch migration tương thích ngược.

## PHASE 1 — Asset Resolver hoàn chỉnh (P0)

Xây dựng một resolver dùng chung cho import, preview, editor, exam export và lesson export, thay vì mỗi nơi tự xử lý khác nhau.

Hỗ trợ:
- `\includegraphics{image}`, `\includegraphics[width=...]{dir/image.png}`, ảnh có/không có phần mở rộng; thứ tự thử phần mở rộng phù hợp pdfLaTeX.
- `\graphicspath{{images/}{figures/}}`, kể cả được khai báo trong preamble hoặc file nguồn liên quan.
- Nguồn gồm nhiều file `.tex` và cấu trúc thư mục; `\input{...}`/`\include{...}` cần có dependency graph, phát hiện vòng lặp và giới hạn độ sâu.
- TikZ inline không yêu cầu file ảnh; `\input{figures/chart.tex}` là dependency riêng; hỗ trợ các file `.pdf/.png/.jpg/.jpeg/.tex` và các định dạng thực tế được xác nhận.
- Macro tự định nghĩa có tham chiếu tài nguyên: phát hiện trường hợp phổ biến một cách an toàn; với macro động không thể xác định tĩnh, đánh dấu `NEEDS_REVIEW`, không đoán.
- Phân biệt thiếu file, nhiều ứng viên, file bị chặn, định dạng không hỗ trợ và dependency động.

Thiết kế dữ liệu có `original_reference`, `resolved_asset_id`, `source_context`, `dependency_type`, `resolution_status` và thông tin nguồn gốc khi cần. Ưu tiên mở rộng schema hiện có, dùng migration an toàn, giữ tương thích câu hỏi cũ.

**Không âm thầm chọn ảnh khi có nhiều file trùng tên hợp lệ.** Cho người dùng xác nhận lựa chọn.

## PHASE 2 — Kho tài nguyên độc lập (P0)

- Tiếp tục dùng content-addressed storage SHA-256; đường dẫn tương đối theo `data_dir` (có thể phân cấp theo prefix hash).
- Sao chép và xác minh checksum trước khi ghi nhận asset hoàn tất; dùng ghi tạm + atomic replace khi khả thi.
- Không phụ thuộc thư mục ảnh nguồn sau khi import thành công.
- Thiết kế staging tạm để hủy nhập không tạo rác lâu dài; garbage collection chỉ sau khi kiểm tra tham chiếu, có dry-run, báo cáo và cơ chế an toàn.
- Xác minh cả file vật lý, hash, bản ghi DB, quan hệ question-assets; cung cấp chức năng quét/sửa liên kết thiếu.
- Nếu file ảnh gốc thay đổi sau khi nhập, ngân hàng không tự đổi ảnh; cập nhật asset là thao tác rõ ràng, có kiểm soát phiên bản và tác động tới câu liên quan.

## PHASE 3 — Import Review UI (P0)

Thiết kế màn hình nhập theo quy trình:
1. Chọn một/nhiều `.tex` hoặc thư mục dự án (kèm cây ảnh và file phụ thuộc).
2. Phân tích số câu, loại câu, đáp án, lỗi cú pháp và dependency.
3. Bảng danh sách câu: thumbnail đã render, trạng thái `READY`, `MISSING_ASSET`, `AMBIGUOUS_ASSET`, `NEEDS_REVIEW`, `INVALID_LATEX`, `DUPLICATE`.
4. Inspector bên phải: code LaTeX, preview, danh sách tài nguyên, nguồn gốc, lỗi cụ thể.
5. Thao tác `Chọn lại ảnh`, `Thêm thư mục tìm kiếm`, `Áp dụng cho các tham chiếu tương tự`, `Bỏ qua`, `Lưu nháp`, `Nhập câu hợp lệ`.
6. Xác nhận kết quả và thống kê nhập.

Không mở nhiều dialog chồng nhau. Tác vụ nặng chạy nền, có tiến trình, hủy an toàn và không hiển thị preview cũ khi đổi câu nhanh. Không thay đổi layout ngoài phạm vi khi chưa cần thiết.

## PHASE 4 — Visual Question Library & Editor (P1)

- Dùng PySide6, shell kiểu IDE: explorer môn/lớp/chương/bài, vùng danh sách câu, preview/inspector, bottom panel lỗi.
- Danh sách có chế độ compact và card thumbnail; mặc định giáo viên xem nội dung render, không bắt buộc đọc LaTeX thô.
- Lọc câu có ảnh, thiếu ảnh, lỗi biên dịch, cần sửa, trùng nội dung, chưa phân loại.
- Editor LaTeX + preview song song, tab nhiều câu, Ctrl+S, cảnh báo chưa lưu, hiển thị lỗi gắn câu.
- QSplitter resize/ẩn panel, nhớ trạng thái, light/dark; hỗ trợ 1366x768, 1600x900, 1920x1080.
- Tái sử dụng widget hiện có; tách dần `main_window.py`, tránh refactor hàng loạt.

## PHASE 5 — Xuất đề và bài giảng portable (P0/P1)

- Mọi thao tác preview/xuất đề phải dùng resolver và asset manifest thống nhất.
- Snapshot đề cần cố định đúng phiên bản nội dung và asset được chọn; không đổi ảnh khi nguồn ngoài thay đổi.
- Khi xuất `.tex`, xuất kèm thư mục tài nguyên và dependency cần thiết, dùng đường dẫn tương đối; cung cấp tùy chọn ZIP portable.
- Kiểm tra trước xuất: tài nguyên thiếu, macro chưa giải quyết, profile MAPClass/ex_test thiếu; báo chính xác câu nào lỗi.
- Kiểm thử file xuất sau khi sao chép sang thư mục/máy khác không có thư mục nguồn cũ.
- Bảo đảm chế độ đề học sinh không rò đáp án/lời giải.

## PHASE 6 — Quản lý kho, di chuyển và backup (P1)

Thêm `Cài đặt > Quản lý tài nguyên`:
- Thống kê số asset, dung lượng, số asset được chia sẻ, số thiếu/hỏng, asset không còn liên kết.
- Quét integrity và xuất báo cáo.
- Di chuyển kho dữ liệu bằng quy trình `copy -> verify SHA-256 -> switch config -> smoke test -> giữ bản cũ đến khi xác nhận`.
- Sao lưu toàn bộ DB, assets, preamble/profile và dependency cần thiết; backup manifest có checksum; khôi phục kiểm tra checksum trước khi kích hoạt.
- Không khuyến nghị chỉ backup file SQLite.

## PHASE 7 — Test và benchmark

Bắt buộc thêm integration tests cho:
1. Nhập ảnh relative path và ảnh không có extension.
2. `\graphicspath` nhiều thư mục.
3. Hai ảnh cùng tên khác nội dung.
4. Hai câu dùng chung một ảnh.
5. `\input` TikZ rời và nested input.
6. Macro động không resolve được: cảnh báo thay vì tự chọn.
7. Di chuyển/đổi tên/xóa thư mục ảnh gốc sau khi nhập: preview và export vẫn hoạt động.
8. Di chuyển toàn bộ `data_dir` có kiểm chứng integrity.
9. Hủy import, retry, import lại, migration DB cũ.
10. Asset bị xóa/hỏng trong kho nội bộ: phát hiện và báo đúng câu.
11. Xuất đề ZIP sang thư mục mới và compile độc lập bằng pdfLaTeX.
12. Không lộ đáp án trong PDF học sinh.
13. Đường dẫn `../`, symlink ngoài phạm vi, tệp quá lớn và input cycle.
14. Import 1.000/10.000 câu có asset; đo thời gian, RAM và độ mượt UI.

Không đánh dấu PASS cho test tích hợp Windows/TeX nếu môi trường không có đủ dependency. Ghi `BLOCKED` kèm lý do.

## PHASE 8 — Báo cáo nghiệm thu

Tạo `docs/ASSET_UX_IMPLEMENTATION_REPORT.md` gồm:
- HEAD và working tree ban đầu.
- Kiến trúc cũ/mới, migration.
- File thay đổi và các hành vi giữ nguyên.
- Test pass/fail/blocked; số liệu benchmark thật.
- Ảnh chụp UI nếu có môi trường đồ họa.
- Checklist kiểm thử thủ công Windows.
- Các rủi ro còn lại và phương án rollback.

## Cách triển khai

Làm tuần tự, ưu tiên PHASE 0–3 và 5 trước khi đánh bóng UI. Sau mỗi phase chạy test liên quan và regression test. Không thay đổi dữ liệu người dùng thật khi thử nghiệm; dùng fixture/copy. Không tự động commit/push. Nếu gặp quyết định nghiệp vụ có nguy cơ mất dữ liệu, dừng và trình bày lựa chọn.

**Tiêu chí nghiệm thu cao nhất:** Nhập một câu chứa `\includegraphics` từ thư mục A, sau đó đổi tên/di chuyển/xóa thư mục A; câu trong ngân hàng vẫn render đúng, xuất đề đúng và có thể sao lưu/khôi phục trên máy khác mà không cần A.
