# Phase 6 — Asset Management and Backup Safety

Ngày: 10/10/2026.

`LibraryService` now exposes integrity and garbage-collection reports. Settings includes a `Quản lý tài nguyên` section for scanning the content-addressed store, inspecting unlinked files in dry-run mode and confirming cleanup. Cleanup checks database references before deleting and reports missing/corrupt/shared counts. Existing backup/restore checksum and rollback paths continue to include nested asset paths.

Validation: **7 passed in 7.56 seconds** for management, review UI, library asset filters, app and shell smoke tests. The management test confirms dry-run does not delete and confirmed GC removes only an unlinked asset. No real data directory was touched.
