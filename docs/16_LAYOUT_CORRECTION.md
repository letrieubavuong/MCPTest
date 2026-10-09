# Sửa layout theo MCPTest C# — 0.1.1

## Căn cứ

MainWindow.xaml của dự án MCPTest2020 có Grid hai cột LeftPanel và vùng control nội dung. MainWindow.xaml.cs, Btn_NhapCH_Selected gọi HideTab("tbNhapCH", tbNhapCH); Btn_XemCSDL_Selected gọi HideTab("tbXemCH", tbXemCH). Chức năng là control được chọn bên trong cửa sổ chính. Bản trước dùng dock toàn cửa sổ và dialog nhập/ra đề không đúng ý người dùng.

## Thay đổi

- main_window.py: drawer ở cột trái và QStackedWidget ở cột phải; bốn trang giữ instance khi chuyển. Library docks nằm trong control CSDL, không float. Import progress/review/commit và settings nhúng. Tạo đề trả kết quả tại trang trước khi người dùng chọn xuất.
- import_dialog.py, pending_dialog.py, exam_dialog.py: chuyển thành QWidget có signal, bỏ exec cho các luồng chức năng chính. Không thay database/schema hoặc service nghiệp vụ.
- Workspace v2 lưu trang/drawer và bố cục nội bộ CSDL; đọc v1 giữ geometry/tabs và bỏ layout dock shell cũ.
- tests/test_navigation.py: click menu, kiểm tra parent/window, edit chưa lưu, trạng thái form, khôi phục workspace, background result không giành trang, nhập/commit và tạo đề không có dialog chức năng.
- README, USER_GUIDE, RELEASE_NOTES, UI_UX_SPEC được cập nhật.

## Kiểm chứng

31 tests pass. Đã xem ba ảnh giao diện trong artifacts/Layout - *.png; chỉ sử dụng câu toán minh họa. Runtime Python cũ trong máy thoát ngay không thực thi mã, nên kiểm thử/build dùng Python 3.14.0 embedded tải từ python.org trong workspace, cùng dependency đã cài. Không thay cấu hình Telegram, không commit/push, không sửa dự án C# tham chiếu. Kiểm thử EXE và kết quả gửi bot được ghi bổ sung sau khi đóng gói.

## Nghiệm thu gói 0.1.1

ZIP được giải nén sang `.runtime/layout-release-acceptance`, EXE chạy exit 0 với PATH không có Python và tạo ảnh `artifacts/Layout - EXE.png` thể hiện drawer trái/trang Ra đề phải. Hash EXE giữ nguyên trước/sau chạy. Manifest tại `artifacts/layout_release_acceptance.json`. Chưa có Windows VM sạch.

Telegram đã xác nhận sendPhoto ok=true cho ảnh Nhập câu hỏi (message_id=62) và Ra đề thi (message_id=63). Kết quả sendMessage được ghi riêng nếu được API xác nhận.
Telegram sendMessage: API ok=true, message_id=64.
