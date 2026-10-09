# Báo cáo Phase 01 — 09/10/2026

## Kết quả
Skeleton Windows Python/PySide6 chạy được, cơ sở dữ liệu tạo/mở lại an toàn. 14 pytest đạt; smoke CLI thật exit=0 và lưu artifacts/Phase 01 UI.png, đã xem ảnh và xác nhận chữ tiếng Việt hiển thị đúng. Không tự triển khai Phase 02; không commit/push.

## Thay đổi
- pyproject.toml/.gitignore/README.md và scripts/run.ps1: package/cài đặt/chạy trong đường dẫn có khoảng trắng.
- src/latex_question_studio/app: bootstrap, config JSON versioned + atomic replace, logging xoay file.
- domain/question.py: DTO bất biến và kiểm tra invariants; difficulty legacy tách cognitive level.
- application/services.py: dependency injection đơn giản.
- persistence/database.py: foreign keys, transaction BEGIN IMMEDIATE, user_version migrations, backup SQLite API trước nâng cấp, từ chối schema lạ/newer.
- persistence/questions.py: CRUD tham số hóa, revision snapshots, chống stale update bằng revision.
- ui/main_window.py: cửa sổ tiếng Việt, trạng thái/count DB và nút refresh; không seed câu tự động.
- tests/test_persistence.py, tests/test_app.py: rollback migration/failed revision, reopen, backup, upgrade, FK, validation, config/logging và Qt smoke.
- docs/00–06 sửa lại UTF-8 vì PowerShell lần trước làm mất dấu; giữ kết luận khảo sát, ghi rõ subset Phase 01.

## Kiến trúc và quyết định
Dùng sqlite3 chuẩn và migrations có kiểm soát (master plan cho phép), chưa cần SQLAlchemy/Alembic. Python 3.14.6; PySide6 6.11.1; pytest 9.1.1; pytest-qt 4.5.0. Venv phiên này dùng system-site-packages để tái dùng Qt có sẵn; README có hướng dẫn venv độc lập để tái lập.

PySide6 metadata license LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only; packaging/release cần đáp ứng license đã chọn ở Phase 09. Chưa có QScintilla/PyMuPDF/TeX dependency vì chưa tới phase tương ứng.

## Bằng chứng kiểm thử
python -m pytest -q: 14 passed (0.67s ở lần đầu).
scripts/run.ps1 -DataDir .runtime/phase01-smoke -SmokeTest -Screenshot artifacts/Phase 01 UI.png: exit 0.
Test nâng schema thật v1→v2 kiểm tra dữ liệu giữ nguyên và backup user_version=1. Test migration SQL lỗi kiểm tra schema/transaction rollback và retry thành công. Test revision INSERT lỗi đảm bảo UPDATE câu rollback. Legacy DB lạ/newer bị từ chối không đổi bytes.

## Giới hạn
Chưa migrate dữ liệu cũ, parser, FTS, nhập, editor, preview, đề thi hoặc EXE. UI shell là Phase 02. Repository delete hiện xóa kèm revision; archive/restore và chính sách xóa giao diện bổ sung ở Phase 04. Backup Phase 01 chỉ DB vì chưa có assets; backup toàn ứng dụng cần hoàn thiện khi assets được đưa vào. MAPClass/ex_test/preamble và mapping nhận thức vẫn chờ, không chặn skeleton.

## Telegram
Mốc started Phase 01 bị timeout, delivery unconfirmed; không retry. Ảnh cửa sổ Phase 01 đã gửi thành công bằng sendPhoto: API ok=true, message_id=47. Caption kèm dự án/phase/kết quả 14 tests và smoke. Không có dữ liệu cá nhân trong ảnh.

Kiểm tra cuối: 14 passed (0.62s), smoke mở lại exit=0. Manifest tham khảo 53 tệp được đối chiếu SHA-256; kết quả ghi bên dưới.
SHA-256 cuối Phase 01: 53 tệp, 0 thay đổi so với manifest Phase 00.
