# Phase 2 — Portable Asset Store

Ngày: 09/10/2026.

Implemented `AssetStore` with SHA-256 content-addressed paths, two-phase batch staging under `.asset-staging`, fsync plus atomic replace, checksum verification, cleanup after commit/failure, integrity reports and dry-run garbage collection. Import now stages asset bytes before commit and promotes them only during commit; source archives and question source remain authoritative.

Validation: **40 passed** in 5.47 seconds for asset resolver/import/persistence/stabilization tests. The tests verify staging is not visible as a final asset, promotion/checksum, dry-run and actual GC, source deletion after import, and no READY question for unresolved assets. No user data was modified.
