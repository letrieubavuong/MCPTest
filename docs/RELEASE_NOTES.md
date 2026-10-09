# 0.5.2

- Preview mặc định dùng nguyên bản MAPClass + ex_test do người dùng cung cấp.
- Đóng gói class/package trong EXE, cache nhận biết thay đổi mẫu.
- Gói bài giảng kèm dependency để biên dịch TeX lại.

# 0.5.1 — Khôi phục hướng sử dụng thư viện

- Cây CSDL luôn hiện khi mở thư viện; phục hồi trạng thái ẩn của layout cũ, giữ chiều rộng tối thiểu 240px.
- Bấm bài/dạng đưa danh sách ra trước và lọc đúng phạm vi; các tab editor/draft vẫn giữ.
- Toolbar có nhãn các thao tác chính; bổ sung dòng phạm vi, hướng dẫn ngắn và trợ giúp danh sách trống.
- Danh sách hiển thị mức độ và bài/dạng thay cho phiên bản kỹ thuật.
- Thu sidebar chỉ làm cây CSDL gọn hơn; bỏ nút đóng cây để tránh mất điều hướng.

# 0.5.0 — Desktop workspace redesign

- Activity Bar 64px; splitter workspace và panel có trạng thái lưu riêng.
- CSDL tìm/lọc inline, multiselect, inspector phân loại/source/lỗi, danh sách và thẻ render theo yêu cầu.
- Editor tìm/thay thế inline, thụt dòng, toolbar chung, cảnh báo dirty và ánh xạ dòng lỗi khi xác định được.
- Nhập có bước tiến trình, số hợp lệ/lỗi/trùng và checkbox chọn bỏ câu; chỉ nhập IDs đã chọn.
- Ra đề ba vùng với thống kê NB/TH/VD/VDC, cảnh báo thiếu nguồn và preview source snapshot.
- Bài giảng outline/editor/bank/preview với toolbar lưu, biên dịch, xuất; giữ revision, autosave và pinned questions.
- Light/Dark qua theme module; sửa đổi theme không tạo revision bài giảng và không hủy preview.
- Xem UI_REDESIGN_REPORT.md cho bằng chứng, ảnh, kiểm thử và giới hạn; launcher console vẫn là hạn chế kỹ thuật đã ghi nhận.

# 0.4.0 ? ?n ??nh k? thu?t

- Th?ng k? SQL v?i cache c?u tr?c LaTeX theo SHA-256 v? parser version; cache kh?ng thay ngu?n/revision.
- Catalog JSON v? profile s?ch/phi?n b?n c?ng t?n t?i, gi? ID ch??ng/b?i ?? s? d?ng.
- ?? h?c sinh lo?i ??p ?n/l?i gi?i kh?i TeX v? kh?ng ch?p ?nh ch? d?ng trong l?i gi?i.
- Ch?n x?o c?u c? nhi?u macro ??p ?n kh?ng r? r?ng; gi? seed, matching v? ??p ?n ??ng.
- Th?ng k?/t?o ?? ch?y worker c? h?y; h?y preview tr??c thay control; review nh?p ph?n trang 200 c?u.
- C? audit, benchmark t?ng h?p 1k/10k/50k v? b?o c?o nghi?m thu. Gi?i h?n performance v? Windows console launcher ???c ghi r? trong b?o c?o.

Bản 0.3.5: gom nút ra đề vào toolbar đầu trang: lấy câu, thống kê, thêm phạm vi, thêm/xóa hàng, tạo và xuất đề. Icon có tooltip, xuất chỉ bật sau khi có đề. Xóa hàng cập nhật tổng ma trận.

Bản 0.3.4: đưa thao tác phân loại, mức độ, preview, lưu và đóng lên cùng toolbar Chọn file/Chọn thư mục/Hàng chờ. Dọn action khi đổi nội dung để tránh lặp hoặc gọi control cũ.

Bản 0.3.3: trang nhập dùng toolbar; thao tác thêm dạng, chọn mức độ, gán, nhập và đóng nằm trên toolbar icon có tooltip. Cột phải có Preview/Source, tự biên dịch nền khi chọn câu, hỗ trợ ảnh đi kèm, nhiều trang và báo lỗi không chặn phân loại. Preview dùng compiler.json và yêu cầu TeX engine đã cấu hình.

Bản 0.3.2: cố định bố cục trang nhập. Vùng nội dung có QWidget giãn riêng, giữ tiêu đề và thanh nút ở đầu trang cả khi chưa tải dữ liệu.

Bản 0.3.1 — Ra đề theo cây CSDL: chọn phạm vi môn/chương/bài/dạng, chọn loại câu, xem nguồn NB/TH/VD/VDC và số chưa gán mức độ. Nhập số cần lấy rồi thêm vào ma trận; lặp cho các phạm vi khác và tạo đề. Thống kê bỏ câu lưu trữ, source lỗi và câu đã chọn thủ công. Các phạm vi chồng nhau có thể dùng chung nguồn: bộ chọn kiểm tra đủ câu độc lập khi tạo đề. Có xóa hàng và tổng số câu theo mức độ.

