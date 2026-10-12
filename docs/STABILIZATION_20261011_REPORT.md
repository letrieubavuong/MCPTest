# Ổn định và phát hành lại bản 0.5.2

Ngày 11/10/2026. Không triển khai phase mới, không commit/push. Chỉ dùng dữ liệu kiểm thử riêng; không mở ngân hàng cá nhân khi nghiệm thu.

## Các lỗi hồi quy đã xử lý

- Thanh điều hướng bị đổi từ 64 lên 68 px làm hỏng hợp đồng layout; đã giữ chiều rộng 64 px.
- Migration schema 19 chạy lại khi bảng đã tồn tại gây lỗi. Đã thêm kiểm tra tồn tại cho bảng/index và nghiệm thu giữ nguyên dữ liệu khi nâng từ trạng thái phục hồi có `user_version` thấp hơn.
- Đồng bộ mục được chọn sau khi refresh cây/chèn câu đã được sửa để lưu vào đúng mục bài giảng.
- Script build xóa staging đã verify khi gặp ứng dụng đang mở. Đã giữ staging sau khi EXE/ZIP đạt, và ghi JUnit trước bước thay bản. Bản vừa bị dọn được phục hồi từ bản giải nén của lần kiểm tra ZIP còn lại; hash EXE và mọi module được đối chiếu trước khi dùng lại.
- Kiểm tra bytecode trước đây đọc PYZ từ workdir, có thể kiểm tra nhầm bản. Script nay đọc archive trực tiếp từ EXE đang nghiệm thu; khi được cung cấp PYZ build, kiểm tra thêm hai archive khớp nhau.

## Bằng chứng kiểm thử

Ba lượt full suite ở lượt ổn định trước phát hành đều đạt **162/162**: 225,11 giây, 222,98 giây, và 225,34 giây trong lượt build cuối. Đây là kết quả đã chạy trước khi người dùng đóng ứng dụng. Lượt tiếp tục chỉ phục hồi/phát hành lại cùng mã ứng dụng; toàn bộ 37 module đã bundle khớp source, gồm persistence/database và application/lessons.

EXE SHA-256: `033173d201f55790a9de0fc84e1aad13f69cc2099e57b2680017a4f7f93e6cfd`. Nghiệm thu candidate: exit 0, stderr rỗng, subsystem Windows GUI 2, ICO đủ 10 cỡ, schema 19, integrity `ok`, 641 node phân loại. `ui.metadata_dialog` không được bundle do không được giao diện hiện tại import; không có module được dùng nào lệch source.

Đã thay EXE vào đúng đường dẫn và nghiệm thu lại cùng kết quả. Kiểm thử thao tác thay bản/dọn tệp: **6 passed in 6.51s**. Bản ZIP mới đã giải nén và khởi chạy exit 0; toàn bộ module và icon khớp source, không kèm database người dùng hoặc cấu hình bí mật.

Kiểm tra EXE với dữ liệu mẫu schema 18 có bài giảng/câu ghim: nâng lên 19, backup vẫn ở schema 18, source bài giảng và câu ngân hàng không đổi, integrity `ok`; tạo 1 PDF công thức mới từ cache trống. Kết quả `migration-smoke.json`, ảnh `schema19-lesson.png` nằm trong cùng thư mục bằng chứng. Bản cũ/staging và các bản giải nén thử được dọn sau khi bản mới đạt.

Bản chạy: `dist/0.5.2/LaTeXQuestionStudio/LaTeXQuestionStudio.exe`. ZIP/checksum: `release/LaTeXQuestionStudio-0.5.2-win64.zip` và `.zip.sha256`. Kết quả EXE/ZIP hiện hành nằm trong `artifacts/stabilization-20261011/`; chỉ kiểm chứng trên máy Windows này, chưa nghiệm thu VM sạch.

Mô hình bài giảng schema 19 vẫn là lát triển khai hiện có: bảng nguồn/snapshot/chỉ mục cùng editor nội dung và selector tệp. Việc hoàn thiện màn hình quản lý theo từng file là công việc phase tiếp theo; báo cáo này không coi đó là đã hoàn thành.
