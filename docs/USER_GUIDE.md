# Thư viện 0.5.1 — Bắt đầu từ cây CSDL

Cây **CSDL → Môn → Chương → Bài → Dạng** luôn hiện bên trái trang thư viện. Nhấp đúp để mở/đóng nhánh, bấm bài hoặc dạng để thấy các câu thuộc phạm vi đó ở giữa. Dòng **Phạm vi** cho biết đang xem ở đâu. Bấm một câu để xem nội dung toán bên phải; bấm **Sửa câu** hoặc nhấp đúp câu để mở editor. Các bản nháp ở tab editor vẫn giữ khi bạn chọn bài khác.

**Nhập TeX** chuyển tới trang nhập; chọn file rồi dùng cây ở trang nhập để gán bài/dạng và mức độ. **Phân loại** mở inspector cho câu đang xem. **Lấy vào đề** đưa các câu đã chọn sang ra đề. Các thao tác ít dùng nằm trong **Thao tác khác**. Khi không có câu, xem hướng dẫn trong trang hoặc bấm **Xem tất cả câu** để kiểm tra câu chưa phân loại.

Cây CSDL tự hiện lại khi mở trang, kể cả workspace cũ lưu trạng thái ẩn. Nút thu sidebar ở trang CSDL chỉ làm cây gọn hơn; kéo splitter để tăng chiều rộng.

# Workspace 0.5.0

Thanh icon trái chuyển CSDL, Nhập, Ra đề, Cài đặt và Bài giảng. Tooltip cho biết chức năng. Nút thư mục phía trên thu/mở sidebar; kéo vạch splitter để chia không gian. Các panel có nút đóng; mở lại bằng toolbar hoặc menu Hiển thị. Layout được lưu khi thoát.

CSDL: gõ tìm nhanh, chọn loại/mức độ/trạng thái; Ctrl/Shift để chọn nhiều. Nhấp câu để xem render, nhấp đúp để mở editor. Chọn Thẻ preview để xem bản render đã tải; chỉ câu được chọn mới biên dịch. Inspector Phân loại lưu bài/dạng, mức độ, nhãn và nguồn trực tiếp. Thẻ chưa render hiện tóm tắt; F5 cập nhật câu đang xem.

Editor: Ctrl+S lưu, Ctrl+F tìm, Ctrl+H thay thế; thanh tìm nằm trong editor. F5 biên dịch, nút Đi tới dòng lỗi chuyển tới source khi ánh xạ được, lỗi preamble/tệp phụ xem nhật ký. Thay source làm preview cũ mất hiệu lực.

Nhập: chọn tệp/thư mục → phân tích → chọn bài/dạng trên cây và mức độ → gán các câu đang chọn → tick những câu muốn nhập → Nhập câu đã chọn. Câu không tick hoặc source lỗi vẫn giữ trong hàng chờ. Toolbar hiển thị hợp lệ/lỗi/gợi ý trùng; gợi ý trùng không tự xóa.

Ra đề: chọn phạm vi trái, nhập số NB/TH/VD/VDC trong bảng thống kê, thêm vào ma trận; có thể lấy thêm câu đang chọn từ CSDL. Tạo đề ghim source/đáp án/permutation; danh sách phải là cấu trúc đề đã tạo. Preview và xuất dùng snapshot này. Bài giảng vẫn chèn qua thư viện chọn/tick, giữ revision riêng.

Bản 0.3.3: trang nhập dùng toolbar; thao tác thêm dạng, chọn mức độ, gán, nhập và đóng nằm trên toolbar icon có tooltip. Cột phải có Preview/Source, tự biên dịch nền khi chọn câu, hỗ trợ ảnh đi kèm, nhiều trang và báo lỗi không chặn phân loại. Preview dùng compiler.json và yêu cầu TeX engine đã cấu hình.

Bản 0.3.1 — Ra đề theo cây CSDL: chọn phạm vi môn/chương/bài/dạng, chọn loại câu, xem nguồn NB/TH/VD/VDC và số chưa gán mức độ. Nhập số cần lấy rồi thêm vào ma trận; lặp cho các phạm vi khác và tạo đề. Thống kê bỏ câu lưu trữ, source lỗi và câu đã chọn thủ công. Các phạm vi chồng nhau có thể dùng chung nguồn: bộ chọn kiểm tra đủ câu độc lập khi tạo đề. Có xóa hàng và tổng số câu theo mức độ.

