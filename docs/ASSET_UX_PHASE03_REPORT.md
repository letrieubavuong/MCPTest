# Phase 3 — Import Review UI

Ngày: 09/10/2026.

The existing three-pane import review now shows explicit statuses (`READY`, `MISSING_ASSET`, `AMBIGUOUS_ASSET`, `NEEDS_REVIEW`, `INVALID_LATEX`, `DUPLICATE`), an asset inspector with source context, and resource counts. The toolbar adds `Chọn lại ảnh/tài nguyên` and `Thêm thư mục tìm kiếm tài nguyên`; replacements are staged with `AssetStore` and only become durable when the reviewed batch is committed. The original source editor/preview and pagination remain in place.

Validation: **23 passed in 29.66 seconds** for review UI, import classification/layout, stabilization UI and library UI regression. A missing image remains visible in review and cannot be committed as READY. No database outside test fixtures was opened.
