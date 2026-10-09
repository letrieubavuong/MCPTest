# Khắc phục lỗi

- EXE không mở: giải nén cả thư mục, giữ _internal. Xem logs/studio.log trong thư mục dữ liệu. Không dùng DB cũ đặt tên studio.db: schema lạ sẽ bị từ chối để bảo vệ nguồn.
- Preview không có engine: cấu hình đường dẫn pdflatex.exe. Thiếu package: bổ sung qua TeX distribution ngoài app. Không cài package qua mạng tự động.
- Undefined control sequence: macro không có trong profile article. Chọn preamble thật cùng cls/sty; MAPClass/ex_test chưa có trong máy khảo sát nên chưa được nghiệm thu tương thích.
- Thiếu ảnh: giữ đường dẫn nguồn tương đối đúng và file ảnh cạnh file nhập, sửa trong Hàng chờ rồi kiểm tra lại. Assets nhập thành công được quản lý theo hash.
- PDF lỗi: xem source:dòng trong log, cấu trúc brace hoặc TeX math sai phải sửa; timeout 45 giây và hủy không làm treo UI.
- Không có kết quả search: kiểm tra filter/node đang chọn, dùng Xóa tìm kiếm/bộ lọc. Đếm bảng là số câu đang lọc, không phải toàn DB.
- Save báo stale edit: câu đã có revision mới ở phiên khác; giữ source đang sửa, mở lại câu để đối chiếu. Không tự ghi đè.
- Backup lỗi checksum/schema: không phục hồi bản hỏng. Dùng bản ZIP khác; DB hiện tại chưa bị thay khi validation thất bại.
- Telegram timeout: delivery unconfirmed, không tự retry để tránh gửi lặp. Script chỉ báo success khi API ok=true và không in token/URL bí mật.

Giới hạn đã biết: chưa có chứng cứ compatibility MAPClass/ex_test/preamble gốc; parser không thực thi TeX expansion tùy ý, macro sinh cấu trúc cần hàng chờ; benchmark 3.075 câu thực tế, chưa hàng trăm nghìn; chưa kiểm tra EXE trên VM Windows sạch riêng. Không thay dữ liệu MCPTest2020.
