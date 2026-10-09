# Sửa hướng sử dụng thư viện — 0.5.1

Phản hồi: mất cây CSDL, khó hiểu và không biết dùng. Nguyên nhân tìm thấy: panel cây có thể bị đóng rồi workspace lưu trạng thái ẩn; chọn bài trong lúc mở editor lọc danh sách nằm phía sau mà chưa chuyển tới danh sách. Toolbar icon cùng cấp thiếu nhãn trực tiếp.

Sửa: cây CSDL luôn hiện khi mở thư viện với minimum width 240px; tự khôi phục dù workspace cũ lưu hidden, bỏ nút đóng panel cây. Thu sidebar ở CSDL chỉ đổi chiều rộng. Click bài/dạng đưa danh sách ra trước và giữ nguyên draft editor. Hiện đường dẫn phạm vi, loại câu, mức độ, bài/dạng; toolbar ghi tên thao tác thường dùng, các thao tác phụ vào menu. Danh sách rỗng có hướng dẫn nhập hoặc xem tất cả câu. Không thay parser, dữ liệu hay dịch vụ nghiệp vụ; không commit/push.

Cách dùng: **Chọn bài/dạng ở cây trái → chọn câu ở danh sách giữa → xem preview phải**, dùng Sửa câu / Phân loại / Nhập TeX / Lấy vào đề theo tên nút.

Ảnh fixture tổng hợp, không ngân hàng thật: [Sáng](../artifacts/library-fix/library-light-1366x768.png), [Tối](../artifacts/library-fix/library-dark-1366x768.png), [Danh sách trống](../artifacts/library-fix/library-empty-light-1366x768.png). Khung Qt 1366×768, cây hiện và rộng 299px, đủ 14 root profiles.

Kiểm thử ban đầu: 14 tests navigation/shell/UI đạt, gồm hồi quy restore hidden tree, chọn bài khi mở editor, giữ draft, nhãn toolbar và trợ giúp rỗng. Toàn suite: **93 passed / 183,35 giây**. EXE Windows x64 0.5.1 smoke exit 0, SQLite integrity ok, schema 17, 641 nodes; bytecode 13 module UI khớp source. ZIP được smoke sau đóng gói. Không kiểm thử Windows VM sạch.

File sửa: main_window.py, pages/library.py, test_ui_redesign.py, capture_library_fix.py, build.ps1, verify_ui_package.py, package_release.py, pyproject.toml và docs hướng dẫn/báo cáo.

Ảnh sửa thư viện đã được Telegram xác nhận sendPhoto `API ok=true`, message_id **103**.

Bản chạy: `dist/0.5.1/LaTeXQuestionStudio/LaTeXQuestionStudio.exe`. ZIP: `release/LaTeXQuestionStudio-0.5.1-win64.zip`.
