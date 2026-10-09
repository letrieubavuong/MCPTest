# Phase 08 — Hiệu năng và ổn định

Migration v5 tối ưu FTS rowid và index pagination; migration v6 giữ raw_source gốc và working_source/import_repairs cho sửa hàng chờ. Import staging/commit và compile/dedup/export chạy worker, pool tối đa 2, cancel khi đóng app. Có test timer UI chạy xuyên import/commit 500 câu. Menu phân nhóm, context taxonomy, archive câu giữ revisions, metadata type/difficulty/cognitive; preview nhiều trang và crop lề trắng để dễ đọc. QScreen chụp riêng window tránh artefact QWidget.grab của scroll viewport.

29 tests đạt trước kiểm tra cuối. Corpus read-only 3.075 ND cũ bọc ex: 3.074 nhập, 1 quarantine (STT463 thiếu True trong nhóm option hợp lệ). Benchmark cuối artifacts/phase08_benchmark.json: stage 1,33s, commit 1,96s, search median 18,9ms, page median 20,7ms, preview mẫu 3,43s, cache 13,5ms, integrity ok. Chỉ preview mẫu hợp lệ được benchmark, không claim mọi legacy macro compile. Đây là dữ liệu 3.075 câu thực tế, chưa benchmark hàng trăm nghìn câu.

Các test bảo toàn source/asset/answer, rollback/restore, stale edits, Unicode/FTS/matrix và UI pipeline đều chạy. Source legacy không thay đổi. Không commit/push. Tiếp tục Phase 09 đóng gói, docs và kiểm tra EXE độc lập Python.
