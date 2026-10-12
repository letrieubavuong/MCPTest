# Sửa cửa sổ CMD khi mở EXE

Ngày 10/10/2026. Không commit/push; chỉ kiểm tra trên dữ liệu mẫu riêng.

## Nguyên nhân

`scripts/build.ps1` dùng `--console`, tạo EXE với subsystem Console (3). Windows vì vậy mở cửa sổ CMD khi chạy ứng dụng từ Explorer. `verify_ui_package.py` trước đây khởi chạy bằng `CREATE_NO_WINDOW`, che triệu chứng nên smoke vẫn đạt. pdfLaTeX đã có `CREATE_NO_WINDOW` trong cả truy vấn phiên bản và biên dịch.

## Thay đổi

- Dùng `--windowed` và bootloader `runw.exe` từ PyInstaller 6.22.3 đang cài. Không sửa/hide cửa sổ console lúc ứng dụng đã chạy.
- Smoke xác minh EXE là subsystem Windows GUI (2), rồi mở bình thường không dùng cờ che console. Đóng gói từ chối EXE console và ghi trạng thái GUI vào manifest.
- Công cụ sửa launcher thủ công cũng chọn bootloader GUI, tránh đưa console trở lại khi được sử dụng sau này. Build bình thường không gọi công cụ này.
- `scripts/verify_windowed_launch.py` mở EXE thật với bản copy bài giảng mẫu, không copy cache, theo dõi cửa sổ hiển thị và tiến trình con; yêu cầu ứng dụng hiển thị, pdfLaTeX thực sự chạy và công thức tạo được PDF mới.
- Tiếp tục ghi log vào `logs/studio.log`; giữ mã ứng dụng, schema và dữ liệu người dùng.

## Kiểm chứng

- Full suite: **150 passed in 181.98s (0:03:01)**. PyInstaller ban đầu không dọn được thư mục `localpycs` cũ (WinError 5); đã giữ lại workdir và tiếp tục cùng cấu hình build trong workdir mới, không đổi mã ứng dụng sau kiểm thử.
- EXE dùng bootloader `runw.exe`, subsystem GUI **2**; mở bình thường, không có `CREATE_NO_WINDOW` ở launcher kiểm thử. Smoke exit **0**, stderr rỗng, SQLite integrity **ok**, schema **18**, 641 node phân loại, 17 module UI khớp source.
- Quan sát khởi động/biên dịch **13,87 giây**: cửa sổ ứng dụng hiển thị, không xuất hiện cửa sổ console mới. Quan sát được tiến trình `pdflatex.exe`, tạo 1 PDF mới từ cache trống và render đúng phân thức. `conhost.exe` có thể tồn tại trong tiến trình nền của Windows nhưng không có cửa sổ console hiển thị.
- Kiểm tra bundle công thức: **37 module khớp source**, gồm bốn module nhập công thức/preview; EXE đã mở và render dữ liệu mẫu từ cache trống, exit 0.

Hash EXE của mốc chuyển Windows GUI trước khi thêm icon: `005e4a4ef2e1b44c8bde8e428ece1ff9d4c45c052beab93ecdd3d0fc32c1e2fd`. Bản chạy ở `dist/0.5.2/LaTeXQuestionStudio/LaTeXQuestionStudio.exe`; các cập nhật icon/dọn build mới và hash hiện hành xem `APP_ICON_BUILD_RETENTION_REPORT.md`, `artifacts/build-current/windows-smoke.json`. Gói ZIP ở `release/LaTeXQuestionStudio-0.5.2-win64.zip`, manifest giữ `windowed: true`, subsystem 2. Kết quả smoke mốc GUI ở `artifacts/windowed-build/zip-smoke.json`; hash ZIP hiện hành nằm trong file `.zip.sha256`.

Báo cáo tự động và ảnh nằm ở `artifacts/windowed-build/` (`windows-smoke.json`, `window-observation.json`, `windowed-formula.png`). Bản console trước được giữ trong `.runtime/bundle-before-windowed-20261010`. Chỉ kiểm chứng trên máy này, chưa chạy Windows VM sạch; không commit/push.
