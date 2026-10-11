# WYSIWYG trong Soạn bài giảng

Ngày: 10/10/2026. HEAD giữ nguyên `c1b8ee070c5f6c66cbed8c7935ae84789d909b0b`; working tree đã có thay đổi chưa commit khi bắt đầu. Không commit hoặc push, không dùng CSDL người dùng thật để thử nghiệm.

## Thay đổi

Soạn bài giảng mặc định dùng vùng trực quan có thể chỉnh sửa, đồng bộ với editor LaTeX hiện có. B/I/U áp dụng định dạng trên văn bản chọn; có tiêu đề, danh sách, chèn/sửa công thức, undo/redo. Công thức, ảnh và TikZ render bằng Compiler/pdfLaTeX nền trong cùng tài liệu, có cache và generation guard khi đổi block. PDF toàn bài vẫn dùng profile MAPClass/ex_test để kiểm tra bản in.

`parsing/visual.py` tạo projection từ source spans, dùng parser nhóm/lệnh hiện có. Wrapper, comment, đáp án, macro lạ và môi trường TeX giữ source nguyên văn; chỉ phần được sửa được cập nhật. `ui/wysiwyg.py` dùng QTextEdit/QPyTextObject với các đối tượng công thức và anchor cấu trúc. Xóa phạm vi làm mất cấu trúc câu/đáp án bị từ chối; vẫn có thể sửa cấu trúc chủ động ở Mã LaTeX. Văn bản thường được escape; công thức có dấu phân cách và lệnh định dạng đã hỗ trợ được nhận dạng khi nhập/dán hoàn chỉnh.

Đồng bộ qua editor source hiện hữu, tiếp tục dùng LessonService/autosave/revisions/teacher-student policies. Sửa câu ghim chỉ đổi bản trong bài giảng. Không đổi schema hoặc định dạng lưu; bài cũ mở trực quan và có thể quay về mã nguyên vẹn. Chuyển theme/chế độ không tạo revision; đổi block hủy kết quả render cũ.

## Phạm vi

- Văn bản, đậm/nghiêng/gạch chân, section/subsection, itemize/enumerate.
- ex/vidu, bốn phương án MCQ/TF, shortans và lời giải; True/cấu trúc giữ trong source.
- Math inline/display, equation/align/gather và TikZ render thành đối tượng có thể mở sửa.
- Macro/bảng/môi trường chưa hỗ trợ chỉnh trực quan được giữ dưới dạng đối tượng TeX, không đoán kết quả khai triển.
- WYSIWYG áp dụng cho tab Bài giảng; editor ngân hàng câu hỏi hiện có giữ nguyên.
- WYSIWYG phản hồi văn bản tức thời; công thức render nền cần pdfLaTeX. Bố cục trang in lấy từ tab PDF; đây không phải chỉnh trực tiếp trên trang PDF.

## Kiểm chứng

24 kiểm thử WYSIWYG đã đạt, gồm round-trip source/Unicode/comment/TikZ/macro lạ/malformed TeX, sửa trực quan, định dạng, bảo vệ cấu trúc, undo/redo, sync hai chế độ, autosave/reopen, bảo toàn câu ngân hàng, theme, loại kết quả render cũ, mở đối tượng từ vị trí con trỏ và xuất PDF thật. Ảnh sáng/tối ở 1024x768, 1366x768, 1600x900 và PDF nằm trong `artifacts/wysiwyg/`; script `scripts/capture_wysiwyg.py` dùng dữ liệu mẫu riêng.

Lượt build WYSIWYG ban đầu: **143 passed in 249.82s**. EXE smoke exit 0, SQLite integrity `ok`, schema 18, 641 node; 50 module bundle khớp source, gồm `ui.wysiwyg` và `parsing.visual`. Đã mở EXE với bản copy bài giảng mẫu, đợi render và chụp vùng WYSIWYG thực tế: exit 0, stderr rỗng; xem `artifacts/wysiwyg/bundle-window.png` và `bundle-smoke.json`. Không chứng nhận Windows VM sạch.

## Sửa nhập công thức theo ảnh phản hồi

