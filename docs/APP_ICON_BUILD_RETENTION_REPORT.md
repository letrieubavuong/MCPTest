# Icon ứng dụng và dọn các bản build cũ

Ngày 10/10/2026. Không commit/push, không dùng dữ liệu cá nhân để kiểm thử.

## Icon

Biểu tượng gốc được thiết kế bằng SVG: sách mở màu trắng, dấu kiểm xanh ngọc trên nền xanh dương. Hình đơn giản và tương phản rõ ở kích thước nhỏ. Nguồn nằm tại `src/latex_question_studio/ui/assets/mcptest.svg`; script `scripts/generate_app_icon.py` xuất PNG 512 px và ICO với 10 cỡ: 16/20/24/32/40/48/64/96/128/256 px. Không cần font icon hoặc dịch vụ bên ngoài.

Ứng dụng đặt icon cho QApplication và cửa sổ chính; PyInstaller nhúng cùng ICO vào EXE và đóng gói assets. Kiểm tra bản đóng gói đối chiếu bytes của từng ảnh trong tài nguyên PE với ICO nguồn, đồng thời kiểm tra icon giao diện đã đi theo bundle. Bản GUI vẫn dùng `--windowed`, không mở CMD.

Icon điều hướng trong thanh bên cũng dùng cùng bộ nét bo tròn 24px: home, ngân hàng, nhập, ra đề, cài đặt, bài giảng và nút cây thư mục. Mục đang chọn dùng màu accent của theme; các mục còn lại dùng màu trung tính. Dashboard chỉ active home, tránh trạng thái chọn kép với CSDL.

## Chính sách giữ bản mới

`scripts/build.ps1` mặc định tạo icon, kiểm thử, build vào thư mục staging riêng và smoke EXE. Chỉ tạo/kiểm tra ZIP khi dùng `-PackageRelease` theo yêu cầu phát hành. Khi tất cả đạt, thay bản hiện tại rồi dọn bản cũ. Có journal để khôi phục các mục đã thay nếu bước sau thất bại; nếu khôi phục chưa xong thì giữ backup thay vì dọn staging. Nếu kiểm thử/build/smoke lỗi, bản đang dùng được giữ nguyên. Việc thay file yêu cầu ứng dụng đang chạy được đóng trước.

Sau build thành công giữ một thư mục phiên bản hiện tại trong `dist`, một ZIP và checksum hiện tại trong `release`, cùng workdir PyInstaller hiện tại để kiểm tra bytecode. Dọn các phiên bản cũ, backup EXE/PyInstaller, ZIP giải nén để smoke, bản copy fixture dùng cho bundle và thư mục kiểm thử tạm đã nhận diện trong `.runtime`. Không tạo thêm `bundle-before-*` sau mỗi lần build.

`scripts/clean-builds.ps1 -DryRun` xem trước danh sách; bỏ `-DryRun` để dọn theo cùng quy tắc. Xóa dùng đường dẫn literal và PowerShell trong phạm vi `dist`, `release`, `.runtime`; không xóa các thư mục gốc đó, không đi ra ngoài dự án. Từ chối junction/link trong bundle; link do pytest tạo chỉ được gỡ chính link trong thư mục kiểm thử, không duyệt/xóa đích. Giữ môi trường Python, mã nguồn, tài liệu, examples và dữ liệu cá nhân; bundle cũ chứa database sẽ được giữ và báo lỗi để tránh mất dữ liệu.

## Kiểm chứng

6 kiểm thử icon/build đã đạt: ICO đủ kích thước/alpha/icon cửa sổ, dọn đúng bản cũ và giữ bản hiện tại/dữ liệu, xử lý file read-only, từ chối đường dẫn ngoài phạm vi, bảo vệ junction/database đặt nhầm trong bundle, đổi tên thư mục nguyên vẹn và rollback khi giả lập lỗi giữa bước thay bản. Sau lỗi đổi tên thư mục chỉ đọc trên Windows, đã bỏ thuộc tính đệ quy và dùng `Move-Item -Force`; kiểm thử rollback vẫn giữ bản cũ.

Kiểm thử timer nhập 500 câu trước đây đếm số nhịp trong khoảng thời gian do tốc độ máy quyết định, có lúc chỉ được một nhịp dù nhập thành công. Đã đổi sang checkpoint có tín hiệu: xác nhận stage và commit chạy ngoài UI thread, yêu cầu UI phản hồi ít nhất 3 nhịp trong từng pha trước khi worker tiếp tục, vẫn kiểm tra đủ 500 câu. Không đổi nghiệp vụ nhập. Tập trung cuối: **8 passed in 5.98s**; lượt build hoàn tất **157 passed in 248.26s (0:04:08)**.

EXE và ZIP đã smoke thành công: exit 0, stderr rỗng, subsystem Windows GUI 2, schema 18/integrity `ok`, 641 node. Tài nguyên PE khớp cả 10 cỡ ICO nguồn; icon giao diện được đóng gói đúng, 17 module UI và 37 module bundle khớp source. Mở lại EXE bình thường và render từ cache trống đã tạo PDF công thức mới, không có cửa sổ console hiển thị.

Lượt build đã dọn **132 mục**, tổng **6.116.444.732 bytes** (5.696 GiB), gồm bản build cũ và thư mục tạm. Kiểm tra ngay sau dọn: chỉ còn `dist/0.5.2`, ZIP/checksum hiện tại và không còn thư mục backup/ZIP giải nén/pytest/staging cũ đã nhận diện. Chi tiết ở `artifacts/build-current/cleanup.json`; bản tóm tắt được đóng gói ở `verification/app-icon/retention.json`. Những thư mục tạm sinh ra khi kiểm tra bổ sung cũng được dọn sau cùng.

EXE SHA-256 hiện hành: `3e99d7dd8211c598e048c573dccbbf32448a84a0aadc0c33839ef74d8408a3b7`. Bản chạy: `dist/0.5.2/LaTeXQuestionStudio/LaTeXQuestionStudio.exe`. Gói phát hành: `release/LaTeXQuestionStudio-0.5.2-win64.zip`, manifest 157 tests, không kèm database người dùng hoặc config bí mật. Hash ZIP chính thức nằm trong file `.zip.sha256`; kết quả giải nén/khởi chạy ở `artifacts/build-current/zip-smoke.json`. Chỉ kiểm chứng trên máy Windows hiện tại, chưa chạy VM sạch.

Bằng chứng icon ở `artifacts/app-icon/icon-sizes.png`; kết quả build ở `artifacts/build-current/` (`tests.xml`, `windows-smoke.json`, `zip-smoke.json`, `cleanup.json`).
