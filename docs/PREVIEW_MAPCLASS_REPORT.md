# Preview theo MAPClass và ex_test — 0.5.2

Preview mặc định dùng nguyên bản `docs/Class/MAPClass.cls` và `docs/Packages/ex_test.sty`. Class nạp package qua `Packages/ex_test`; không thay thế các macro bằng mô phỏng. Tùy chọn mặc định: `company=BookA4,pagesize=DethiA4,mausac=01,tuychon=GV1`. Preview phục vụ giáo viên hiển thị đáp án và lời giải.

Các trang CSDL, nhập TeX, biên tập, ra đề và bài giảng dùng chung Compiler. Để trống File preamble riêng trong Cài đặt để dùng bộ này; preamble riêng được ưu tiên khi có cấu hình. Khi chạy từ mã nguồn, đọc trực tiếp file trong docs. EXE mang theo bản sao nguyên vẹn; build.ps1 đồng bộ lại từ docs trước mỗi build.

Cache PDF và cache ảnh CSDL tính cả nội dung class/package, tránh dùng kết quả cũ khi sửa mẫu. Gói bài giảng xuất ra kèm MAPClass.cls và Packages/ex_test.sty để biên dịch lại. Xuất TeX đề thi độc lập vẫn giữ mẫu article trước đây; PDF và preview dùng profile đã cấu hình.

Cần pdfLaTeX và các dependency mà class khai báo (môi trường kiểm tra: TeX Live 2026). Khi thiếu package, giao diện hiển thị log lỗi; không tự đổi sang mẫu giả. Không sửa parser, cách phân loại hoặc đáp án câu hỏi.

Ảnh kiểm tra dùng câu hỏi tổng hợp, không có dữ liệu ngân hàng thật:

![Preview MAPClass](../artifacts/mapclass-preview/library-light-1366x768.png)


Kết quả xác minh: **95 kiểm thử đạt** (219,92 giây). PDF thật kiểm tra các kiểu câu hỏi, TikZ/ảnh và cache; lời giải giáo viên được giữ, bản học sinh không lộ lời giải. Gói bài giảng TeX biên dịch lại thành công. EXE 0.5.2 smoke test exit 0, CSDL integrity ok/schema 17/641 node; bytecode Compiler và xuất bài giảng khớp mã cuối cùng. Tài nguyên trong bundle khớp byte-for-byte file docs và biên dịch PDF thành công. Ảnh tổng hợp Telegram: API ok=true, message_id=106. Chưa kiểm tra trên Windows VM sạch.
