# Yêu cầu nghiệp vụ

Nguồn chuẩn: LATEX_QUESTION_STUDIO_CODEX_PLAN.md. Bằng chứng kế thừa: 00_MCPTEST_AUDIT.md. Đặc tả không đồng nghĩa tính năng đã triển khai.

## Kế thừa và viết lại
Giữ cây/mã phân loại từ MainViewModel.LoadIDTreeview và UserQLID.ThemIDCSDL; nhập ex/vidu/ID/lời giải từ UseNhapCSDL; lọc và chọn không lặp từ UserRutdeHH; chỉ tiêu ma trận từ UserMatrande; ý định so trùng từ UserTimcautrung. Viết lại parser, transaction, sampling và dedup để tránh mất nguồn. Thiết kế bài giảng đã được người dùng xác nhận là nghiệp vụ chính: lý thuyết, dạng toán, ví dụ và bài tập trích lọc từ ngân hàng. Xuất tài liệu TeX/PDF ưu tiên trước; Beamer trong UserXuatBeamer cần mẫu và nghiệm thu đầu ra riêng. Xem 18_LESSON_AUTHORING_SPEC.md.

| ID | Yêu cầu | Nghiệm thu |
|---|---|---|
| BR01 | Câu độc lập file, metadata/assets/provenance/revision | Sửa có revision, khôi phục nguyên văn |
| BR02 | Nhập một/nhiều file/thư mục, tiến trình và hủy, staging | Mọi vùng nguồn có trạng thái; lỗi có vị trí, không mất câu |
| BR03 | ex/ex*/vidu/vidu*, choice/choiceTF/choiceTFt/shortans/loigiai/hdan/True | Scanner xử lý comment, brace lồng và escape; macro lạ giữ nguyên |
| BR04 | Commit batch transaction | Lỗi rollback; staging vẫn review được |
| BR05 | Editor tab/highlight/số dòng/tìm thay/undo/snippets | Dirty tab có Lưu/Bỏ/Hủy, restart an toàn |
| BR06 | Preview câu được chọn, TikZ/ảnh, pdfLaTeX/PDF render/cache | Cache hợp lệ tức thì, không hiển thị result câu cũ |
| BR07 | FTS5 và lọc metadata | Query tham số hóa, kiểm thử tìm tiếng Việt |
| BR08 | Exact/near dedup | Giữ số/công thức/True, không tự xóa |
| BR09 | Chọn tay/ma trận/xáo câu và phương án | Không lặp ID, quota đúng, lưu seed/revision, bảo toàn đáp án |
| BR10 | Xuất tex/PDF/đáp án/lời giải | Corpus compile đạt hoặc dependency thiếu báo rõ |
| BR11 | Offline/backup/restore/EXE Windows | DB+assets khôi phục, máy sạch có TeX chạy được |
| BR12 | Thiết kế bài giảng có lý thuyết/dạng toán/ví dụ/bài tập | Cây nội dung giữ thứ tự, soạn và xuất bài hoàn chỉnh |
| BR13 | Chọn/trích lọc bài tập từ ngân hàng | Pin revision, báo thiếu nguồn, sửa cục bộ không đổi ngân hàng |
| BR14 | Xuất bài giảng học sinh/giáo viên và phiếu bài tập | Chính sách lời giải theo khối, assets đầy đủ, snapshot không đổi |

## Quy tắc
Giữ byte nguồn/encoding/hash và source span; ND/LG cũ đã bị biến đổi phải có snapshot và source_origin=legacy_reconstructed. difficulty_legacy Y/B/K/G/T độc lập cognitive_level NB/TH/VD/VDC; chưa rõ để NULL. Loại chưa parse chắc là unknown. Hủy trước commit không đổi ngân hàng. Merge là thao tác có xác nhận/revision/provenance.

## Quyết định còn mở
Mapping 5 mức cũ sang 4 nhận thức; ưu tiên cây Khối→Môn hay Môn→Khối; cung cấp MAPClass/ex_test/preamble/assets có quyền dùng; mẫu Beamer và phạm vi web. Bài giảng đã vào phạm vi chính theo yêu cầu mới. Mặc định bảo toàn legacy, nhận thức trống, giữ cấp cây cũ; phạm vi thiết kế được bổ sung bài giảng theo yêu cầu mới.
