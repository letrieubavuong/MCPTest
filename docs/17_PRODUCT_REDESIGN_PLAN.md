# Phương án nâng cấp nghiệp vụ và UX — LaTeX Question Studio

Ngày: 2026-10-09. Trạng thái: đề xuất sản phẩm để review, chưa triển khai. Phạm vi: desktop Windows, làm việc offline, một người dùng; có thể tự biên tập và tự duyệt. Nhiều người dùng/phân quyền/server là giai đoạn riêng, không giả định đã có.

## Bổ sung phạm vi đã được người dùng xác nhận

Ứng dụng đồng thời phục vụ thiết kế bài giảng: lý thuyết, các dạng toán, ví dụ, bài tập vận dụng; bài tập trích lọc từ ngân hàng. Đây là nghiệp vụ chính, không còn là mở rộng chờ quyết định. Đặc tả chi tiết: [18_LESSON_AUTHORING_SPEC.md](18_LESSON_AUTHORING_SPEC.md). Xuất tài liệu TeX/PDF là phạm vi đầu; xuất slide Beamer cần mẫu và nghiệm thu riêng.

## 1. Đánh giá lại sản phẩm hiện tại

Bản 0.1.1 là nền tảng kỹ thuật có thể chạy, chưa đạt trải nghiệm của công cụ quản lý ngân hàng và ra đề thực tế. Việc tests pass không chứng minh nghiệp vụ đã đủ. Hai cột đúng cấu trúc nhưng thông tin, thao tác và luồng xử lý còn sơ sài.

Căn cứ source hiện tại:
- ui/metadata_dialog.py: các trường môn/khối/chương/bài/chủ đề là text tự do, dễ lệch tên và cây phân loại.
- application/search.py: exact fingerprint chỉ chuẩn hóa CRLF; near duplicate dùng SequenceMatcher trên toàn source và quét câu trong ngân hàng. Đây không phải kiểm tra tương đương toán học.
- application/importing.py: staging/archive/assets đã có; asset resolver chủ yếu tìm cạnh file nguồn, chưa đủ dependency theo dự án TeX. Thông báo khi không có câu còn chưa tách rõ file không chứa câu và lỗi giải mã.
- ui/exam_dialog.py: ma trận dùng ô text và số lượng; thiếu section, điểm, thời lượng, nguồn khả dụng, nhóm câu và kiểm tra độ phủ nghiệp vụ.
- application/exams.py: đã có seed/snapshot/matching tránh lặp ID; không đồng nghĩa tránh lặp họ câu, duyệt chất lượng hay cân bằng nhiều đề độc lập.
- ui/main_window.py: đã có drawer/pages; CSDL còn hiển thị chuỗi LaTeX cắt ngắn và quá nhiều thao tác phân tán.

Giữ nền tảng bảo toàn nguồn, transaction, revisions, cache/worker, assets theo hash, FTS và snapshot đề. Thiết kế lại cách người dùng vận hành chúng.

## 2. Công việc thực tế của người quản lý và ra đề

Một chu trình chuẩn:
1. Tiếp nhận nguồn từ nhiều bộ đề/giáo viên, ghi nguồn và phạm vi sử dụng.
2. Đọc dự án TeX, gom phụ thuộc, tách câu nhưng bảo toàn file gốc.
3. Kiểm tra câu, đáp án, lời giải, hình, macro, khả năng biên dịch.
4. Phân loại theo chương trình và gắn ID nghiệp vụ.
5. So trùng, phân biệt bản sao với biến thể; xử lý xung đột đáp án.
6. Duyệt câu đủ điều kiện đưa vào ngân hàng dùng ra đề.
7. Lập cấu trúc/ma trận, kiểm tra nguồn đủ, chọn câu và kiểm soát trùng dạng.
8. Tạo mã đề, xem trước, rà đáp án và bố cục in.
9. Phát hành bộ tài liệu học sinh/giáo viên; lưu nguyên bộ đã phát hành.
10. Ghi nhận câu sai, sửa thành phiên bản mới, đánh giá độ phủ và bổ sung nguồn thiếu.

