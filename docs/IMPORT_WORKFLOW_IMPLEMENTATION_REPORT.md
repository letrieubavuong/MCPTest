# Import Workflow UI

Ngày: 10/10/2026.

Tab Nhập câu hỏi đã chuyển thành wizard 5 bước: Chọn nguồn, Phân tích, Đối chiếu tài nguyên, Xem trước và Xác nhận. Backend staging/review/preview hiện hữu được giữ nguyên; wizard chỉ điều phối trạng thái và hiển thị. Bước xem trước có thẻ Tổng câu, Hợp lệ, Thiếu tài nguyên, Lỗi biên dịch; bảng câu hỏi, cây phân loại, inspector tài nguyên và preview LaTeX vẫn dùng widget hiện tại.

Kiểm chứng ở mốc ban đầu: regression import/navigation **13 passed**; full suite **119 passed in 124.50s**. Các kết quả này là lịch sử của phiên bản wizard ban đầu.

## Bỏ thao tác trùng ngày 11/10/2026

Chọn file TeX, chọn thư mục và hàng chờ chỉ có một vị trí ở bước Chọn nguồn. Thanh công cụ trên cùng chỉ hiện lúc duyệt câu hỏi hoặc chạy tác vụ; Hủy chỉ hiện khi đang phân tích/ghi. Bước tài nguyên không lặp nút mở hàng chờ. Đóng duyệt trở lại bước chọn nguồn và giữ batch, chọn hàng chờ đưa đúng trang duyệt ra trước.

Chọn/bỏ câu dùng checkbox trong bảng; thao tác với nhiều dòng nằm ở menu chuột phải, tránh hai icon dấu X cạnh nhau trên toolbar. Toolbar của widget review được chuyển lên thanh công cụ trang và ẩn bản nội bộ, giữ một nút Nhập câu đã chọn.

Kiểm tra chỉ dùng dữ liệu mẫu riêng. Hai kiểm thử mới xác nhận vị trí duy nhất, callback chọn nguồn, chuyển bước, trạng thái bận/Hủy và hàng chờ; regression nhập/phân loại/navigation và chọn/bỏ qua nhiều trang: **12 passed in 18.94s**. Ảnh sáng/tối ở 1024/1366 px trong `artifacts/import-workflow/`. Lượt full suite/build tiếp theo đã được dừng theo yêu cầu người dùng để ưu tiên push mã nguồn; không tạo EXE/ZIP mới cho thay đổi này. Không đổi schema hoặc nghiệp vụ parser/staging/commit.
