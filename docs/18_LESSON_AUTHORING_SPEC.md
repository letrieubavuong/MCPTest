# Thiết kế bài giảng — đặc tả nghiệp vụ đề xuất

Ngày: 2026-10-09. Bổ sung theo yêu cầu người dùng; nghiệp vụ bài giảng là phạm vi chính. Tài liệu thiết kế đích; bản 0.2.0 đã triển khai lát soạn bài mới. Xem 19_LESSON_IMPLEMENTATION_REPORT.md để phân biệt phần đã có và phần còn lại. Duy trì cấu trúc drawer trái và trang chức năng phải. Ngân hàng câu hỏi, đề thi và bài giảng dùng chung nguồn/tài nguyên nhưng có cấu trúc và vòng đời riêng.

## 1. Mục đích

Giáo viên tổ chức kiến thức và hoạt động học, không chỉ ghép danh sách câu. Một bài cần mục tiêu, kiến thức nền, lý thuyết, dạng toán/phương pháp, ví dụ có hướng dẫn, bài tập luyện tập/vận dụng và bài tập về nhà. Mục tiêu, thời lượng và bài tập về nhà là tùy chọn; bốn nhóm người dùng xác nhận là lý thuyết, dạng toán, ví dụ, vận dụng.

Mặc định ưu tiên tài liệu bài giảng TeX/PDF in được. Không đồng nhất tài liệu với slide trình chiếu; Beamer là đầu ra bổ sung khi có mẫu cụ thể, cần thiết kế phân trang/frame và kiểm chứng riêng. Không tự mở rộng thành LMS, quản lý lớp hay giao/chấm bài trực tuyến.

## 2. Cấu trúc nội dung

```text
Chương / Chủ đề
└── Bài: Ứng dụng đạo hàm
    ├── Mục tiêu / Kiến thức cần nhớ [tùy chọn]
    ├── A. Lý thuyết
    │   ├── Định nghĩa / Định lý / Công thức
    │   └── Chú ý và hình minh họa
    ├── B. Các dạng toán
    │   ├── Dạng 1: Xét tính đơn điệu
    │   │   ├── Nhận diện và phương pháp giải
    │   │   ├── Ví dụ 1 + hướng dẫn / lời giải
    │   │   ├── Ví dụ 2
    │   │   └── Bài tập luyện tập cho dạng 1
    │   └── Dạng 2: Tìm cực trị [cấu trúc tương tự]
    ├── C. Bài tập vận dụng tổng hợp
    └── D. Bài tập về nhà [tùy chọn]
```

Đây là mẫu khởi tạo, không phải cây cứng. Cho thêm, đổi tên, kéo thả, di chuyển lên/xuống, nhân bản và ẩn mục ở bản xuất. Có lệnh bàn phím thay kéo thả. Dạng toán chứa phương pháp, ví dụ và bài tập theo thứ tự giáo viên quyết định. Giữ nhóm ngữ liệu/câu chung khi di chuyển.

Nội dung được lưu bằng các khối có ID: đoạn văn/TeX, định nghĩa, định lý, công thức, chú ý, hình/TikZ, dạng toán, ví dụ, nhóm bài tập và ngắt trang. Không ép toàn bộ bài thành một câu hỏi hoặc một chuỗi source duy nhất khó quản lý. Khối TeX tự do vẫn được phép, giữ nguyên source; cấu trúc nội bộ macro chưa hiểu không bị tự sửa.

## 3. Giao diện trang Bài giảng

Drawer chính có mục Bài giảng. Bên trong vùng nội dung phải:
- Trang danh sách: lọc môn/khối/chương, tên bài, trạng thái, ngày sửa; Tạo bài/Tạo từ mẫu/Nhập TeX/Nhân bản.
- Khi mở bài, thanh đầu: breadcrumb, tên, trạng thái lưu; Thêm nội dung, Chèn từ ngân hàng, Xem trước, Xuất.
- Khu cây nội dung bên trái của trang: lý thuyết/dạng toán/ví dụ/bài tập, icon theo loại khối, lỗi theo từng mục. Đây là cây của bài, không thay drawer toàn ứng dụng.
- Khu giữa: biên tập khối đang chọn; tab Nội dung/Source TeX. Metadata của bài và thuộc tính khối ở panel có thể mở/đóng.
- Khu phải: preview khối hoặc toàn bài, chuyển Bản học sinh/Bản giáo viên; splitter và chế độ tập trung cho màn hình nhỏ.