Ứng dụng phải giúp trả lời: đang thiếu câu gì, câu nào dùng được, câu nào có vấn đề, vì sao chọn câu này, mã đề nào sử dụng revision nào, chuyển máy khác có còn đủ hình không.

## 3. Các quyết định thiết kế mặc định

- Giữ hai cột: drawer trái và vùng trang phải; chức năng chính không mở window riêng. Chỉ chọn file, xác nhận và tác vụ phụ ngắn dùng dialog.
- Mở vào Ngân hàng hoặc trang dùng gần nhất. Tổng quan là một trang lựa chọn, không ép người dùng qua dashboard mỗi lần.
- Danh sách câu ưu tiên nội dung đọc được/thumbnail; source TeX chỉ mở khi biên tập.
- Chỉ câu Đã duyệt và đạt kiểm tra kỹ thuật hiện hành được chọn mặc định vào đề chính thức.
- Không tự suy diễn đáp án, nhận thức hoặc mức độ từ nội dung. Gợi ý có nguồn gốc và cần xác nhận.
- Không tự xóa hoặc hợp nhất câu gần trùng. Không tự sửa file nguồn hoặc thay ảnh của toàn bộ câu dùng chung.
- Phân loại dùng danh mục có ID; một nguồn sự thật cho cây và bộ lọc, không nhập chuỗi song song dễ lệch.
- Mã nghiệp vụ hiển thị độc lập ID nội bộ bất biến. Đổi phân loại không làm hỏng lịch sử đề.
- Ngôn ngữ giao diện là tiếng Việt; hiển thị Trắc nghiệm/Đúng sai/Trả lời ngắn/Tự luận, không dùng mcq/essay như nhãn chính.

## 4. Cấu trúc điều hướng và hệ thống giao diện

Drawer nhóm công việc:
- Tổng quan: độ phủ, câu cần xử lý, đợt nhập gần đây, đề gần đây.
- Ngân hàng câu hỏi: tìm, lọc, xem, chọn, sửa, duyệt, lưu trữ.
- Nhập nguồn TeX: các đợt nhập và luồng tiếp nhận.
- Kiểm tra chất lượng: lỗi, thiếu hình/metadata/đáp án, so trùng.
- Ra đề thi: cấu trúc đề, ma trận, giỏ câu, mã đề, preview.
- Bài giảng: tổ chức chương/bài, soạn lý thuyết và dạng toán, chèn ví dụ/bài tập ngân hàng, preview và xuất.
- Kho đề: nháp/đã kiểm tra/đã phát hành và xuất lại.
- Tài nguyên: ảnh, TikZ, phụ thuộc, nơi sử dụng, ảnh thiếu.
- Danh mục: chương trình, phân loại, ID, mẫu đề, profile TeX.
- Cài đặt và sao lưu.

Không cần đưa mọi trang ra drawer cùng lúc ở giai đoạn đầu: Kiểm tra chất lượng có thể chứa tab So trùng, Tài nguyên có thể nằm trong nhóm Quản lý. Drawer thể hiện mục hiện tại rõ ràng, có tooltip khi thu gọn; badge là số việc cần làm, không phải số trang.

Mỗi trang: tiêu đề + mô tả ngắn; toolbar hành động; khu lọc; nội dung; chi tiết theo ngữ cảnh. Một thao tác chính nổi bật trên mỗi bước, không tô xanh toàn bộ nút. Giữ trạng thái lọc, chọn, scroll và bản nháp khi chuyển trang.

