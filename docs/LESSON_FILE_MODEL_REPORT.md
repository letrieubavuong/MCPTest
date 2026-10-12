# Mô hình file nguồn bài giảng

Ngày 10/10/2026.

## Vấn đề cũ

Trang Bài giảng trước đây hiển thị một cây block, nhưng không có khái niệm file nguồn. Khi xuất, toàn bộ nội dung được nối vào `main.tex`; vì vậy cấu trúc thực tế của một bài giảng gồm nhiều file không được phản ánh trong DB hoặc giao diện.

## Mô hình mới

DB schema 19 có thêm `lesson_files` và `lesson_file_exercises`. `lessons.document_json` vẫn giữ `file_model_version=1` và `files` để snapshot/backup tương thích; mỗi entry có `id`, `role`, `title`, `filename`, `block_ids` và `locked`:

- `theory` → `theory.tex`: lý thuyết bài.
- `method` → `dang-XX-*.tex`: một dạng toán, gồm phương pháp và toàn bộ ví dụ con.
- `exercise` → `bai-tap-van-dung.tex`: nhóm bài tập vận dụng.

`lesson_files` lưu source tổng hợp, role, vị trí, filename và trạng thái chốt. `lesson_file_exercises` lưu từng `question_id`, revision, source snapshot, `export_index` và trạng thái khóa. Block/source/revision vẫn được giữ nguyên trong document để tương thích dữ liệu hiện tại và phục vụ WYSIWYG. File manifest là lớp tổ chức phát hành; không sao chép câu vào ngân hàng và không làm mất source cũ.

Khi mở document cũ không có `files`, `LessonService` dựng manifest từ cây block và đồng bộ sang hai bảng mới. Khi bài tập thay đổi, file bài tập bị mở khóa; muốn xuất phải bấm **Chốt file và chỉ mục xuất**. Khi xuất, ứng dụng tạo các file `.tex` riêng, `main.tex` dùng `\input{...}`, PDF/assets/manifest checksum và snapshot vẫn được lưu trong `lesson_exports`. Như vậy người dùng có thể mở DB để tiếp tục soạn hoặc lấy bộ TeX đã xuất để biên dịch bên ngoài.

Giao diện hiển thị vùng **TỆP NGUỒN BÀI GIẢNG** dưới outline, cho biết file hiện tại, số mục thuộc file và trạng thái lưu DB/xuất TeX. Chọn file sẽ đưa con trỏ tới mục đầu tiên của file.

Giao diện không còn coi outline là toàn bộ bài: file nguồn là selector độc lập bên dưới outline; outline chỉ là các mục thuộc file đang chọn. Kiểm thử mới: **5/5** cho manifest mặc định, nâng document cũ, DB source/index, khóa export, file_sources giữ dạng toán cùng ví dụ, và export nhiều file/`main.tex` input. Cùng với regression bài giảng hiện có: **14/14** kiểm thử lesson/file đạt.
