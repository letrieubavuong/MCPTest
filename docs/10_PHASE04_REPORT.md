# Phase 04 — Thư viện và dữ liệu

Có metadata môn/khối/chương/bài/chủ đề/nhãn/nguồn, taxonomy có parent FK và lọc subtree, revision snapshot/khôi phục tạo revision mới. Backup ZIP có manifest SHA-256, DB nhất quán qua SQLite backup API và sources/assets; restore kiểm tra checksum/schema/FK trước thay DB, giữ rollback DB. Đã sửa connection SQLite không tự đóng khi dùng context manager trên Windows; dùng closing để giải phóng file trước dọn staging.

Thay đổi application/library.py, ui/metadata_dialog.py, main_window và questions snapshot; tests/test_library.py. 21 tests đạt gồm reopen, metadata/taxonomy, revision, DB+asset backup/restore và từ chối backup hỏng/path traversal. Không merge/xóa tự động, không migrate legacy. Restore UI có xác nhận và xử lý dirty tabs. Không commit/push.