Bản 0.3.0 — Phân loại khi nhập TeX: chọn câu (Ctrl/Shift để chọn nhiều), chọn bài hoặc dạng trên cây CSDL, chọn mức độ rồi Gán. Có gán toàn bộ danh sách, tìm cây, thêm dạng dưới bài, lọc câu chưa gán. Phân loại lưu trong hàng chờ và giữ khi sửa source; khi nhập chuyển sang metadata, liên kết cây và snapshot. Gán lại có xác nhận. Hàng chờ có nút mở lại cây phân loại. Chưa hỗ trợ tự đọc comment metadata hoặc AI phân loại; xem source ở cột phải.

Bản 0.2.8: sửa nhấp đúp mở/thu gọn cây CSDL. Click lọc bảng không tạo lại các item, giữ ổn định chuỗi sự kiện chuột của Qt.

Bản 0.2.7: thêm VẬT LÍ 11 (4 chương/26 bài), TOÁN 12 (5 chương/17 bài theo danh sách cung cấp), VẬT LÍ 12 (4 chương/25 bài). Cây CSDL có icon sách xanh cho môn, thư mục vàng cho chương, trang xanh lá cho bài. Schema 15 nâng cấp có backup; sửa đề khảo sát thành để khảo sát.

Bản 0.2.6: thêm TOÁN 10 (9 chương/27 bài), VẬT LÍ 10 (7 chương/34 bài), TOÁN 11 (9 chương/33 bài) theo danh sách người dùng. Schema 14 nâng cấp có backup và tự điền đúng môn/lớp/chương/bài.

Bản 0.2.5: thêm KHTN 9 (14 chương, 51 bài; Bài 1 ngoài chương) và TOÁN 9 (10 chương, 32 bài) theo danh sách người dùng. Sửa lỗi gõ dòng diện → dòng điện, aalcohol → alcohol, Mendel và ax². Schema 13 có backup trước nâng cấp; tự điền phân loại lớp 9.

Bản 0.2.4: thêm CSDL → KHTN 8 (46 bài, Bài 1 trực tiếp dưới môn và 8 chương) và TOÁN 8 (10 chương, 39 bài) theo danh sách người dùng. Tự điền môn/lớp 8/chương/bài; schema 12 nâng cấp có backup.

Bản 0.2.3: thêm CSDL → TOÁN 7 (Kết nối tri thức), 10 chương và 37 bài theo danh sách người dùng. Tự điền môn Toán, lớp 7 và chương/bài; schema 11 nâng cấp có backup.

Bản 0.2.2: thêm CSDL → KHTN 7, 10 chương và 41 bài (Bài 2–42) theo danh sách người dùng. Tự điền môn Khoa học tự nhiên, lớp 7, chương/bài; schema 10 nâng cấp có backup.

CSDL → TOÁN 6: 9 chương, 43 bài và 2 mục luyện tập chung theo danh sách người dùng. Chọn chương/bài để lọc ngân hàng; tạo câu tại mục đã chọn tự điền môn Toán, lớp 6 và chương/bài. Database nâng cấp lên schema 9 có backup trước migration.

# LaTeX Question Studio 0.2.0 — Soạn bài giảng

Thêm trang Bài giảng: cây lý thuyết/dạng toán/ví dụ/bài tập, biên tập TeX, tự lưu và lịch sử, chèn/trích lọc câu ngân hàng có pin revision và bản sửa cục bộ, ảnh/TikZ, preview nhiều trang, bộ xuất giáo viên/học sinh/phiếu bài tập gồm TeX/PDF/assets/checksum. Icon SVG thống nhất và nút chính/phụ rõ hơn.

40 tests pass, có biên dịch PDF thật, compile lại bộ TeX và backup/restore bài giảng. Schema 7 có backup trước migration; ứng dụng cũ không đọc schema mới. Giữ nguyên _internal cạnh EXE; TeX distribution là phụ thuộc ngoài. Launcher console x64; chưa nghiệm thu Windows sạch.

Đây là lát soạn bài mới, chưa hoàn tất tái thiết kế ngân hàng/duyệt/họ câu/ma trận nâng cao. Chưa nhập trọn bài giảng TeX cũ hoặc xuất Beamer. Gói bài giảng hiện dùng profile tích hợp; macro lạ trong source học sinh bị chặn cần review. Đọc 19_LESSON_IMPLEMENTATION_REPORT.md để biết phạm vi và giới hạn cụ thể.

Gói phát hành không chứa database người dùng, cấu hình hay token Telegram. Không commit/push.