Icon: SVG đồng bộ nét 20/24 px, ngân hàng=chồng thẻ, nhập=file+mũi tên, chất lượng=khiên+dấu kiểm, trùng=hai thẻ chồng, ra đề=tài liệu+bút, kho đề=thư mục, tài nguyên=ảnh, danh mục=cây, sao lưu=ổ đĩa+mũi tên. Icon luôn đi cùng chữ hoặc accessible name/tooltip; dùng cùng bộ, không trộn emoji và phong cách. Màu trạng thái kèm chữ: Lỗi/Chờ xử lý/Đã duyệt/Đã phát hành, không chỉ dựa vào đỏ/xanh.

Thiết kế sáng mặc định cho đọc và in, tùy chọn tối. Font UI 13–14 px, nội dung đọc 15–16 px, source monospace riêng. Toolbar gọn, table header đủ rộng, splitter nhớ kích thước, có trạng thái rỗng hướng dẫn làm tiếp. Tại cửa sổ hẹp, chi tiết chuyển sang tab trong cùng trang. Kiểm tra bàn phím, focus, tương phản và DPI 100/150/200%.

## 5. Trang Ngân hàng câu hỏi

Trong vùng nội dung phải:
- Trên: tìm kiếm, bộ lọc nhanh và nút Thêm câu/Nhập nguồn.
- Khu phụ trái: cây Khối → Môn → Chương → Bài/Chủ đề, có tùy chọn đổi cách nhóm. Lưu taxonomy cũ qua mapping, không tự đổi nghĩa ID cũ.
- Giữa: danh sách có checkbox chọn nhiều. Cột mã, tóm tắt đọc được, loại, nhận thức, trạng thái, hình, nguồn, số lần dùng; tùy chọn cột. Công thức/hình xem bằng preview được cache, không ép compile toàn bộ danh sách.
- Khu chi tiết phải: tabs Nội dung, Đáp án/Lời giải, Phân loại, Hình/Tài nguyên, Nguồn, Lịch sử, Đã dùng trong đề.

Một click xem, không mở editor ngay. Nút Biên tập mở vùng làm việc trong trang; source và preview song song, metadata bên cạnh/ở tab. Chọn nhiều có thanh thao tác: gắn nhãn, phân loại, gửi duyệt, thêm giỏ đề, xuất, lưu trữ. Thao tác hàng loạt có preview số câu bị ảnh hưởng và tạo lịch sử; không ghi đè sửa tay không báo.

Tìm kiếm gồm nội dung, mã, nguồn, nhãn; công thức có chế độ tìm literal/token để không giả vờ FTS hiểu toán học. Bộ lọc phụ thuộc và có chip hiển thị điều kiện hiện tại, xóa từng chip, lưu bộ lọc thường dùng. Bộ lọc chất lượng: chưa có lời giải, thiếu hình, chưa duyệt, chưa dùng, dùng gần đây, đang nghi trùng.

## 6. Nhập nguồn TeX: một đợt có thể xử lý, dừng và tiếp tục

Luồng 5 bước nằm trong trang Nhập nguồn:
1. Chọn nguồn: file/nhiều file/thư mục/ZIP dự án; tên đợt, nguồn, năm, môn/khối mặc định; chọn file gốc và profile TeX. ZIP kiểm tra đường dẫn, số file và kích thước trước giải nén.
2. Quét: cây file, file câu hỏi, include/input, ảnh, cls/sty, macro phụ thuộc; cảnh báo encoding, thiếu file, vòng include và nội dung không nhận diện.
3. Review: tabs Tất cả/Mới/Nghi trùng/Thiếu ảnh/Lỗi/Chưa phân loại; list trái và nội dung/nguồn/lỗi phải. Sửa bản làm việc, không sửa bản gốc.
4. Xử lý: áp phân loại cho nhóm chọn, xác nhận gợi ý ID, nối ảnh thiếu, xử lý trùng, đánh dấu câu chờ. Hiển thị rõ tác động.
5. Nhập đã chọn: câu vào trạng thái Nháp/Chờ duyệt, không tự thành Đã duyệt. Báo số tạo mới, liên kết nguồn vào câu có sẵn, biến thể mới, còn chờ, bỏ qua có lý do và lỗi.

