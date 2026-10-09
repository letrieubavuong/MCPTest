# Các phase và cổng nghiệm thu

Không tự chuyển phase khi chưa có kết quả nghiệm thu. Master plan là nguồn phạm vi. Người dùng yêu cầu tiếp tục sau báo cáo Phase 00: triển khai Phase 01, không tự mở rộng Phase 02.

| Phase | Deliverable | Nghiệm thu |
|---|---|---|
| 00 | Audit + 6 tài liệu thiết kế/migration | Source/schema dẫn chứng, unknown rõ |
| 01 | Package/config/logging/migrations/repository/cửa sổ Qt | Smoke mở app, CRUD, reopen, rollback, backup, pytest |
| 02 | Activity/Explorer/tab/dock/status/theme/layout | Chuyển màn, dirty tab, restart layout, keyboard |
| 03 | Scanner/assets/staging import | Source round-trip, lỗi vị trí, multi-file/hủy, không mất câu |
| 04 | Library/metadata/revisions/tags/backup | CRUD restart/revision restore/FK/DB+assets backup |
| 05 | Editor/compiler/render/cache | Corpus toán/TikZ/ảnh, timeout/hủy/cache invalidation, không block UI |
| 06 | FTS/filter/dedup | Search đúng, giữ số/True, gần trùng không tự xóa |
| 07 | Manual/matrix/shuffle/export | Quota/không lặp/seed/đáp án đúng/PDF corpus |
| 08 | Lazy load/queue/cache/benchmark | Dataset/máy rõ, đo import/search/preview/UI responsiveness |
| 09 | EXE/config/manual | Windows sạch có TeX, không Python riêng, restore/dependency license |

## Phase 00
Đã khảo sát chỉ đọc: 3.075 câu/828 phân loại, integrity ok, 0 orphan câu/3 orphan taxonomy; macro và source đối chiếu. 7 tài liệu + manifest 53 tệp. Không chạy ứng dụng cũ/TeX/migration. Telegram text API ok=true message_id=46; ảnh Phase 00 không nhận xác nhận và không retry.

## Phase 01
Xem 07_PHASE01_REPORT.md để biết file/kiến trúc/tests/kết quả/giới hạn. Skeleton dùng controlled sqlite3 migrations, không ORM ở bước đầu. Không migration legacy, không parser/compile/import/thiết kế shell Phase 02. No commit/push.

## Quyết định còn mở
Giữ taxonomy đủ cấp, mức cũ tách nhận thức; 3 orphan cần người duyệt; nguồn TeX/class/style/preamble/assets còn thiếu; SL/DanhsachID.TMC chưa rõ. Các quyết định này không ngăn skeleton nhưng phải giải quyết trước migration dữ liệu và nghiệm thu compile. Beamer/web/bài giảng ngoài MVP trừ khi người dùng yêu cầu.
