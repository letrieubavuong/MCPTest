# Chiến lược migration

Chưa chạy migration legacy. Nguồn đã xác minh MCPTest2020/bin/Debug/MCPDatabase.db (3.010.560 byte); root DB 0 byte không dùng. Read-only mode=ro, schema/checksums trong phase00_evidence.json. Không coi bin/Debug luôn là bản mới nhất: trước migration người dùng chọn nguồn.

| Nguồn | Đích | Chính sách |
|---|---|---|
| DanhsachID.STT | legacy_id_map → taxonomy_nodes.id | Giữ raw STT, ID mới độc lập |
| TYPE | parent_id | 0→NULL; map cha; 3 orphan quarantine với raw parent |
| ID/NDID/Level/Ten | code/name/legacy_level/kind | Giữ Dạng/Loại, không mất quan hệ |
| DanhsachID.TMC | legacy raw JSON | Chưa suy nghĩa |
| DanhsachCH.STT | legacy_id_map → questions.id | Fingerprint/table/STT UNIQUE, idempotent |
| ID | metadata legacy_code | Có thể là mã phân loại chứa X, không unique question ID |
| ND/LG | raw snapshot; source/solution | Giữ nguyên chuỗi, legacy_reconstructed |
| EX | environment metadata | Source nhập: 0 ex, 1 vidu; dữ liệu chỉ 0 |
| LC | candidate type | Chuỗi '0' MCQ/'1' essay; parser kiểm tra, lạ→unknown |
| MD | difficulty_legacy | 0–4→Y/B/K/G/T theo NewMD_SelectionChanged; cognitive=NULL |
| SL | raw legacy usage value | Không tạo lịch sử đề giả |
| TMC câu | question_taxonomy | Map STT taxonomy; hiện 0 orphan |
| True | answer_data derived | Parse nhóm choice; không sửa ND, không chắc→review |

ND/LG cũ không khôi phục byte TeX trước nhập, preamble/whitespace/môi trường bị xóa. Không nối loigiai vô điều kiện vì parser cũ Substring cắt cố định có thể để brace dư. Revision đầu tiên bắt đầu ở migration, không giả lập lịch sử cũ.

## Quy trình và rollback
1. Fingerprint/schema/count/integrity/orphan/cycle/duplicate code preflight; tạo snapshot nhất quán qua SQLite backup API đọc nguồn.
2. DB đích mới, migration version, staging raw rows và map. Mỗi hàng mapped hoặc quarantine có lý do.
3. Import taxonomy giữ cây, cách ly cha thiếu/chu trình; không sửa DB nguồn.
4. Import câu/metadata/revision/provenance, parse answer/resolve assets. Trùng không tự xóa; giữ record/provenance.
5. FTS rebuild; commit transaction; đối soát 3.075 câu/828 nodes gồm quarantine, ND/LG hash, MD/LC counts, FK/answers/assets.
6. Dry run compile với dependency thật; 3.010 MCQ một literal True chỉ là baseline, chưa chứng minh shuffle/compile.
7. Báo cáo nghiệm thu rồi mới đổi DB cấu hình. Backup nguồn và logs giữ lại.

Run khóa fingerprint/version để chạy lại không tạo bản sao; source đổi là run mới có reconciliation. Lỗi trước commit rollback run; lỗi sau upgrade khôi phục DB+assets cùng manifest trước nâng cấp. 3 orphan phải xử lý hoặc quarantine rõ. Thiếu nguồn TeX thì không nghiệm thu bảo toàn byte trước nhập. Phase 01 chỉ nâng schema DB mới, chưa thực thi chiến lược này.