Bản 0.3.0 — Phân loại khi nhập TeX: chọn câu (Ctrl/Shift để chọn nhiều), chọn bài hoặc dạng trên cây CSDL, chọn mức độ rồi Gán. Có gán toàn bộ danh sách, tìm cây, thêm dạng dưới bài, lọc câu chưa gán. Phân loại lưu trong hàng chờ và giữ khi sửa source; khi nhập chuyển sang metadata, liên kết cây và snapshot. Gán lại có xác nhận. Hàng chờ có nút mở lại cây phân loại. Chưa hỗ trợ tự đọc comment metadata hoặc AI phân loại; xem source ở cột phải.

Bản 0.2.7: thêm VẬT LÍ 11 (4 chương/26 bài), TOÁN 12 (5 chương/17 bài theo danh sách cung cấp), VẬT LÍ 12 (4 chương/25 bài). Cây CSDL có icon sách xanh cho môn, thư mục vàng cho chương, trang xanh lá cho bài. Schema 15 nâng cấp có backup; sửa đề khảo sát thành để khảo sát.

Bản 0.2.6: thêm TOÁN 10 (9 chương/27 bài), VẬT LÍ 10 (7 chương/34 bài), TOÁN 11 (9 chương/33 bài) theo danh sách người dùng. Schema 14 nâng cấp có backup và tự điền đúng môn/lớp/chương/bài.

Bản 0.2.5: thêm KHTN 9 (14 chương, 51 bài; Bài 1 ngoài chương) và TOÁN 9 (10 chương, 32 bài) theo danh sách người dùng. Sửa lỗi gõ dòng diện → dòng điện, aalcohol → alcohol, Mendel và ax². Schema 13 có backup trước nâng cấp; tự điền phân loại lớp 9.

Bản 0.2.4: thêm CSDL → KHTN 8 (46 bài, Bài 1 trực tiếp dưới môn và 8 chương) và TOÁN 8 (10 chương, 39 bài) theo danh sách người dùng. Tự điền môn/lớp 8/chương/bài; schema 12 nâng cấp có backup.

Bản 0.2.3: thêm CSDL → TOÁN 7 (Kết nối tri thức), 10 chương và 37 bài theo danh sách người dùng. Tự điền môn Toán, lớp 7 và chương/bài; schema 11 nâng cấp có backup.

Bản 0.2.2: thêm CSDL → KHTN 7, 10 chương và 41 bài (Bài 2–42) theo danh sách người dùng. Tự điền môn Khoa học tự nhiên, lớp 7, chương/bài; schema 10 nâng cấp có backup.

CSDL → TOÁN 6: 9 chương, 43 bài và 2 mục luyện tập chung theo danh sách người dùng. Chọn chương/bài để lọc ngân hàng; tạo câu tại mục đã chọn tự điền môn Toán, lớp 6 và chương/bài. Database nâng cấp lên schema 9 có backup trước migration.

# CSDL KHTN 6 — 0.2.1

- Mở **CSDL → KHTN 6** trên menu đầu cửa sổ. Chọn Tất cả KHTN 6, một chương, hoặc một bài để chuyển về ngân hàng và lọc câu tương ứng.
- Cây phân loại bên trái trang CSDL có KHTN 6 với 10 chương/55 bài, đúng thứ tự số. Số trong ngoặc là câu đang hoạt động của mục và toàn bộ mục con.
- Khi sửa Phân loại/Nhãn, chọn đường dẫn KHTN 6 › Chương › Bài. Môn=Khoa học tự nhiên, khối=6 và chương/bài được đồng bộ từ danh mục.
- Tạo câu mới khi đang chọn bài sẽ gán vào bài đó. Danh mục không tự tạo câu hỏi; bài chưa có câu hiển thị 0.
- Nhánh mở và bài đang chọn được lưu khi đóng/mở ứng dụng. Database cũ được backup trước khi nâng cấp schema 8; các danh mục/câu cũ giữ nguyên.

# Soạn bài giảng — 0.2.0

