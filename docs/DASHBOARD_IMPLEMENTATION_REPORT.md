# Dashboard Implementation Report

Ngày: 10/10/2026.

Đã làm lại trang chủ Dashboard bằng PySide6, đặt tại nút Trang chủ trên thanh điều hướng mà không đổi route/index của CSDL, Nhập câu hỏi, Ra đề thi, Cài đặt và Bài giảng.

Dashboard đọc SQLite trực tiếp và hiển thị tổng câu hỏi, câu đang sử dụng, source lỗi, tài nguyên cần xử lý, phân bố mức độ theo từng môn, tình trạng tài nguyên, hoạt động cập nhật gần đây và quick actions. Bố cục mới có header phân cấp, KPI có icon/màu trạng thái, biểu đồ có trục/nhãn/legend, donut có tổng và tỷ lệ, trạng thái rỗng rõ ràng, activity row đã chuyển source thành nội dung đọc được và nút thao tác có icon. Biểu đồ vẽ bằng Qt, không thêm dependency; hỗ trợ theme sáng/tối, cuộn dọc và tự đổi KPI từ 4 cột xuống 2 cột ở cửa sổ hẹp.

Kiểm chứng: test Dashboard và UI liên quan **13/13 passed in 41.84s**; full suite **157 passed in 248.26s (0:04:08)**. Script chụp ảnh dùng dữ liệu mẫu riêng ở 1024x768, 1366x768, 1600x900, theme sáng/tối trong `artifacts/dashboard/`; `bundle-dashboard.png` được chụp từ EXE mới với bundle thật. Không đụng database cá nhân.

EXE mới smoke exit 0, subsystem Windows GUI 2, icon đủ 10 kích thước, SQLite integrity `ok`, schema 18, 641 node; ZIP cũng verify không kèm database người dùng/config bí mật. EXE SHA-256 `3e99d7dd8211c598e048c573dccbbf32448a84a0aadc0c33839ef74d8408a3b7`; hash ZIP chính thức nằm trong `release/LaTeXQuestionStudio-0.5.2-win64.zip.sha256`.
