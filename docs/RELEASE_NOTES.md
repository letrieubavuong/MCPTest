Bản 0.2.4: thêm CSDL → KHTN 8 (46 bài, Bài 1 trực tiếp dưới môn và 8 chương) và TOÁN 8 (10 chương, 39 bài) theo danh sách người dùng. Tự điền môn/lớp 8/chương/bài; schema 12 nâng cấp có backup.

Bản 0.2.3: thêm CSDL → TOÁN 7 (Kết nối tri thức), 10 chương và 37 bài theo danh sách người dùng. Tự điền môn Toán, lớp 7 và chương/bài; schema 11 nâng cấp có backup.

Bản 0.2.2: thêm CSDL → KHTN 7, 10 chương và 41 bài (Bài 2–42) theo danh sách người dùng. Tự điền môn Khoa học tự nhiên, lớp 7, chương/bài; schema 10 nâng cấp có backup.

CSDL → TOÁN 6: 9 chương, 43 bài và 2 mục luyện tập chung theo danh sách người dùng. Chọn chương/bài để lọc ngân hàng; tạo câu tại mục đã chọn tự điền môn Toán, lớp 6 và chương/bài. Database nâng cấp lên schema 9 có backup trước migration.

# LaTeX Question Studio 0.2.0 — Soạn bài giảng

Thêm trang Bài giảng: cây lý thuyết/dạng toán/ví dụ/bài tập, biên tập TeX, tự lưu và lịch sử, chèn/trích lọc câu ngân hàng có pin revision và bản sửa cục bộ, ảnh/TikZ, preview nhiều trang, bộ xuất giáo viên/học sinh/phiếu bài tập gồm TeX/PDF/assets/checksum. Icon SVG thống nhất và nút chính/phụ rõ hơn.

40 tests pass, có biên dịch PDF thật, compile lại bộ TeX và backup/restore bài giảng. Schema 7 có backup trước migration; ứng dụng cũ không đọc schema mới. Giữ nguyên _internal cạnh EXE; TeX distribution là phụ thuộc ngoài. Launcher console x64; chưa nghiệm thu Windows sạch.

Đây là lát soạn bài mới, chưa hoàn tất tái thiết kế ngân hàng/duyệt/họ câu/ma trận nâng cao. Chưa nhập trọn bài giảng TeX cũ hoặc xuất Beamer. Gói bài giảng hiện dùng profile tích hợp; macro lạ trong source học sinh bị chặn cần review. Đọc 19_LESSON_IMPLEMENTATION_REPORT.md để biết phạm vi và giới hạn cụ thể.

Gói phát hành không chứa database người dùng, cấu hình hay token Telegram. Không commit/push.