Người dùng nhìn thấy thứ tự dạy học, không bị buộc làm việc với một danh sách source. Mỗi nhóm bài tập có số câu, mức độ và lỗi thiếu nguồn/hình. Nhấp một lỗi đi đúng khối. Toolbar theo ngữ cảnh: thêm ví dụ khi đang ở dạng toán, chọn bài tập khi đang ở nhóm bài tập. Có undo/redo, tự lưu bản nháp, khôi phục sau restart và cảnh báo nội dung chưa lưu.

## 4. Chèn ví dụ và trích bài tập từ ngân hàng

Chèn từ ngân hàng mở panel chọn trong trang, giữ nguyên vị trí đang soạn. Panel dùng lại bộ lọc/preview/ngân hàng, không tạo bản ngân hàng riêng.

Hai cách chọn:
1. Chọn tay: lọc, xem, tick nhiều câu rồi chèn vào đúng mục.
2. Trích lọc: đặt điều kiện môn/khối/chủ đề/dạng/loại/nhận thức/nhãn/nguồn, số lượng hoặc phân bổ; preview nguồn khả dụng và các câu được chọn; xác nhận chèn.

Quy tắc trích lọc được lưu để tái sử dụng, nhưng một lần trích phải tạo danh sách câu cụ thể và pin revision. Mở lại hoặc xuất lại bài không được tự rút bộ câu mới. Rút lại/thay câu là hành động riêng, có preview thay đổi; câu khóa được giữ.

Ví dụ: trong Dạng 1, chọn hai ví dụ cơ bản và sáu bài luyện tăng dần; trong phần tổng hợp, chọn bốn câu từ các dạng đã học. Số lượng này chỉ minh họa. Thiếu nguồn chỉ rõ điều kiện, không tự nới hoặc lặp câu cho đủ.

Theo dõi vai trò sử dụng: Ví dụ, Luyện tập, Vận dụng, Về nhà. Ngăn lặp cùng ID trong nhóm; cảnh báo cùng họ bài trên toàn bài giảng. Khác đề thi, giáo viên có thể chủ động lặp câu từ ví dụ sang luyện tập để ôn lại; phải chọn Cho phép lặp và có lý do, không chặn tuyệt đối. Không tự xáo câu/phương án khi chèn, vì thứ tự có thể phục vụ tiến trình dạy học.

Mặc định ưu tiên câu Đã duyệt. Cho chèn câu nháp trong bài nháp với badge rõ; trước phát hành yêu cầu duyệt hoặc một quyết định ngoại lệ có ghi nhận, không âm thầm coi là đạt.

## 5. Quan hệ giữa bài giảng và ngân hàng

Ba thao tác phân biệt rõ:
- Chèn tham chiếu: pin question ID + revision và tài nguyên của revision đó. Có provenance về ngân hàng, không nhân bản câu vào ngân hàng mỗi lần sử dụng.
- Tạo bản dùng riêng trong bài: sửa lời dẫn, cách diễn đạt, gợi ý, lời giải hoặc trình bày của bản cục bộ. Giữ liên kết nguồn và diff; không cập nhật ngược ngân hàng.
- Đề xuất cập nhật ngân hàng/Tạo câu mới: thao tác riêng có xác nhận, preview tác động, revision và quy trình duyệt.

Nếu ngân hàng có revision mới: hiện thông báo và diff, cho cập nhật từng câu/nhóm hoặc giữ bản cũ. Không tự cập nhật làm thay nội dung đã dạy hoặc đã phát hành. Khi câu được lưu trữ khỏi ngân hàng, snapshot bài cũ vẫn đọc/xuất được. Nội dung lý thuyết nhập trong bài không tự tạo thành câu hỏi; lưu làm khối tái sử dụng hoặc chuyển thành câu hỏi là hành động chủ động.

