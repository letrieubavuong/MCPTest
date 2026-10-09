# Phase 06 — Search và dedup

Migration v3: FTS5 unicode61/remove_diacritics và folding đ→d, trigger đồng bộ source/metadata/delete, merge ledger. Bộ lọc subject/grade/chapter/lesson/topic/source/tag/type/cognitive/difficulty và subtree, query tham số hóa/FTS token quote. Gần trùng worker dùng SequenceMatcher, exact hash chỉ chuẩn hóa CRLF (giữ số/math/True/space). Merge sau xác nhận lưu ledger snapshot, archive bản phụ; không xóa nguồn/revisions/answers/assets.

25 tests đạt, gồm tiếng Việt không dấu, metadata/tag filters, cập nhật search, exact/near/merge lưu bản phụ. Thay đổi application/search.py, database migrations/triggers, main_window và tests/test_search.py. UI bộ lọc metadata hiện có; loại/nhận thức sẽ bổ sung khi hoàn thiện sản phẩm. Không commit/push.
