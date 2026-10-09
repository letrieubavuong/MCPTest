# Kiểm toán kỹ thuật — baseline ce9dbd6

Ngày: 2026-10-09. Working tree sạch trước nhiệm vụ. Không dùng database thật. Phạm vi: parser, curriculum, persistence, import, search, exams, compiler, lesson service và các trang Qt; đọc kiểm thử và luồng tác vụ.

## Luồng dữ liệu
TeX bytes → archive SHA-256 → scanner giữ spans → import_items (raw/working/parsed/diagnostics) → duyệt/gán classification trong parsed_json → transaction questions/metadata/taxonomy/assets/revision. Sửa repository có optimistic revision; metadata tạo revision mới. FTS5 cập nhật bằng trigger. Search phân trang 100–500 bản ghi; taxonomy lọc subtree. Ma trận dùng bipartite matching chống lặp ID, snapshots pin source và permutation. Compiler hash source/profile/dependencies/assets/engine rồi cache PDF; chạy TeX -no-shell-escape ở worker. Bài giảng pin câu, assets và revisions; student_source loại lệnh đáp án theo scanner.

## Vấn đề xác nhận từ mã
| Mức | File / hàm | Bằng chứng / nguyên nhân | Hướng xử lý |
|---|---|---|---|
| P0 | application/exams.py export_tex/content | Đề học sinh vẫn ghi nguyên source có True, shortans và nội dung loigiai vào .tex; chỉ renewcommand để ẩn PDF. Người nhận .tex đọc được đáp án. | Loại answer spans khỏi bản xuất học sinh; giữ nguyên ngân hàng/teacher; từ chối macro chưa chứng nhận. |
| P1 | exams.statistics/is_valid_candidate | candidates tải source rồi get từng ID, parse lại toàn bộ ở mỗi thống kê và sinh đề. | Cache validation theo SHA/version parser, invalidation source; aggregate SQL. |
| P1 | ui/exam_dialog.py refresh_statistics; main_window.generate_exam | Gọi thống kê và sinh đề đồng bộ trên UI thread. | Worker + generation guard + hủy; đo timer responsiveness. |
| P1 | importing.stage | known set đọc toàn bộ latex_source để so trùng; import chưa có cancel trong vòng câu/transaction cuối. | Hash index chuẩn hóa, batch lookup; kiểm tra cancel theo câu và trước commit. |
| P1 | parsing.analyze | Nhiều choice/shortans ở depth 0 ghi đè answer thay vì đánh dấu không chắc chắn. | Diagnostic ambiguous, không xáo câu đó. |
| P1 | main_window.replace_import_content / import_dialog | deleteLater không gọi closeEvent nên preview nền chưa được hủy trước thay control; toolbar actions tách khỏi disabled review khi commit. | Cleanup rõ, chặn thay/gán trong lúc commit. |
| P2 | domain/curriculum.py / main_window.refresh_curriculum_menu | Danh mục và danh sách root hardcode riêng; root MATH10 sắp trước MATH6 theo code. | Catalog JSON giữ IDs và tên; registry động, thứ tự rõ, legacy migration bất biến. |
| P2 | search.find + DB | Thiếu index taxonomy_id→question_id và metadata expressions; statistics/search lặp WHERE. | Index và WHERE dùng chung; EXPLAIN/benchmark. |
| P2 | exams.generate | Chống trùng ID nhưng không cảnh báo nguồn giống/gần giống khác ID. | Cảnh báo, không tự xóa/đổi chọn. |

Không xác nhận P0 mất database: transaction, backup trước migration và giữ revision đã có. Chưa chứng nhận macro tự định nghĩa hoặc MAPClass/ex_test toàn bộ. Sẽ kiểm tra dependency và tích hợp thực tế ở phase 4. Parser validity là cấu trúc scanner, không phải cam kết mọi TeX biên dịch thành công.

## Thứ tự xử lý
Ưu tiên chặn lộ source đáp án trước hiệu năng; phase 2 cache/statistics/seed matching; phase 3 registry curriculum; phase 4 parser/export integration; phase 5 benchmark; phase 6 workers/lifecycle/layout; phase 7 nghiệm thu. Không đổi nghiệp vụ phân loại, không suy đoán mức độ. Kết quả test baseline và benchmark được ghi vào báo cáo cuối với dữ liệu đo thực tế.


## Bằng chứng bổ sung khi triển khai

- P0 `exams.export_tex`: ảnh chỉ nằm trong `loigiai` vẫn được chép vào thư mục học sinh ở baseline. Test `test_student_export_does_not_copy_solution_image` xác nhận bộ học sinh cần lọc tài nguyên theo body đã loại đáp án; bộ giáo viên giữ đủ ảnh.
- P1 `import_dialog.refresh_rows`: baseline tạo một QTableWidgetItem cho mỗi ô của toàn bộ batch. Với 50.000 câu là 250.000 item trên UI thread. Đã phân trang review 200 câu, giữ đầy đủ batch và gán toàn bộ danh sách theo yêu cầu.
- P1 parser `commands/brace_error`: `verb*` nhận dấu `*` làm delimiter, khiến lệnh giả trong đoạn verb có thể tham gia cấu trúc. Test inline verb* và macro definition xác nhận lỗi; scanner giữ nguyên spans và bỏ qua literal.
- Tạo cache theo `LIMIT 256` lặp trên toàn scope là điểm nghẽn mới phát hiện trong benchmark sau triển khai: cold 50.000 khoảng 42 giây. Đã lấy snapshot ID thiếu cache một lần, đọc source theo batch dưới writer lock; không tải tất cả source vào bộ nhớ.

Baseline pytest: **61 passed, 66,34 giây**. Kết quả cuối, benchmark đo và giới hạn tích hợp ở `CODEX_STABILIZATION_REPORT.md` và `PERFORMANCE_BENCHMARK.md`. Đây là lỗi được xác nhận bằng mã/test/đo, không phải suy đoán về nghiệp vụ hoặc dữ liệu thật.

- H?i quy c?a cache ?? ???c ch?n: n?u source ??i sau l?c ??c revision ?? t?o ??, ph?i ph?n t?ch source c?a revision ?? pin thay v? d?ng ??p ?n cache m?i. Test `test_cached_answer_matches_pinned_source_when_question_edited` ki?m tra ??p ?n B c?a revision 1 kh?ng b? thay b?ng ??p ?n D c?a revision 2.
- Import ?? c? ph?n t?ch ???c x?c th?c b?i hash/version; commit m?i d?ng l?i k?t qu? ??, pending t? phi?n b?n c? ho?c kh?ng kh?p hash v?n c? fallback ph?n t?ch. Test `test_import_reuses_validated_parse_and_falls_back_for_old_pending` x?c nh?n kh?ng parse l?p v? fallback m?t l?n.