Accounting phải khép kín: mỗi vùng nguồn đã nhận diện có đúng một trạng thái; vùng chưa phân tích, preamble, nội dung ngoài câu và file không có câu đều được ghi riêng. Không dùng thông báo lỗi giải mã cho mọi trường hợp không tìm thấy ex. Encoding khác UTF-8/UTF-16 được phát hiện hoặc cho chọn và xem thử, không ép đổi âm thầm. Một file được include nhiều lần cần ghi sự xuất hiện, tránh nhập lặp do traversal.

Có lịch sử đợt, hủy scan, tiếp tục review sau restart; nút ghi dữ liệu chỉ bật cho các mục hợp lệ được chọn. Trong commit atomic: không cho hiểu nút Hủy là có thể bỏ một nửa transaction. Thư mục tạm chưa liên kết được thu gom sau thời gian giữ, không xóa asset đã được tham chiếu.

## 7. Quản lý nội dung và duyệt chất lượng

Tách trạng thái biên tập khỏi kết quả kiểm tra kỹ thuật:
- Biên tập: Nháp → Chờ duyệt → Đã duyệt; Tạm ngưng/Lưu trữ khi cần.
- Kiểm tra: chưa kiểm tra/đạt/cảnh báo/lỗi, gắn với revision, profile và hash asset. Thay nội dung/đáp án/ảnh làm mất hiệu lực kiểm tra tương ứng.

Checklist câu trước ra đề: parse hợp lệ; loại câu rõ; đáp án cấu trúc hợp lệ; tài nguyên đủ; compile đạt profile sử dụng; phân loại tối thiểu; không có xung đột trùng đang chặn; người soạn đã xác nhận đúng nội dung. Compile thành công không chứng minh đáp án toán đúng.

MCQ kiểm tra số phương án theo profile và đúng một đáp án; đúng/sai kiểm tra từng mệnh đề và chính sách đảo; trả lời ngắn phân biệt giá trị hiển thị, dữ liệu chấm, đơn vị và quy ước dấu thập phân; tự luận lưu hướng dẫn chấm/điểm thành phần. Hỗ trợ Đã duyệt có/không lời giải theo chính sách từng ngân hàng, không ép mọi câu phải có lời giải nếu người dùng không yêu cầu.

Revision sửa nội dung không tự kế thừa duyệt cũ. Thay nhãn quản trị thuần túy có thể giữ duyệt theo chính sách được ghi nhận. Một người dùng có thể tự duyệt; vai trò này là trách nhiệm nghiệp vụ, chưa phải hệ thống tài khoản/phân quyền.

## 8. Chống câu trùng và quản lý biến thể

Không có một tỷ lệ similarity duy nhất đủ kết luận trùng. Phân loại:
1. Bản sao nguồn: hash byte/source bảo thủ giống nhau.
2. Cùng câu nhưng trình bày khác: gợi ý từ thân câu, tập phương án, ảnh và cấu trúc macro đã hỗ trợ. Thứ tự phương án có thể khác; phải đối chiếu đáp án theo nội dung phương án.
3. Cùng họ bài nhưng khác số liệu/hình: liên kết họ câu/biến thể, thường giữ cả hai và mặc định tránh chọn hai câu cùng họ vào một đề.
4. Cùng nội dung nhưng đáp án/lời giải khác: Xung đột, chặn duyệt hoặc phát hành đến khi có quyết định.

Trang xử lý: danh sách nhóm nghi trùng, hai preview cạnh nhau, diff source/thân câu/đáp án/lời giải/ảnh/nguồn; nêu lý do gợi ý, không hiển thị phần trăm như độ chắc chắn toán học. Quyết định: liên kết nguồn vào câu có sẵn, giữ độc lập, liên kết biến thể, hợp nhất có chọn trường, hoặc hoãn. Ghi người/thời gian/lý do và có hoàn tác.