## 6. Biên tập lý thuyết, dạng toán và ví dụ

Lý thuyết hỗ trợ cấu trúc Định nghĩa/Định lý/Công thức/Chú ý và TeX tự do. Dạng toán có tên, dấu hiệu nhận diện, phương pháp/các bước, điều kiện áp dụng, lỗi thường gặp; các trường tùy chọn.

Ví dụ gồm đề bài và phần hướng dẫn/lời giải, có thể tự viết hoặc lấy từ ngân hàng. Cho phép ghi chú giảng dạy riêng của giáo viên và khoảng trống cho học sinh làm bài. Phân biệt lời giải của câu trong ngân hàng với phần diễn giải sư phạm bổ sung trong bài. Có đánh số theo bài hoặc theo dạng, cross-reference dùng ID ổn định thay vì gõ cứng số thứ tự.

Bản học sinh không mặc định ẩn mọi ví dụ đã giải: ví dụ mẫu có lời giải có thể là nội dung cần học. Chính sách xuất theo từng khối: hiện đầy đủ, chỉ đề bài, hiện gợi ý, chừa chỗ làm; ghi chú riêng giáo viên luôn loại khỏi bản học sinh. Có preview chính xác trước xuất và cấu hình mặc định theo vai trò khối. Người dùng có thể ghi đè rõ ràng ở từng ví dụ/nhóm bài tập.

## 7. Nhập bài giảng TeX có sẵn

Cần parser tài liệu có cấu trúc ngoài scanner câu hỏi: section/subsection, môi trường lý thuyết được profile hỗ trợ, dạng toán, ví dụ, bài tập, hình và input.

Không được dùng luồng nhập ex hiện tại rồi bỏ đoạn lý thuyết giữa các câu. Giữ toàn bộ byte gốc, thứ tự, preamble, dependency và coverage. Phần chưa ánh xạ được thành khối TeX tự do/chờ review với vị trí nguồn. Cho giáo viên xác nhận cấu trúc trước khi lưu.

Các macro định lý/dạng toán tùy chỉnh cần profile và mẫu thực tế. Không giả định macro của MCPTest hay MAPClass có nghĩa khi chưa đọc đúng nguồn. Vòng đầu ưu tiên soạn bài mới; nhập đầy đủ bài giảng cũ là lát triển khai riêng, không tuyên bố chỉ parser ex là đã hỗ trợ.

## 8. Hình ảnh và tái sử dụng nội dung

Lý thuyết, phương pháp và ví dụ đều có thể chứa ảnh/TikZ, không chỉ bài tập. Dùng chung asset store/dependency resolver của ngân hàng, nhưng liên kết tới block/revision bài. Kéo/chèn hình tạo bản quản lý, không chỉ trỏ file ngoài.

Một hình dùng nhiều bài được dedup theo bytes; thay hình tạo asset mới và revision liên quan. Đề/bài giảng phát hành giữ source và assets đóng băng. Cache preview xét source khối, thứ tự/đánh số/cross-reference, template và dependency; đổi thứ tự hoặc đổi lời giải hiện/ẩn phải invalidate đúng preview toàn bài.

Kho khối tái sử dụng là giai đoạn sau: phương pháp, lý thuyết, hình, mẫu dạng toán; khi dùng lại cũng chọn pin hoặc sao chép cục bộ, không có cập nhật dây chuyền âm thầm.

## 9. Xuất bài giảng

Đầu ra đầu tiên: PDF/TeX bài giảng, phiếu bài tập được chọn từ bài, bản giáo viên và bản học sinh. Tùy chọn đáp án/lời giải ở ngay sau câu hoặc cuối tài liệu. Mẫu kiểm soát font, header/footer, mục lục, đánh số, khoảng trống và ngắt trang; nội dung độc lập mẫu trình bày.

Đối với source học sinh, loại ghi chú riêng/đáp án/lời giải bị ẩn khỏi cả source và file phụ, không chỉ dùng macro giấu khi render. Phân biệt lời giải ví dụ cố ý công khai với đáp án bài tập cần ẩn. Profile không chứng minh được việc loại dữ liệu thì chặn gói source đó và giải thích tại khối có vấn đề.

