# Asset Integrity and Question Bank UX — Implementation Report

Ngày hoàn tất: 10/10/2026. HEAD ban đầu: `c1b8ee070c5f6c66cbed8c7935ae84789d909b0b`. Working tree ban đầu đã có thay đổi chưa commit từ công việc trước; không commit, push hoặc hoàn tác chúng. Mọi kiểm thử dùng fixture/copy, không mở dữ liệu người dùng thật.

## Kiến trúc và migration

`AssetResolver` là đường chung cho import/review và có model resolution graph: source context, dependency type, candidate paths, SHA-256 và status. Nó hỗ trợ ảnh có/không extension, `graphicspath`, input/include lồng nhau, cycle/depth limit, path traversal, symlink, giới hạn kích thước, định dạng chưa hỗ trợ và tham chiếu động cần review.

`AssetStore` dùng content-addressed path theo prefix hash, staging theo batch, fsync/atomic replace, verify bytes, cleanup và GC dry-run. Schema SQLite tăng từ 17 lên **18** bằng migration thêm metadata nullable-compatible cho `question_assets`; dữ liệu cũ mặc định `legacy/RESOLVED`. Migration có guard cho database phục hồi bị đặt user_version thấp nhưng đã có cột mới.

## Hành vi đã triển khai

- Import giữ nguyên bytes source, archive và spans; câu thiếu/ambiguous/dynamic dependency không được READY.
- Review nhập hiển thị status, tài nguyên, source context; cho phép chọn lại file hoặc thêm thư mục tìm kiếm bằng staging.
- Thư viện lọc có/thiếu/hỏng/cần xem xét tài nguyên; inspector báo integrity và dùng chung.
- Đề từ CSDL có ZIP portable với manifest/checksum; đề học sinh loại đáp án/lời giải khỏi body.
- Cài đặt có quét integrity, dry-run và GC cần xác nhận.
- Mã đề từ file TeX, preview và UI sáng/tối từ phase trước được giữ; source/mẫu gốc và tài nguyên không bị rewrite.

## Kiểm chứng

- Full regression: **118 passed in 109.89s** during the final build (`.runtime/pytest-final` equivalent); the extra test protects exam snapshot assets from GC.
- Phase 1: 39 passed; Phase 2: 40 passed; Phase 3: 23 passed; Phase 4: 18 passed; Phase 5: 22 passed; Phase 6: 7 passed; Phase 7 integration: 20 passed.
- Benchmark synthetic direct questions, shared PNG: 1k parse 0.0790s/resolve 0.8844s/peak 1.12MB; 10k 0.8340s/7.1804s/11.20MB; 50k 3.7132s/30.5712s/56.08MB. Evidence: `artifacts/asset-benchmark.json`.
- UI capture: light/dark at 1366×768 and 1024×768; preview remains rendered and nonblank. Evidence: `artifacts/tex-exams/`.
- pdfLaTeX and MAPClass/ex_test integration tests pass in the full suite. Portable ZIP manifest hashes were checked after extraction in a new directory.

## Build and manual boundary

The source-level acceptance suite passes. EXE build completed with PySide6 6.11.2, PyMuPDF 1.28.0 and PyInstaller 6.22.3. Smoke: exit 0, schema 18, integrity `ok`, 641 nodes; 46 source modules match bundled bytecode. MAPClass/ex_test hashes match and bundled PyMuPDF renders. ZIP `release/LaTeXQuestionStudio-0.5.2-win64.zip` verifies with SHA-256 `7e597d8699ac3e7817106ed4967e644cdcec1ad48cd898118bbb1d9f2521234d`, schema 18 and no bundled user DB/secret config. No clean Windows VM is available, so clean-machine compatibility remains BLOCKED.

Remaining risks: resolver cost is linear and reaches 30.57s/56MB for the synthetic 50k case; full project import with nested files may need worker-level batching for larger real corpora. Dynamic macros remain `NEEDS_REVIEW`; no static resolver can safely guess them. Custom preamble dependency packaging remains restricted to the audited profiles. GC intentionally only considers DB `assets` references; future lesson/exam manifest retention policies should add explicit reference tables before automatic deletion.

Rollback: keep the pre-migration DB backup created by `Database.initialize()`, restore the prior checkout, and use the backup/restore verification path. Do not copy only SQLite without `assets`, `sources`, lesson exports and manifest checksums.