Chỉ chuẩn hóa những macro đã hiểu; không bỏ số, dấu âm, đơn vị, điều kiện hoặc nội dung toán khi kết luận exact. Macro chưa hiểu làm giảm mức tin cậy. Khi phương án trùng nội dung hoặc không ánh xạ được đáp án thì báo xung đột, không cưỡng ép matching.

Fingerprint phải xét asset hash: hai câu cùng tên hinh1.png nhưng ảnh khác không là exact duplicate. Ảnh giống hoặc perceptual hash chỉ là tín hiệu; không kết luận hai bài trùng chỉ vì dùng cùng hình. Chạy trong batch và so với ngân hàng, cả khi sửa câu; index tạo tập ứng viên trước khi diff, không quét mọi cặp trên UI thread. Nghiệm thu trên bộ mẫu có người gán nhãn trùng/khác; đo precision/recall và ưu tiên tránh gộp nhầm.

## 9. Hình ảnh, TikZ và phụ thuộc TeX

Mỗi câu cần gói phụ thuộc có thể di chuyển độc lập, không chỉ một chuỗi đường dẫn từ máy người nhập.

Resolver theo file gọi thực tế: include/input tương đối, graphicspath, extension được engine hỗ trợ và thư mục nguồn người dùng chọn. Có cycle detection, báo file ngoài thư mục dự án và yêu cầu người dùng chọn nguồn rõ ràng; không quét toàn ổ đĩa. Macro động không giải được phải giữ nguyên, báo chưa xác minh, có mapping thủ công.

Assets gốc lưu bất biến theo hash; giữ tên/đường dẫn gốc, loại, kích thước, nơi sử dụng. Hai file trùng tên khác bytes tồn tại độc lập. Bản thumb/PNG cho xem trước là cache; không thay PDF/vector gốc bằng raster. Không phóng to ảnh nhỏ rồi báo đã cải thiện chất lượng.

UI ảnh thiếu: câu, reference gốc, nơi đã tìm và nút Chọn file/Chọn thư mục để ghép hàng loạt. Thay ảnh dùng chung cần chọn Chỉ câu này hoặc Những câu đã chọn; tạo asset và revision mới, vô hiệu cache/duyệt liên quan. Xem danh sách câu/đề đang dùng trước khi tác động. Ảnh không dùng chỉ được dọn sau khi kiểm tra cả revision, backup đang quản lý và snapshot đề.

TikZ giữ source; preview dùng profile đã xác minh. Phụ thuộc input dữ liệu/font/macro của TikZ được ghi vào manifest; externalization hoặc chuyển SVG/EPS cần quy trình riêng, không bật shell escape mặc định. Profile tương lai có thể hỗ trợ engine khác khi cần; trước hết kiểm chứng pdfLaTeX với mẫu thực tế. MAPClass/ex_test chỉ chứng nhận khi có đúng file/mẫu và quyền sử dụng.

Snapshot đề pin bytes/hash của assets, macro/profile và source revision, không trỏ duy nhất tới ảnh đang sống trong thư viện. Sửa/xóa ảnh hiện tại không làm đổi đề đã phát hành.

## 10. Ra đề: cấu trúc, ma trận, giỏ câu và mã đề

Bước 1 — Hồ sơ: tên, môn, khối, thời gian, kỳ/năm, tổng điểm, mẫu đầu trang/chân trang, hướng dẫn, chính sách đáp án và loại đề.

Bước 2 — Cấu trúc phần: MCQ/Đúng sai/Trả lời ngắn/Tự luận; số câu, điểm, quy tắc chấm. Phân biệt số câu với số mệnh đề/ý chấm. Câu có ngữ liệu chung là nhóm giữ chung, không tách/ngẫu nhiên hóa từng phần như câu độc lập.

Bước 3 — Ma trận: hàng chủ đề, cột nhận thức; tùy chọn chi tiết loại câu, số câu/điểm. Mỗi ô có Cần/Có/Thiếu, xem ứng viên, gắn câu bắt buộc/loại trừ. Tổng điểm tự kiểm tra; nhận thức khác difficulty legacy. Khi ô chồng điều kiện, tính khả dụng trên tập ứng viên toàn cục; không cộng số hiển thị từng ô rồi kết luận đủ.

