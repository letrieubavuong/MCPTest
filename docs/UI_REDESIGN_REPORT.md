# UI redesign 0.5.0 — Báo cáo nghiệm thu

## Phạm vi

Thực hiện theo UI-01 → UI-08 trong yêu cầu P0. Giữ Python/PySide6/SQLite, không sửa parser, đáp án, seed, permutation, snapshot hoặc cơ chế nghiệp vụ. Giữ nguyên các thay đổi ổn định kỹ thuật có trước trong working tree. Không commit/push.

## Kết quả theo màn hình

| Phase | Thay đổi thực tế |
|---|---|
| UI-01 | Audit code và tests; ghi vấn đề cụ thể, tác động và thứ tự ưu tiên tại UI_UX_AUDIT.md |
| UI-02 | ApplicationShell/Activity Bar 64px, reusable Panel/Workspace/CommandToolbar, Light/Dark module riêng, splitter state/visibility và geometry lưu workspace.json v3; đọc layout cũ tương thích |
| UI-03 | CSDL explorer có count, tìm nhanh debounce và lọc loại/mức/trạng thái, multiselect/copy/archive, inspector phân loại/source/log, compact list và card với render theo lựa chọn; RAM cache giới hạn 40 và compiler disk cache; generation/cancel chống kết quả cũ |
| UI-04 | Giữ highlight/gutter/completion/tab/dirty warning; thêm thụt dòng và tìm/thay thế inline; toolbar dùng được ở tab editor, Ctrl+S/Ctrl+F/Ctrl+H/F5; invalidation preview khi gõ; ánh xạ lỗi source từ wrapper khi xác định được |
| UI-05 | Luồng có nhãn bước, tổng hợp hợp lệ/lỗi/trùng/chọn nhập, checkbox bỏ câu và trạng thái xuyên trang; commit IDs đã tick qua API cũ, câu bỏ lại giữ pending; cây/bulk classification/source lỗi từng câu/preview/cancel |
| UI-06 | Explorer trái, thống kê và ma trận giữa, câu thủ công/snapshot + preview phải; NB/TH/VD/VDC khả dụng/cần lấy/thiếu nguồn; form xáo/seed gọn, primary tạo đề, secondary ma trận và export; snapshot preview dùng source ghim |
| UI-07 | Outline/editor/bank tabs/preview cùng QSplitter, toolbar lưu/biên dịch/xuất và menu secondary; chèn bằng nút chọn/tick, giữ autosave/revision/snapshot; outline thao tác icon tooltip |
| UI-08 | Đã kiểm thử hồi quy, chụp ảnh hai theme ở ba kích thước, kiểm tra phím tắt và batch 2.000 câu; EXE và ZIP smoke được ghi trong verification |

Bottom panel CSDL có Nhật ký/Tác vụ/Lỗi LaTeX. Các trang nhập/ra đề/bài giảng có trạng thái và lỗi preview trong workspace tương ứng. Bộ theme không đặt stylesheet lên MainWindow.

## Kiểm tra trực quan

Ảnh gốc tại `artifacts/ui-redesign/`: CSDL, editor, nhập, ra đề, bài giảng, cài đặt, cả Dark/Light và 1366×768, 1600×900, 1920×1080; thêm thẻ preview và contact sheets. Dữ liệu fixture tổng hợp, không ngân hàng thật, token hoặc thông tin cá nhân. Capture Qt window.grab với frame ẩn để canvas đủ 1920×1080 trên màn hình Windows hiện tại; đây là kiểm chứng widget native Qt, không phải ảnh mockup.

Trước: [Nhập](../artifacts/stabilization-import.png), [Ra đề](../artifacts/stabilization-exam.png).

Sau: [CSDL](../artifacts/ui-redesign/csdl-dark-1366x768.png), [Editor](../artifacts/ui-redesign/editor-dark-1366x768.png), [Nhập](../artifacts/ui-redesign/import-light-1366x768.png), [Ra đề](../artifacts/ui-redesign/exam-dark-1366x768.png), [Bài giảng](../artifacts/ui-redesign/lessons-light-1366x768.png), [Thẻ render](../artifacts/ui-redesign/cards-light-1366x768.png).

Các lỗi sửa từ kiểm tra ảnh/test: toolbar editor bị mất; trạng thái preview không khôi phục khi về library; đổi theme làm lesson dirty/hủy preview; lỗi callback task sau QObject bị hủy; selection card bị mất sau nhận render; ảnh giữ minimum size gây tràn khi kéo splitter; cache thẻ cũ sau đổi source/revision. Các test cũ kỳ vọng Preview/Source được đổi thành nhãn tiếng Việt theo yêu cầu.

