# Danh mục chương trình học phiên bản 1

Catalog tích hợp: `src/latex_question_studio/domain/data/curricula.json`. Các migration 8–15 giữ nguyên, không đổi IDs, tên chương/bài hay câu đã liên kết. Migration 17 chỉ bổ sung `curriculum_profiles` và `curriculum_order`, có backup trước nâng schema. Thứ tự hiển thị lấy từ dữ liệu; các menu gốc tự lấy từ SQLite.

Mỗi profile có `root_id`, `subject`, `grade`, `book`, `version`, `nodes`. Mỗi node có `id`, `parent_id`, `kind`, `name`, `code`, `description` (có thể null), `display_order` số nguyên. Các bộ sách/phiên bản khác nhau phải có root và node ID riêng. Không dùng tên hiển thị làm ID, không tái sử dụng ID cũ cho phiên bản khác.

Ví dụ tệp bổ sung:

```json
{
  "schema_version": 1,
  "profiles": [{
    "root_id": "curriculum:math7:mybook:2026",
    "subject": "Toán", "grade": "7", "book": "Bộ sách riêng", "version": "2026",
    "nodes": [
      {"id": "curriculum:math7:mybook:2026", "parent_id": null, "kind": "subject", "name": "TOÁN 7 — Bộ sách riêng", "code": "MYBOOK", "display_order": 1000},
      {"id": "curriculum:math7:mybook:2026:lesson:01", "parent_id": "curriculum:math7:mybook:2026", "kind": "lesson", "name": "Bài 1: Bài do giáo viên cung cấp", "code": "MYBOOK-B01", "display_order": 1001}
    ]
  }]
}
```

API quản trị hiện có: `LibraryService(services).install_curriculum(path)`. Cần dùng `services` của đúng thư mục dữ liệu; API tạo backup, validate cây/ID, cài trong một transaction, trả đường dẫn backup. Mở lại ứng dụng để các cây đã khởi tạo cùng nhận chương trình mới. Chưa bổ sung hộp thoại quản lý catalog trong đợt ổn định này.

Cài lặp không đổi tên đã tùy chỉnh hoặc liên kết cũ (`INSERT OR IGNORE`). Thay `book/version/subject/grade` của root ID đã dùng bị từ chối; muốn phiên bản mới hãy cấp ID mới. Mức độ nhận thức vẫn do giáo viên gán, không suy ra từ tên bài hay bộ sách.