Bước 4 — Ràng buộc: chỉ Đã duyệt; tránh cùng ID/họ câu; nguồn cho phép; giới hạn câu từng dùng gần đây; câu bắt buộc, thứ tự phần, khóa câu/nhóm; target độ khó nếu có dữ liệu được duyệt. Thiếu nguồn phải chỉ rõ ô và các ràng buộc loại ứng viên; nới điều kiện là quyết định có ghi nhận, không âm thầm lấp.

Bước 5 — Chọn và review: giỏ câu từ ngân hàng hoặc sinh theo ma trận. Thay một câu bằng ứng viên cùng tiêu chí, xem tác động điểm/phủ và giữ các câu khóa. Quay lại bước trước không xóa cấu hình. Lưu nháp/tự lưu, resume sau restart.

Bước 6 — Mã đề: tách hai chế độ: cùng bộ câu, đảo thứ tự; hoặc nhiều bộ câu độc lập cùng ma trận. Cùng seed chỉ tái lập khi pin cả tập ứng viên, revisions, thuật toán và cấu hình. Chế độ bộ câu độc lập cần tính khả dụng liên mã; không hứa mọi mã không trùng khi nguồn không đủ.

Chính sách xáo từng câu: cho phép xáo/giữ nguyên/khóa nhóm. Mặc định không đảo phương án dạng 'cả A và B', 'tất cả đáp án trên' hoặc tham chiếu vị trí nếu chưa chuyển đổi an toàn. Đúng/sai chỉ đảo mệnh đề khi có chính sách và mapping kiểm chứng; câu chung hình/chuỗi ý giữ quan hệ. Mã đáp án gắn option ID trước khi đổi sang A/B/C/D, không xử lý bằng thay chữ đơn giản.

Bước 7 — Kiểm tra trước phát hành: ma trận/điểm, ID/họ trùng, đáp án, assets, macro, PDF, dòng/trang, đánh số và hướng dẫn. Bảng đối chiếu các mã: vị trí → ID/revision → thứ tự option → đáp án. Xem PDF từng mã trong trang; người dùng xác nhận layout in và nội dung, không chỉ exit code compiler.

Ví dụ minh họa, không phải mặc định quy chế: 45 phút, 10 điểm; 12 MCQ × 0,25 = 3 điểm; 4 trả lời ngắn × 0,5 = 2 điểm; 2 tự luận tổng 5 điểm. Hệ thống kiểm tra 18 câu/10 điểm, độ phủ chủ đề và từng mã. Đúng/sai dùng chính sách chấm do người dùng chọn, không mặc định một công thức cho mọi kỳ thi.

## 11. Xuất và phát hành

Các gói tách rõ:
- Học sinh: PDF sẵn in; tùy chọn source đã loại đáp án/lời giải.
- Giáo viên: đáp án bảng theo mã, PDF lời giải, hướng dẫn chấm/điểm thành phần.
- Dự án TeX đầy đủ: main.tex + assets + các dependency được phép phân phối + manifest/profile/readme. Nhãn rõ có đáp án hay không.
- Ngân hàng trao đổi: source câu + metadata + tài nguyên + provenance; khác với gói đề học sinh.

Ẩn True/loigiai khi render không có nghĩa đã loại đáp án khỏi file TeX được bàn giao. Xuất source học sinh phải loại dữ liệu đáp án thật trên cây cú pháp hỗ trợ; macro lạ không kiểm chứng được thì chặn xuất source học sinh hoặc chỉ xuất PDF đã kiểm tra. Kiểm tra cả comment, file phụ và phụ thuộc đi kèm; không giao nguyên dự án chứa lời giải dưới nhãn 'học sinh'. Với PDF kiểm tra text extract và xem hình/trang, kể cả đáp án có thể được render thành hình.