1. Mở Bài giảng ở drawer, bấm Tạo bài, nhập tên bài. Cây mẫu có Lý thuyết, Dạng toán, Ví dụ và nhóm Bài tập vận dụng.
2. Chọn mục trong cây, sửa tên/source TeX. Thêm mục cùng cấp/con; ↑/↓ đổi thứ tự cùng cha. Bản nháp tự lưu sau 1,5 giây; Lưu/Ctrl+S lưu ngay; Lịch sử khôi phục thành revision mới.
3. Chọn nhóm đích, mở Chèn từ ngân hàng, Tìm/Làm mới danh mục. Tick câu hoặc đặt bộ lọc/số câu/seed rồi Trích lọc để xem đề xuất. Chọn vai trò Ví dụ/Bài tập và bấm Chèn. Cho phép lặp có chủ đích nếu cần ôn lại cùng câu.
4. Câu được pin revision. Sửa source ở bài chỉ đổi bản trong bài, không sửa ngân hàng. Ghi chú giáo viên nằm ở ô riêng. Chèn hình quản lý bytes gốc trong kho assets.
5. Với từng khối chọn Hiện đầy đủ/Chỉ đề bài/Chỉ giáo viên. Ví dụ có lời giải được công khai khi Hiện đầy đủ. Bài tập mặc định Chỉ đề bài; ghi chú riêng không xuất cho học sinh.
6. Chọn Bản giáo viên/Bản học sinh, Xem trước toàn bài; ←/→ đổi trang. Có thể chọn Chỉ xuất phiếu bài tập. F5 preview, Hủy dừng compile.
7. Xuất bộ TeX+PDF, chọn thư mục. Ứng dụng tạo thư mục mới có main.tex, bai-giang.pdf, assets và manifest checksum; không ghi đè bộ cũ. Phải cài/cấu hình pdfLaTeX. Profile riêng chưa được chứng nhận gói xuất.
8. Sao lưu thư viện giữ cả bài, revisions, ảnh và gói xuất được quản lý. Review bản học sinh trước phát tài liệu, nhất là ảnh/lời giải được viết tự do.

Chưa hỗ trợ nhập đầy đủ bài giảng cũ hoặc Beamer. Nội dung hiện biên tập bằng TeX, không phải editor trực quan. Xem 19_LESSON_IMPLEMENTATION_REPORT.md.

# Điều hướng từ phiên bản 0.1.1

Cột trái là menu drawer, nút ☰ thu gọn/mở rộng. Chọn Xem CSDL, Nhập câu hỏi, Ra đề thi hoặc Cài đặt để tải trang ở cột phải. Các chức năng chính hoạt động trong cửa sổ hiện tại.

- Xem CSDL: cây phân loại, bảng câu hỏi, editor và preview. Ctrl+1 chuyển về trang này.
- Nhập câu hỏi (Ctrl+I): bấm Chọn file TeX/Chọn thư mục, theo dõi tiến trình rồi xem source/lỗi và xác nhận ghi ngay trong trang. Hàng chờ/Sửa lỗi cũng nằm ở trang này.
- Ra đề thi: chọn câu trong CSDL, chuyển trang rồi bấm Lấy câu đang chọn từ Xem CSDL, hoặc thêm hàng ma trận. Bấm Tạo đề, xem kết quả, rồi Xuất đề/Đáp án/Lời giải.
- Cài đặt: nhập đường dẫn pdfLaTeX/preamble và lưu tại trang.

Chuyển trang giữ nội dung đang nhập. Hộp chọn file và xác nhận vẫn xuất hiện khi cần. Hướng dẫn cũ phía dưới về Ctrl+I mở chọn file trực tiếp được thay bằng trang Nhập câu hỏi.

# Hướng dẫn sử dụng LaTeX Question Studio 0.1

## Bắt đầu
Mở LaTeXQuestionStudio.exe trong thư mục phát hành. Giữ nguyên thư mục _internal bên cạnh EXE. Không cần cài Python. Dữ liệu riêng ở %LOCALAPPDATA%/LaTeXQuestionStudio; chương trình không tự mở hoặc sửa DB MCPTest2020.

Bản này đã được kiểm tra trên Windows 10 với TeX Live 2026; chưa chạy trên máy Windows sạch/VM riêng. pdfLaTeX là dependency ngoài cho preview/PDF; các thao tác thư viện/nhập/tìm kiếm không cần Internet hoặc TeX.

## Nhập và sửa câu
Chọn Nhập file TeX hoặc Tệp → Nhập thư mục. Có tiến trình và Hủy. Xem source/thống kê mới-trùng-lỗi trước Ghi các câu hợp lệ. Các câu lỗi vẫn ở Tệp → Hàng chờ nhập: chọn câu, sửa bản làm việc, Kiểm tra và lưu bản sửa, rồi Ghi mục đang chọn. Byte file nguồn gốc được giữ trong archive; file đầu vào không bị sửa.

Mở câu bằng double-click bảng, hoặc Ctrl+N tạo câu mới. Ctrl+S lưu revision; Ctrl+W đóng tab, có Lưu/Bỏ/Hủy khi chưa lưu. Ctrl+F tìm, Ctrl+H thay, Ctrl+Space hoàn thành macro; undo/redo chuẩn Qt. Metadata gồm môn/khối/chương/bài/chủ đề/nguồn/nhãn, loại câu, difficulty legacy 0–4 và nhận thức NB/TH/VD/VDC. Không tự đổi 5 mức cũ sang 4 nhận thức.