Đã tái hiện lỗi: dán `\subsection{NỘI DUNG BÀI GIẢNG}` và `$a=\dfrac{v^2-v_0^2}{2s}$` vào vùng trực quan làm dấu phân cách và lệnh bị escape như chữ thường. PDF vì vậy in nguyên mã. Lỗi thuộc bộ chuyển đổi WYSIWYG, không phải pdfLaTeX hoặc công thức người dùng.

- Nhận dạng công thức/lệnh định dạng hoàn chỉnh khi nhập/dán, chuyển ngay thành đối tượng/định dạng trực quan. Các ký tự thường như `50%`, `&`, giá `$5` vẫn là văn bản. Hộp chèn công thức nhận biểu thức không cần bọc `$`.
- Nút **Nhận dạng lại công thức LaTeX** chỉ hiện khi nội dung có mã đã bị escape có thể khôi phục. Người dùng chủ động bấm; giữ revision và undo. Không sửa ngầm nội dung đã lưu; LaTeX đúng có ký tự escape được giữ nguyên.
- **Xem trước** mặc định dựng **Mục đang soạn**, không thêm tiêu đề bài hay các mục rỗng. Chọn **Toàn bài giảng** để xem bố cục MAPClass đầy đủ. Xuất TeX/PDF tiếp tục xuất cả bài theo cấu hình.
- Công thức nhiều tầng như phân thức dùng chiều cao phù hợp trong vùng trực quan, tránh ép mọi công thức vào 28 px.

Kiểm thử tập trung: **31 passed in 26.12s**, gồm 7 kiểm thử mới cho paste/gõ công thức, phân biệt văn bản thường, khôi phục dữ liệu đã escape và undo/revision, render/PDF thật cho đúng ví dụ trong ảnh, hai phạm vi preview. `scripts/capture_formula_input_fix.py` chỉ dùng dữ liệu mẫu riêng; ảnh khôi phục, vùng soạn sáng/tối ở 1024/1366/1600 px và PDF ở `artifacts/formula-input-fix/`. PDF trích xuất không chứa `dfrac`/`subsection`, phân thức có mẫu số `2s` và không có banner toàn bài ở phạm vi mục.

Kiểm thử toàn bộ trong lượt build bản sửa: **150 passed in 267.76s (0:04:27)**. Build EXE đã hoàn tất; smoke exit 0, stderr rỗng, schema 18, integrity `ok`, 641 node phân loại. Kiểm tra 17 module UI trong lượt build và 37 module được bundle trong `scripts/verify_formula_bundle.py` đều khớp source; bốn module liên quan nhập công thức/preview khớp đầy đủ. Module `ui.metadata_dialog` không được bundle vì giao diện hiện tại không import nó.

EXE đã mở bản copy dữ liệu mẫu, render đúng phân thức và chụp vùng WYSIWYG thực tế; xem `artifacts/formula-input-fix/bundle-window.png` và `bundle-smoke.json`. Hash của mốc sửa công thức trước khi chuyển launcher GUI: `85171da7800510af2c51d31859041984a52037fff53b67958ef8b145440fdcfa`. Bản chạy ở `dist/0.5.2/LaTeXQuestionStudio/LaTeXQuestionStudio.exe`; bản trước được giữ trong `.runtime/bundle-before-formula-input-fix-20261010`. Build mới đã chuyển sang Windows GUI, không mở CMD; kết quả mới và hash xem `WINDOWED_BUILD_REPORT.md`. Ảnh/bundle-smoke công thức đã được cập nhật với EXE GUI và cache trống.

Gói ZIP dùng manifest 150 tests và kèm ảnh/báo cáo riêng ở `verification/formula-input-fix/`. Kiểm tra bản giải nén bằng `scripts/verify_ui_package.py --zip release/LaTeXQuestionStudio-0.5.2-win64.zip --output-dir artifacts/formula-input-fix`; kết quả và hash ZIP ở `artifacts/formula-input-fix/zip-smoke.json`, checksum độc lập ở file `.zip.sha256` trong release. Chỉ kiểm chứng trên máy hiện tại, chưa chạy Windows VM sạch. Không thay đổi schema, không tự sửa dữ liệu thật, không commit/push.
