# UI-02 — Đặc tả redesign

Activity Bar 64px, tooltip và Ctrl+1/Ctrl+I; trang giữ nguyên instance khi chuyển. Mỗi workspace có toolbar theo ngữ cảnh, cây trái, nội dung giữa, inspector phải. Panel dùng QSplitter, đóng/mở và lưu sizes/visibility vào workspace.json. CSDL có bottom panel nhật ký/tác vụ/lỗi. Theme dùng palette và token module riêng, không stylesheet MainWindow.

CSDL: tìm nhanh debounce, bộ lọc loại/nhận thức/trạng thái, chọn nhiều; compact list hoặc thẻ với ảnh render của câu đã yêu cầu. Chọn câu mới chỉ render câu đó, debounce/cancel/generation guard; cache RAM giới hạn cộng cache compiler hiện có. Inspector chứa preview, metadata chỉnh trực tiếp, source và lỗi. Không chuyển sang editor chỉ để xem. Editor tái sử dụng highlight/gutter, thêm find/replace inline và tự thụt dòng.

Nhập: chỉ báo Chọn tệp → Phân tích → Duyệt/phân loại → Xác nhận. Từng câu có checkbox nhập, lỗi và gợi ý trùng. Phân loại hàng loạt giữ API hiện có; commit chỉ IDs được chọn, câu bỏ lại vẫn trong pending. Không thay parser.

Ra đề: explorer trái; thống kê NB/TH/VD/VDC và ma trận giữa; danh sách thủ công/snapshot và preview phải. Form cấu hình gọn; primary Tạo đề, secondary cấu hình/matrix/export. Preview snapshot dùng source đã ghim, không đọc source mới từ ngân hàng.

Bài giảng: outline, editor/bank tabs và preview cùng workspace; thao tác outline/biên dịch/xuất chuyển toolbar; giữ autosave/revision/question snapshot, chèn qua nút hiện có.

Nghiệm thu: pytest và fixture UI tổng hợp, ảnh 5 trang × 2 theme; 1366×768, 1600×900, 1920×1080; kiểm tra chuyển trang, splitter, dirty editor, tìm/lọc, chọn bỏ nhập và preview cũ. Ghi rõ phần chưa đạt trong báo cáo, không tự tuyên bố hoàn thành dựa trên màu/icon.
