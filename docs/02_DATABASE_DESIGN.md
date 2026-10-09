# Thiết kế dữ liệu

DDL cũ và counts được xác minh trong phase00_evidence.json; mô hình dưới là đích đề xuất. Phase 01 triển khai subset nền tảng, chưa migration dữ liệu cũ.

## Schema cũ
DanhsachID: STT INTEGER PK AUTOINCREMENT, ID TEXT, NDID TEXT NOT NULL, TYPE INTEGER NOT NULL, Level INTEGER, Ten TEXT, TMC INTEGER. DanhsachCH: STT INTEGER PK AUTOINCREMENT, ID TEXT, ND TEXT NOT NULL UNIQUE, LG TEXT, EX INTEGER NOT NULL, LC TEXT NOT NULL, MD INTEGER NOT NULL, SL INTEGER NOT NULL, TMC INTEGER. Không FK khai báo; TYPE là cha STT theo source; LC thực tế chuỗi '0'/'1'.

| Bảng đích | Khóa và nội dung |
|---|---|
| taxonomy_nodes | id PK, parent_id self FK, kind/name/code/legacy_level; giữ Dạng/Loại |
| subjects, grades | Danh mục dùng chung; UI/domain typed views, không làm mất cây legacy |
| questions | UUID PK, type, latex_source, source_origin, solution, answer_data JSON, difficulty_legacy, cognitive_level, hash, revision, timestamps |
| question_taxonomy | PK kép question_id/taxonomy_id, FK |
| tags, question_tags | Tag name UNIQUE, liên kết PK kép |
| source_files | Hash byte, encoding, tên nguồn, archive relative path |
| import_batches, import_items | Status/stats; source offsets/raw_source/diagnostics/question FK nullable |
| assets, question_assets | Content hash UNIQUE, managed relative path; original_reference/resolution |
| question_revisions | FK question, revision_no, source/metadata snapshot; UNIQUE(question,revision) |
| question_duplicates | Ordered pair ID, algorithm/version/score/review status |
| exam_papers, exam_versions | Seed/matrix/preamble/config snapshots |
| exam_questions | Version/position/question/revision/permutation/answer snapshot; không lặp câu mỗi version |
| compilation_cache | Key gồm source/preamble/dependencies/engine/config, output/size/last_access/status |
| app_settings | Key/value JSON/version; không secrets |
| legacy_records, legacy_id_map | Fingerprint/table/STT UNIQUE, raw row, mapped id, run id |
| migration_runs | Source fingerprint/counts/diagnostics/status |

## Ràng buộc và giao dịch
Bật foreign_keys mỗi connection; index parent/type/cognitive/hash/taxonomy/revision. Không UNIQUE source_hash để giữ provenance khác. FTS5 là dữ liệu dẫn xuất, cập nhật cùng transaction và rebuild được. Assets/nguồn lưu path tương đối chống traversal. Không lưu base64 assets mặc định.

Root TYPE=0 chuyển parent=NULL; orphan giữ raw ID và quarantine, không tạo FK sai. taxonomy_nodes bảo toàn cây là phương án thay các bảng chương/bài/chủ đề riêng; typed views phục vụ UI. difficulty_legacy và cognitive_level không tự quy đổi.

Migration versioned có backup trước nâng schema; lỗi rollback toàn run. Backup phải nhất quán DB và assets; không copy DB đang WAL tùy tiện. Staging import tách commit ngân hàng, writer queue và read connections riêng.

## Hiện thực Phase 01
Dùng sqlite3 chuẩn với controlled migration PRAGMA user_version thay SQLAlchemy/Alembic ở skeleton. Có taxonomy_nodes, questions, question_taxonomy, question_revisions; revision snapshot JSON, CHECK/FK/index và optimistic revision check. Các bảng import/assets/exam/cache/FTS bổ sung bằng migration ở phase tương ứng. Xóa repository hiện cascade revisions; archive/restore phục vụ UI phải thiết kế ở Phase 04.