Xuất thử và Phát hành là hai hành động khác nhau. Compile trong staging, chỉ công bố bộ đầu ra khi toàn bộ mã đề qua kiểm tra; không để file nửa chừng ghi đè bản cũ. Phát hành ghi snapshot source/assets/profile/engine/version/seed/mapping, checksum và lưu chính PDF đã phát hành. Không hứa biên dịch lại cho bytes PDF giống tuyệt đối trên runtime khác. Sửa đề phát hành tạo phiên bản mới, bản cũ vẫn tải lại được.

## 12. Mô hình dữ liệu cần bổ sung

| Nhóm | Dữ liệu |
|---|---|
| Nội dung | question UUID, mã hiển thị, revision, trạng thái duyệt, kiểm tra theo revision, họ câu, nhóm/ngữ liệu |
| Đáp án | option/statement ID, correct flag/value/rubric, chính sách shuffle, điểm thành phần |
| Phân loại | taxonomy/version, mapping mã cũ, nhãn, nguồn, nhận thức và difficulty riêng |
| Nguồn nhập | dự án/batch/file/span/encoding/hash, coverage, working copy, quyết định nhập |
| Tài nguyên | asset version/hash/type/original path, dependency graph, liên kết revision và snapshot |
| So trùng | nhóm/cặp, features/phiên bản thuật toán, quyết định/lý do, merge và undo |
| Đề | nháp, section/matrix/ràng buộc, giỏ/khóa, candidate snapshot, mã đề và mapping |
| Bài giảng | bài/revision, cây block có thứ tự, lý thuyết/dạng toán/ví dụ/bài tập, liên kết revision câu, quy tắc trích lọc, snapshot và xuất |
| Phát hành | PDF/TeX/assets đóng băng, profile/engine, validation, checksum, lịch sử sử dụng |

Migration có backup và đọc thử; câu cũ mặc định Chưa duyệt/Chưa kiểm tra, không tự đạt chất lượng vì đã tồn tại. Đề cũ thiếu snapshot asset được đánh dấu mức tái lập hạn chế. Không ép dữ liệu legacy vào mapping NB/TH/VD/VDC chưa xác minh.

## 13. Lộ trình và cổng nghiệm thu

| Chặng | Sản phẩm review được | Điều kiện qua chặng |
|---|---|---|
| A — Thiết kế nghiệp vụ | Wireframe có click của các luồng ngân hàng, nhập, chất lượng, ra đề và bài giảng, icon/style, mẫu nguồn và checklist | Người dùng thao tác được nhập → quản lý → xử lý trùng → ra đề mà không cần giải thích code |
| B — Ngân hàng và duyệt | Danh sách đọc được, bộ lọc danh mục, chi tiết, batch edit, trạng thái duyệt | Tìm/chọn/sửa/duyệt nhóm câu; sửa nội dung làm hết hiệu lực duyệt cũ; không mất bản gốc |
| C — Nhập dự án và tài nguyên | Review theo đợt, coverage, input/graphicspath, nối ảnh, resume | Import bộ mẫu giữ đủ câu/nguồn/phụ thuộc; chuyển thư mục/máy vẫn preview được; hủy/restart không mất trạng thái |
| D — Chất lượng và trùng | So sánh hai câu, nhóm biến thể, xung đột, undo | Cùng hình khác tên, cùng tên khác ảnh, đảo option, khác số/đơn vị và đáp án xung đột đều được xử lý đúng trên corpus gán nhãn |
| E — Ra đề và phát hành | Ma trận có nguồn, giỏ/khóa/thay câu, mã đề, preview, gói phát hành | Đúng quota/điểm, không lặp ID/họ theo chính sách, mapping đáp án đúng, source học sinh không chứa đáp án |
| E2 — Thiết kế bài giảng | Cây bài và block, lý thuyết/dạng toán, ví dụ/bài tập ngân hàng, trích lọc, bản giáo viên/học sinh | Soạn được bài hoàn chỉnh; sửa cục bộ không đổi ngân hàng; xuất ổn định với ảnh và revision đã chốt |
| F — Bàn giao thực tế | Bộ dữ liệu nghiệm thu, EXE, hướng dẫn, backup/restore | Windows sạch với TeX đã cấu hình; nhập → ra nhiều mã → giải nén xuất compile; khôi phục đủ DB, assets và bài giảng |

