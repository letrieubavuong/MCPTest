# Triển khai bài giảng — phiên bản 0.2.0

Ngày 2026-10-09. Đây là lát triển khai soạn bài mới xuyên suốt từ docs/18, chưa phải hoàn tất toàn bộ phương án tái thiết kế docs/17.

## Đã triển khai

- Drawer có Bài giảng, icon SVG đồng bộ; nút chính/phụ phân biệt. Trang nhúng giữ cấu trúc hai cột tổng thể.
- Tạo bài từ mẫu, mở/đổi tên, nhân bản. Cây nội dung có lý thuyết, dạng toán/phương pháp, ví dụ, bài tập và nhóm nội dung; thêm cùng cấp/con, di chuyển lên/xuống giữa các mục cùng cha, xóa nhánh có xác nhận.
- Biên tập TeX, tên mục, ghi chú riêng giáo viên; tự lưu sau 1,5 giây dừng nhập, revision, khôi phục bản cũ thành revision mới. Lưu câu ngân hàng và lưu bài được tách để không mất dữ liệu khi đóng từ trang khác.
- Panel ngân hàng trong trang: tìm nội dung/metadata, lọc môn/khối/chủ đề/loại/nhận thức, tick câu, chọn vai trò ví dụ/bài tập. Trích lọc trên tập phù hợp với số lượng/seed, báo thiếu và preview danh sách trước chèn. Kết quả cụ thể được lưu, không tự rút lại.
- Pin câu/source/revision/assets; sửa trong bài không ghi ngược ngân hàng. Chặn lặp ID mặc định, có cho phép lặp có chủ đích.
- Chèn ảnh PNG/JPG/PDF ở bất kỳ khối, lưu hash trong kho; kiểm tra ảnh thiếu/đổi bytes. TikZ đi qua compiler sẵn có.
- Chính sách theo khối: Hiện đầy đủ, Chỉ đề bài, Chỉ giáo viên. Bản học sinh có thể giữ lời giải ví dụ công khai; ghi chú riêng bị loại. Chính sách Chỉ đề bài loại True/loigiai/hdan/shortans và comment khỏi body source; macro ngoài từ vựng tích hợp bị chặn thay vì tự nhận đã ẩn an toàn.
- Preview toàn bài hoặc phiếu bài tập, giáo viên/học sinh, phân trang; worker và hủy preview, chống kết quả cũ. Ctrl+S/F5/Ctrl+F/Ctrl+H theo ngữ cảnh bài.
- Xuất nền bộ main.tex + PDF + assets + manifest checksum vào thư mục mới, không ghi đè bản cũ. Bản sao gói xuất nằm trong lesson_exports để backup. DB giữ snapshot bài/profile và checksum; bản cũ không tự thay khi chỉnh câu hiện tại.
- Backup/restore mở rộng cho bài/revisions và gói xuất, giữ checksum/path validation. Migration 6→7 backup trước khi thêm bảng lessons/lesson_revisions/lesson_exports.

## Tệp chính

application/lessons.py: nghiệp vụ và export. ui/lesson_page.py: trang soạn và picker. ui/icons.py: SVG gốc. persistence/database.py: schema 7. application/library.py: backup/restore gói xuất. ui/main_window.py: tích hợp và lưu theo ngữ cảnh. tests/test_lessons.py: kiểm thử xuyên suốt.

## Kiểm thử thực tế

40 tests pass sau thay đổi cuối. Chín kiểm thử mới gồm pin/local edit/restore/concurrent save, seed/thiếu nguồn/lặp ID, chính sách dữ liệu giáo viên/học sinh, cây lỗi/ảnh đổi, PDF thật + compile lại gói TeX sau di chuyển + backup/restore, UI embedded/autosave/reopen, đóng từ bài giảng khi câu ngân hàng còn dirty, nâng cấp DB schema 6 giữ câu và backup.

Bài mẫu trong .runtime/lesson-demo dùng 4 câu toán minh họa từ examples/demo.tex; 8 khối, hai dạng toán, một ví dụ và ba bài tập. Xuất hai bản giáo viên/học sinh, preview hai trang. artifacts/lesson_demo_results.json ghi đầu ra; ảnh artifacts/Lesson authoring preview.png và Lesson bank picker.png đã được xem trước, không chứa dữ liệu cá nhân/token.

## Phần chưa triển khai của phương án

- Chưa nhập trọn bài giảng TeX cũ (lý thuyết ngoài ex), chưa xuất Beamer; không quảng bá parser câu hiện tại là parser bài giảng.
- Chưa có editor trực quan, drag/drop đổi cha, cross-reference tự động, thư viện khối tái sử dụng hay quản lý chương/bài đầy đủ. Hiện biên tập nội dung bằng TeX và reorder cùng cấp bằng nút.
- Chưa có luồng duyệt câu/duyệt bài hoàn chỉnh; picker hiện lấy câu có cấu trúc hợp lệ từ ngân hàng đang hoạt động. Người dùng phải review chất lượng trước dùng. Tránh trùng mới theo ID; họ câu, diff hai câu và quyết định merge/undo mới chưa triển khai.
- Gói source bài giảng dùng profile article tích hợp. Profile riêng có thể preview nếu được cấu hình, nhưng export gói bị chặn đến khi dependency/profile được chứng nhận. Từ vựng macro source học sinh được kiểm tra bảo thủ; macro lạ có thể cần mở rộng profile có kiểm thử.
- Chưa tự nhận biết đáp án có trong hình hay nội dung diễn giải tự do; giáo viên phải review bản học sinh. Lệnh Hiện đầy đủ là lựa chọn công khai nội dung khối đó.
- Chưa tự cập nhật revision ngân hàng, chưa có UI lịch sử xuất riêng và cờ duyệt/phát hành chính thức. Đã giữ snapshot các lần xuất; chỉ gọi là bộ xuất, không thay cho toàn bộ quy trình phát hành đã đề xuất.
- Search/picker chưa benchmark trên 50.000 câu. Chưa nghiệm thu Windows VM sạch.

Không commit/push, không sửa dự án C# tham chiếu, không đọc/in token Telegram. Database lên schema 7 không mở bằng app cũ schema 6; có backup trước migration.

## Bước tiếp theo trong lộ trình

Hoàn thiện danh mục và duyệt chất lượng ngân hàng; màn hình so trùng/họ câu; giao diện cập nhật revision/cảnh báo nguồn; sau đó nhập bài giảng TeX cũ và mẫu xuất chuyên biệt. Các bước này tiếp tục dùng đặc tả docs/17 và docs/18, không được đánh dấu hoàn tất bởi bản 0.2.0.
## Đóng gói và báo cáo

EXE x64 bản 0.2.0 đã chạy local với PATH chỉ Windows/TeX, exit 0, tạo ảnh trang Bài giảng và giữ nguyên hash binary. Telegram đã xác nhận sendPhoto ok=true cho hai ảnh soạn bài và chọn ngân hàng; message_id sẽ ghi cùng biên bản giao ZIP.

Bản cuối bổ sung kiểm thử hủy preview/đổi bài không nhận kết quả cũ: tổng 40 tests pass. scripts/python-runtime.ps1 xác minh marker runtime trước khi run/test/build, hỗ trợ -PythonPath; đã thử chọn đúng fallback khi Python .venv không thực thi. Ảnh Telegram API ok=true: message_id=67 và 68. Báo cáo ban đầu message_id=69 dùng kết quả 39 tests tại thời điểm gửi; bản cuối có 40 tests.