## File thay đổi của riêng redesign

- `ui/main_window.py`: orchestration shell/panels/handlers và persisted state.
- `ui/shell/application.py`: shell dùng chung.
- `ui/components/workspace.py`: Panel, Workspace, CommandToolbar.
- `ui/themes/design.py`: theme tokens/palette/style tập trung.
- `ui/pages/library.py`: CSDL/inspector/cards/filter adapters.
- `ui/panels/question_preview.py`: lazy preview dùng lại cho ra đề.
- `ui/editor.py`, `ui/import_dialog.py`, `ui/exam_dialog.py`, `ui/lesson_page.py`.
- `tests/test_ui_redesign.py`, `tests/test_import_classification.py`.
- `scripts/capture_ui_redesign.py`, `scripts/verify_ui_acceptance.py`, `scripts/verify_ui_package.py`, `scripts/build.ps1`, `scripts/package_release.py`, `pyproject.toml`.
- UI audit/spec/report, release notes và user guide.

## Kiểm thử và bản chạy

- Toàn bộ suite: **91 passed / 205,21 giây**, không skip. Có 9 test UI redesign mới.
- Sau sửa nhỏ cuối về primary action khi chuyển toolbar: **11 test toolbar/UI passed / 35,98 giây**. Không đổi parser hoặc dịch vụ nghiệp vụ ở bước này.
- Nghiệm thu QTest gõ source thật và Ctrl+S/Ctrl+F/Ctrl+H: đều đạt; source được lưu, tìm/thay inline mở đúng, editor giữ trạng thái khi chuyển trang.
- Batch tổng hợp **2.000 câu**: stage 0,271s; dựng review 0,299s; chỉ **200 dòng** được tạo mỗi trang; bỏ chọn giữ nguyên khi chuyển trang. Đây là một lần đo fixture, không benchmark ngân hàng thật.
- 36 ảnh trang/theme/kích thước + 1 ảnh thẻ; measurements.json không có kích thước lệch. Thêm 2 contact sheets để đối chiếu trực quan.
- Windows x64 EXE smoke: exit 0, SQLite integrity `ok`, schema 17, 641 taxonomy nodes. Kiểm tra bytecode 13 module UI khớp source cuối; kết quả cập nhật cho binary hoàn thiện trong windows-smoke.json.
- Bản chạy: `dist/0.5.0/LaTeXQuestionStudio/LaTeXQuestionStudio.exe`; ZIP: `release/LaTeXQuestionStudio-0.5.0-win64.zip`. File ZIP được tạo sau khi smoke và tests đạt, có docs/UI evidence, không kèm DB/cấu hình cá nhân.

Bằng chứng: `artifacts/ui-redesign/measurements.json`, `acceptance.json`, `windows-smoke.json`, `zip-smoke.json`. Telegram ghi kết quả API thực tế trong phần bàn giao, không ghi token hoặc URL chứa token.

## Giới hạn còn lại

- Card chưa được chọn chỉ hiện tóm tắt; không tự compile tất cả thẻ khi mở trang. Render on demand là chủ đích để ngân hàng lớn không bị nghẽn.
- Lỗi preamble/tệp phụ không ánh xạ được sẽ giữ log, không nhảy sang dòng source sai.
- Chèn ngân hàng vào bài giảng qua nút hiện có; chưa thêm drag/drop. Không thay đổi revision hoặc snapshot để làm drag/drop.
- MainWindow vẫn giữ điều phối legacy và một số dialog lịch sử/backup/xuất. Refactor module theo từng phần, chưa di chuyển toàn bộ handler sang pages.
- Kiểm thử trực quan bằng fixture Qt và kiểm thử tự động; chưa có vòng dùng thử giáo viên với ngân hàng thực tế, chưa nghiệm thu trên Windows VM sạch.
- Bootloader Windows console là hạn chế kỹ thuật có trước; bản 0.5.0 vẫn có thể hiện CMD. Phase UI này không tuyên bố đã sửa vấn đề đó.

## Báo cáo Telegram

Thông báo tiến độ UI-01→UI-07 được Telegram xác nhận `API ok=true`, message_id 100. Hai lần gửi ảnh Nhập và Editor ở UI-08 timeout, chưa xác nhận đã giao; không coi là gửi thành công. Lỗi ảnh không làm dừng phase. Kết quả lần gửi bổ sung và thông báo bàn giao được ghi tại artifacts/ui-redesign/telegram.json nếu API xác nhận.

Báo cáo bàn giao bằng text đã được Telegram xác nhận `API ok=true`, message_id **102**. Ảnh gửi qua API vẫn chưa xác nhận được; ảnh gốc nằm trong release.