Chặng A làm trước việc tô icon toàn ứng dụng. Sau khi ổn định luồng, triển khai từng lát nghiệp vụ hoàn chỉnh, không đánh dấu xong chỉ vì có nút hoặc dialog. Chưa chốt số ngày khi chưa benchmark corpus ảnh/macros thực tế và kiểm tra môi trường đóng gói.

Mục tiêu UX đề xuất: người đã biết quy trình tìm đúng câu mẫu trong ≤30 giây, xử lý một lỗi ảnh thiếu trong ≤60 giây, lập đề từ ma trận lưu sẵn trong ≤5 phút với dữ liệu đủ. Đây là mục tiêu usability cần đo, không phải kết quả đã đạt. Benchmark tăng dần 3.075 câu thực tế → 10.000/50.000 câu có ghi rõ dữ liệu tổng hợp/thực; đo UI, search, indexing, import, compile riêng. Không dùng benchmark 3.075 câu để tuyên bố khả năng 100.000 câu.

## 14. Bộ tình huống nghiệm thu bắt buộc

1. Dự án nhiều input, tên có khoảng trắng/tiếng Việt, graphicspath và hai ảnh cùng tên khác nội dung.
2. File không có ex, encoding không đọc được, macro lạ, environment hỏng, vùng ngoài câu: accounting đúng và nguồn còn nguyên.
3. Nhập lại cùng bộ đề: xem rõ câu có sẵn, không nhân bản âm thầm; có thể chỉ bổ sung nguồn.
4. Cùng câu đảo option nhưng True đúng; cùng đề bài khác đáp án; khác dấu âm/đơn vị: không gộp nhầm.
5. Thiếu ảnh → chọn lại → preview → export → chuyển thư mục vẫn compile; không cần đường dẫn tuyệt đối máy cũ.
6. Câu chưa duyệt bị loại khỏi nguồn đề; sửa câu đã duyệt phải duyệt revision mới.
7. Ma trận từng ô tưởng đủ nhưng toàn cục thiếu vì chồng điều kiện: chỉ đúng nguyên nhân.
8. Câu không được xáo, nhóm chung ngữ liệu và biến thể cùng họ tuân thủ ràng buộc.
9. Bốn mã cùng bộ câu và bốn bộ độc lập: mapping và khả dụng liên mã đúng theo từng chế độ.
10. Source/PDF học sinh không lộ đáp án; bộ giáo viên vẫn có đủ đáp án/lời giải.
11. Sửa câu/ảnh sau phát hành: đề cũ và PDF cũ không thay đổi.
12. Hủy, crash, restart, backup/restore, DPI cao, Windows sạch: không mất hoặc liên kết nhầm dữ liệu.

## 15. Những điểm cần xác nhận trước thiết kế chi tiết

Mặc định đề xuất để tiếp tục thiết kế: ngân hàng Toán THPT, cá nhân/offline, đủ bốn loại câu, nhiều mã cùng bộ câu là chế độ ưu tiên. Cần xác nhận khi có corpus thực tế: hệ mã ID đang dùng; mẫu đề và quy tắc chấm; ưu tiên cùng bộ câu hay các bộ độc lập; profile MAPClass/ex_test và các macro/ảnh phải hỗ trợ. Có thể dùng mẫu nguồn đã ẩn thông tin cá nhân. Đây là đầu vào cho thiết kế chi tiết, không phải yêu cầu sửa thêm ứng dụng trong lần lập phương án này.