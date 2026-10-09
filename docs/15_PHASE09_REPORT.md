# Phase 09 — Đóng gói và bàn giao 0.1.0

Đã tạo sản phẩm Windows x64 dùng được trên máy hiện tại và gói ZIP để bàn giao. Tiêu chí Windows sạch riêng trong kế hoạch CHƯA nghiệm thu: phiên làm việc này không có VM/máy Windows sạch để kiểm chứng. Không đồng nhất kiểm tra PATH không có Python với kiểm tra máy sạch.

## Đầu ra

- `release/LaTeXQuestionStudio-0.1.0-win64.zip` và `.zip.sha256`.
- `dist/LaTeXQuestionStudio/LaTeXQuestionStudio.exe`, giữ nguyên thư mục `_internal` bên cạnh.
- USER_GUIDE.md, TROUBLESHOOTING.md, RELEASE_NOTES.md, ví dụ và giấy phép phụ thuộc có trong ZIP.
- scripts/build.ps1, finalize_windows_build.py, package_release.py.
- artifacts/release_acceptance.json và ảnh Extracted release preview.png.

## Kiến trúc và xử lý đóng gói

PyInstaller onedir, Python/Qt/PyMuPDF đi kèm; TeX distribution là phụ thuộc ngoài. Bootloader console x64 lấy từ wheel PyInstaller 6.21.0 gốc vì bootloader cài trên máy từng có header x86 không đúng thư mục x64. Có quan sát EXE thay đổi bytes trong các lần thử trước; chưa xác định nguyên nhân. Không phát hành các binary lỗi đó. Launcher console gốc chạy ổn định và hash giữ nguyên sau chạy. Bản windowed không khởi động được với mã 0xC0000138 trên máy này. Bản DLL ucrtbase thu thập cũng gây lỗi khởi tạo; gói cuối dùng UCRT hệ thống Windows. Cửa sổ console có thể xuất hiện cùng giao diện.

## Kiểm tra thực tế

- Bộ ứng dụng: 29 tests pass, gồm Qt, SQLite migration/rollback, parser/source, import/repair/assets, backup/restore, FTS/dedup, seed/True và biên dịch PDF thật.
- EXE x64 chạy bằng PATH chỉ có Windows và TeX, không có Python: exit 0, log khởi động và ảnh giao diện được tạo.
- Giải nén ZIP vào thư mục khác rồi chạy EXE một lần nữa: exit 0, ảnh giao diện có 4 câu minh họa/editor/preview PDF; SHA256 EXE trước và sau chạy giống nhau.
- ZIP không có database người dùng hoặc cấu hình Telegram. 53 tệp tham chiếu legacy giữ nguyên SHA256.
- Telegram sendPhoto: API ok=true, message_id=60. Telegram sendMessage: API ok=true, message_id=61. Ảnh đã xem trước, chỉ chứa dữ liệu toán minh họa.
- Không commit/push; workspace hiện không phải Git repository.

## Giới hạn bàn giao

Chưa kiểm thử trên Windows sạch, chưa chứng nhận MAPClass/ex_test do thiếu dependency gốc. Parser không thay thế TeX expansion đầy đủ. Benchmark corpus thực tế 3.075 câu, không suy rộng lên hàng trăm nghìn câu. Một câu lỗi được quarantine thay vì mất âm thầm. Cần giữ `_internal`, cài TeX và cấu hình đường dẫn nếu máy đích không tự phát hiện.

SHA256 ZIP: 8c8dabc545c6f442f544ca35a381b22a82a09cc8d7f89fbd5054a2ebf9a10e97
