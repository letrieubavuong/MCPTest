# Asset and UI Audit

Ngày audit: 09/10/2026. HEAD: `c1b8ee070c5f6c66cbed8c7935ae84789d909b0b`. Working tree đã có thay đổi chưa commit từ phase trước; không ghi đè hoặc hoàn tác các thay đổi đó. Không mở database người dùng thật.

## Baseline

- Python 3.14.6, PySide6 6.11.2, PyMuPDF 1.28.0, pdfLaTeX TeX Live 2026.
- `107 passed in 157.88s` với `python -m pytest -q --basetemp .runtime/pytest-phase0`.
- Schema SQLite hiện tại: 18. Các bảng tài nguyên hiện có: `assets`, `question_assets`; dữ liệu nguồn được lưu tại `sources` và asset tại `assets` trong `data_dir`.

## Luồng hiện tại

`ImportService.stage()` đọc bytes file nguồn, lưu archive theo SHA-256, parse câu, tìm `includegraphics` tương đối với `path.parent`, copy bytes vào `data_dir/assets/<sha><suffix>`, rồi lưu asset trong `parsed_json`. `commit()` ghi `questions`, revisions, metadata, taxonomy và `question_assets` trong một transaction.

Preview `Compiler` thay tên `includegraphics` bằng tên hash trong thư mục tạm; `ExamService` đọc asset từ `question_assets`; `LessonService` dùng mapping riêng trong document; `TexExamService` có resolver riêng cho file TeX. Những resolver này không chia sẻ `graphicspath`, `input/include`, ambiguity hoặc trạng thái thiếu tài nguyên.

## Findings

| Mức | File/hàm | Bằng chứng | Hướng xử lý |
|---|---|---|---|
| P0 | `application/importing.py:stage`, `repair` | Tìm ảnh chỉ theo `path.parent/reference`, không đọc `graphicspath`; nhiều ứng viên lấy ứng viên đầu tiên; không có trạng thái ambiguity hoặc dependency context. | Phase 1 resolver chung, báo ambiguity/blocked/unsupported/needs review; không tự chọn nhiều ứng viên. |
| P0 | `application/importing.py:stage` | Asset được ghi vật lý trước transaction; hủy giữa batch có thể để lại asset rác. Ghi asset trực tiếp, chưa atomic verify đầy đủ. | Phase 2 staging tạm, checksum trước commit, atomic replace và cleanup khi hủy. |
| P0 | `preview/compiler.py`, `application/lessons.py` | Preview/lesson/export phụ thuộc mapping riêng; sau khi source ngoài bị di chuyển, câu đã nhập có thể không có đủ mapping cho asset chưa được nhận diện. | Dùng AssetResolver và manifest nội bộ cho preview/exam/lesson. |
| P1 | `persistence/database.py` | `question_assets` chỉ có `question_id`, `asset_id`, `original_reference`; thiếu source context, dependency type và resolution status. | Migration bổ sung bảng mapping/columns nullable, giữ dữ liệu cũ đọc được. |
| P1 | `parsing/latex.py` | Parser nhận `includegraphics`, nhưng chưa trả dependency graph cho `graphicspath`, `input/include`, macro động hoặc cycle. | Resolver quét source graph có giới hạn độ sâu, cycle detection và NEEDS_REVIEW. |
| P1 | `ui/import_dialog.py` | Có bảng review, source và preview; chưa có thumbnail/status enum/resource inspector/chọn lại asset/tìm kiếm thư mục. | Phase 3 mở rộng widget hiện tại, không thay layout toàn bộ. |
| P1 | `ui/main_window.py`, `ui/pages/library.py` | Thư viện đã có preview bất đồng bộ, nhưng bộ lọc tài nguyên thiếu/hỏng và trạng thái render chưa có. | Phase 4 thêm filter/status, tái sử dụng splitter/tab hiện có. |
| P2 | `application/library.py:backup/restore` | Backup có DB/assets/sources và checksum nhưng chưa có manifest dependency/profile hoàn chỉnh. | Phase 6 bổ sung thống kê, integrity report và migration/backup manifest. |

## Invariants cần giữ

1. Giữ byte source và source span; resolver chỉ tạo mapping, không rewrite source authoritative.
2. Asset identity là SHA-256 bytes; cùng tên khác bytes là hai asset.
3. Không xóa asset còn được question, revision, snapshot, lesson hoặc export tham chiếu.
4. Câu thiếu dependency không vào trạng thái READY; vẫn có thể giữ trong staging để sửa.
5. Không chạy shell escape hoặc mã nhập; mọi path phải tương đối, chống traversal/symlink và giới hạn kích thước.
6. Snapshot đề/bài giảng phải ghim bytes asset, source và revision.

## Kế hoạch phase

Phase 1 tạo resolver/domain model và migration mapping; phase 2 chuyển kho asset sang content-addressed atomic store; phase 3 tích hợp review UI; phase 4 thêm trạng thái/filter preview trong thư viện; phase 5 thống nhất export/manifest; phase 6 quản lý kho và backup; phase 7 integration/benchmark; phase 8 báo cáo nghiệm thu. Sau mỗi phase chạy test riêng và regression; dữ liệu chỉ dùng fixture/copy.
