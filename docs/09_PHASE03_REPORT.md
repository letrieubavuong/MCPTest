# Phase 03 — Scanner và nhập

Có scanner command/comment/escape/brace/environment, parser ex/ex*/vidu/vidu*, choice/TF/TFt/shortans/loigiai/hdan, asset resolver includegraphics, lưu archive byte gốc theo hash và source span. Stage/errors bền vững qua migration v2; review trước commit, trùng gợi ý không tự xóa. Worker nền có hủy/progress; lỗi không bị bỏ âm thầm. Không sửa nguồn.

Thay đổi parsing/latex.py, application/importing.py, ui/jobs.py, ui/import_dialog.py, ui/main_window.py và database migration; tests/test_import.py. 19 tests đạt trước phần bổ sung thống kê trùng. Corpus DB cũ: 3075 ND được bọc ex, 3075 round-trip source; 1 mục có diagnostics, giữ để xử lý. Chi tiết artifacts/phase03_corpus.json. Không giả đó là source TeX gốc; LG/preamble đã bị parser cũ biến đổi nên chưa kiểm chứng byte trước nhập.

Giới hạn: scanner không thực thi TeX expansion tổng quát; macro sinh môi trường cần review; thiếu class/style và nguồn file corpus. Hàng chờ có thể xem lại, công cụ sửa/commit từng mục sẽ hoàn thiện trong vòng ổn định. Không commit/push.