Xuất toàn bài kiểm tra cross-reference, mục lục, thứ tự, đánh số, ảnh, tràn trang và PDF. Lưu snapshot bài gồm cây khối, câu/revision, override, quy tắc chọn, assets, template/profile, PDF thực tế. Đổi ngân hàng hay template sau phát hành không làm đổi bộ đã xuất.

Xuất Beamer chỉ bổ sung khi chốt mẫu: mapping nội dung sang frame, chia nội dung dài, hiển thị lời giải từng bước, cross-reference và hình. Không coi việc bọc cả bài trong frame là hỗ trợ slide đúng nghiệp vụ.

## 10. Dữ liệu và vòng đời

Đề xuất: lessons, lesson_revisions, lesson_blocks có parent/order/type/payload; question_references pin revision; local_overrides; exercise_sets và selection_recipes; block_assets/dependencies; lesson_templates; lesson_exports/snapshots. Đây là thiết kế, chưa migration.

Bản nháp lưu cấu trúc và nguồn tham chiếu; kiểm tra chất lượng theo revision; phát hành tạo snapshot. Revision bài cần bao gồm thứ tự khối và chính sách hiển thị đáp án, không chỉ nội dung text. Bộ backup/restore bao gồm toàn bộ bài, source, revisions, assets và exports theo chính sách giữ.

Thống kê sử dụng phân biệt Đã dùng làm ví dụ, Đã giao luyện tập, Đã đưa vào đề kiểm tra; không cộng gộp thành một số khiến người ra đề loại nhầm câu chưa từng thi.

## 11. Lộ trình bổ sung

1. Wireframe: thư viện bài → tạo bài mẫu → cây lý thuyết/dạng toán → chèn từ ngân hàng → preview hai đối tượng → xuất.
2. Soạn bài mới: block, reorder, source/preview, autosave, ảnh, template tài liệu.
3. Tích hợp ngân hàng: chọn tay/trích lọc, pin revision, override cục bộ, cảnh báo trùng và thay câu.
4. Phát hành tài liệu: phiếu bài tập, học sinh/giáo viên, đáp án/lời giải, snapshot và backup.
5. Nhập bài giảng cũ/tái sử dụng khối; slide Beamer theo mẫu thực tế là chặng riêng nếu được ưu tiên.

Lát đầu phải hoàn thành một bài có đủ lý thuyết, hai dạng toán, ví dụ và bài tập vận dụng lấy từ ngân hàng, xuất TeX/PDF có hình. Không đánh dấu hỗ trợ bài giảng khi mới có một ô editor hoặc chức năng ghép câu.

## 12. Nghiệm thu

- Tạo và lưu bài có đầy đủ bốn nhóm nội dung người dùng yêu cầu; đóng/mở vẫn giữ thứ tự và bản nháp.
- Chèn câu từ ngân hàng vào đúng dạng; trích lọc báo đủ/thiếu, không tự rút lại khi mở hoặc xuất.
- Sửa câu riêng trong bài không đổi câu ngân hàng; cập nhật ngân hàng không tự đổi bài.
- Cảnh báo lặp giữa ví dụ/luyện tập/vận dụng; cho phép lặp có chủ đích, giữ nhóm ngữ liệu.
- Có hình/TikZ ở lý thuyết và ví dụ; gói xuất chạy ở thư mục khác, không phụ thuộc đường dẫn máy soạn.
- Bản học sinh giữ lời giải ví dụ được chọn công khai, loại ghi chú riêng và đáp án bài tập được đặt ẩn; bản giáo viên có đủ.
- Đổi thứ tự đánh số/cross-reference đúng; sửa sau phát hành không đổi PDF/source cũ.
- Import mẫu bài có lý thuyết ngoài ex không mất đoạn; phần macro chưa hiểu còn nguyên và có trạng thái review.
- Backup/restore khôi phục cây bài, pinned revisions, ảnh và bản phát hành.