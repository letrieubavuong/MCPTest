# UI-01 — Audit giao diện

Audit mã nguồn ngày 09/10/2026: main_window, editor, import_dialog, exam_dialog, lesson_page và test navigation/shell/import_layout/stabilization_ui. Giữ nguyên working tree ổn định kỹ thuật, không commit/push.

| Màn hình | Vấn đề cụ thể | Tác động / ưu tiên |
|---|---|---|
| Shell | Drawer 205px cạnh explorer; chỉ CSDL có dock/log, các trang thiếu cùng cấu trúc | Lãng phí ngang, thiếu nhất quán — P0 |
| CSDL | Cột nội dung là 100 ký tự LaTeX, không chọn để preview; tìm/lọc mở dialog; metadata yêu cầu mở editor | Phân loại khó, nhiều bước — P0 |
| Editor | Có gutter/highlight/completion nhưng chưa tự thụt dòng; tìm/thay dùng hai dialog; gutter tối cả theme sáng | Gián đoạn biên tập — P0 |
| Nhập | Toolbar cùng cấp; thiếu chọn loại bỏ; nhãn trạng thái không biểu thị các bước; chỉ tổng lỗi | Dễ nhập câu không muốn — P0 |
| Ra đề | Form dọc chiếm chiều cao; cây/thống kê trên, ma trận dưới; không thấy câu đã lấy hay preview | Khó đối chiếu nguồn và đề — P0 |
| Bài giảng | Outline nhiều nút lớn; xuất/preview nằm riêng phía phải; bank picker có nguồn thô | Mất không gian, phân tán thao tác — P1 |
| Responsive | Preview đặt minimum theo ảnh; cột ma trận rộng, toolbar có thể dồn overflow | Cần splitter, fit ảnh và kiểm tra nhiều kích thước — P0 |

Đã có phân trang (100 CSDL, 200 review), job cancel/generation guard, cache compiler, dirty tabs và revision/snapshot; tái sử dụng. Không biên dịch cả ngân hàng. Các dialog chọn file, xác nhận mất dữ liệu và chọn nơi xuất vẫn hợp lý.

Ảnh trước: `artifacts/stabilization-import.png`, `artifacts/stabilization-exam.png` (fixture tổng hợp, không dữ liệu cá nhân). CSDL/editor/bài giảng chưa có ảnh trước được chụp riêng trong audit.