Explorer: chọn node để lọc cả cây con; click phải thêm/đổi tên/xóa mục rỗng. Phân loại/Nhãn gắn câu đang mở vào node. Lưu trữ câu hỏi ẩn câu khỏi tìm kiếm/tạo đề nhưng giữ source/history. Lịch sử/Khôi phục tạo revision mới. Thư viện → Khôi phục câu lưu trữ đưa câu trở lại; backup cũng giữ câu này.

## Preview và TeX
F5 biên dịch riêng câu đang mở. Cache hợp lệ không biên dịch lại. LaTeX → Hủy biên dịch dừng process. LaTeX → Trang preview trước/tiếp duyệt tài liệu nhiều trang; scroll ngang/dọc và resize dock khi cần. Nhật ký/Tác vụ ghi lỗi và dòng source. Chuyển câu không hiển thị result cũ.

Cài đặt pdfLaTeX nhận tên pdflatex hoặc đường dẫn pdflatex.exe; preamble để trống dùng profile article tích hợp. Preamble riêng phải chứa documentclass/packages/macros và kết thúc trước begin{document}; cls/sty/tex phụ thuộc để cùng cây thư mục. Profile tích hợp hỗ trợ ex/vidu, choice/choiceTF/choiceTFt, shortans, loigiai/hdan, True, listEX, TikZ và includegraphics. Profile này không phải bản sao MAPClass/ex_test; các macro tùy chỉnh chưa biết cần preamble thật. TeX Live cần vietnam, geometry, amsmath, amssymb, graphicx, tikz, enumitem; không bật shell escape tự động.

## Tìm và so trùng
Ctrl+Shift+F tìm FTS5, hỗ trợ tiếng Việt không dấu; Bộ lọc theo metadata/type/mức độ/nhãn, trường rỗng không giới hạn. Xóa tìm kiếm/bộ lọc trở về thư viện. Phân trang 100 câu. Tìm câu trùng từ câu đang mở; score chỉ là gợi ý. Chọn một kết quả để xem, xác nhận hợp nhất mới lưu trữ bản phụ. Source/đáp án/assets/revisions bản phụ vẫn giữ nguyên, không tự xóa.

## Tạo đề
Trong bảng dùng Ctrl/Shift chọn nhiều hàng, hoặc mở một câu, rồi Tạo đề. Có thể chọn thủ công và thêm hàng ma trận (môn/khối/loại/nhận thức/số lượng). Mỗi đề tối đa 500 câu. Seed tái lập; xáo câu/phương án MCQ giữ True và đáp án. TF giữ thứ tự khẳng định. Thiếu nguồn hoặc câu chưa parse hợp lệ sẽ báo lỗi.

Xuất Đề học sinh, Đề kèm lời giải hoặc Đáp án dưới dạng .tex/.pdf. TeX kèm assets hash ở thư mục assets, cần giữ cùng nhau. Đề học sinh ẩn True/lời giải/giá trị shortans. Đề thi → Lịch sử đề xuất lại snapshot câu và đáp án đã lưu.

## Backup và giao diện
Tệp → Sao lưu tạo ZIP chứa DB, archive nguồn và assets với checksum. Phục hồi có xác nhận; ứng dụng kiểm tra checksum/schema/FK và giữ DB trước phục hồi ở backups. Đợi tác vụ nền hoàn tất trước backup/restore. Workspace/theme/cấu hình máy hiện tại được giữ riêng. Đổi giao diện trên Activity Bar; Hiển thị để bật/tắt dock. Layout/tab mở được khôi phục khi khởi động lại.

## Dữ liệu minh họa
examples/demo.tex và diagram.png gồm MCQ, đúng/sai, trả lời ngắn, tự luận/TikZ/ảnh với dữ liệu học tập mẫu. Nhập file này để thử toàn bộ luồng mà không dùng dữ liệu thật.


Preview mặc định từ bản 0.5.2 dùng MAPClass.cls và ex_test.sty trong docs. Trong Cài đặt, để trống “File preamble riêng” để dùng mẫu này; nếu đã cấu hình preamble riêng, mẫu riêng vẫn được ưu tiên. Bản EXE có sẵn class/package; máy cần cài pdfLaTeX và các gói phụ thuộc của MAPClass. Nhấn Xem trước/F5 để biên dịch lại câu đang xem.
