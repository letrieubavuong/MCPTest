# Bàn giao MCPTest / LaTeX Question Studio

Ngày bàn giao: 09/10/2026. Repository: https://github.com/letrieubavuong/MCPTest — nhánh `main`. Phiên bản ứng dụng: **0.5.2**; schema SQLite: **17**. Commit chứa tài liệu này là mốc tiếp tục công việc.

## Mục tiêu và nguyên tắc sản phẩm

Ứng dụng desktop Windows quản lý ngân hàng câu hỏi từ TeX, phân loại, ra đề theo ma trận và thiết kế bài giảng. Một cửa sổ chính: thanh điều hướng bên trái, nội dung chức năng bên phải. Cây CSDL Môn → Chương → Bài → Dạng là điểm vào chính, phải giữ rõ ràng và dễ dùng ở thư viện, nhập câu hỏi và ra đề. Không chuyển mỗi chức năng thành cửa sổ riêng.

Bài giảng gồm lý thuyết, dạng toán, ví dụ, bài tập vận dụng; bài tập có thể lấy từ ngân hàng và lưu snapshot. Giữ nguyên nguồn TeX, đáp án, lịch sử sửa đổi; bản dành cho học sinh phải ẩn đáp án/lời giải. Các danh mục chương/bài dựa trên bộ Kết nối tri thức và danh sách người dùng đã cung cấp; không tự thêm nội dung còn thiếu.

## Trạng thái đã hoàn thành

- Ngân hàng, tìm kiếm FTS5, chống câu trùng, hàng chờ nhập và gán phân loại từ cây CSDL.
- Danh mục chương/bài JSON: 14 hồ sơ môn/lớp, 641 node; migration có backup.
- Toolbar gọn cho nhập/ra đề; thư viện có cây, danh sách và preview; bấm cây quay về danh sách đúng phạm vi.
- Editor LaTeX, tìm/thay thế, thụt dòng, giao diện sáng/tối; jobs nền có hủy và tránh kết quả preview cũ ghi đè.
- Ra đề theo ma trận/thống kê, snapshot câu hỏi, xáo phương án giữ đúng đáp án; xuất TeX/PDF.
- Thiết kế bài giảng, tự lưu, revisions, lấy câu từ ngân hàng, preview và xuất gói tài nguyên.
- Preview dùng nguyên `docs/Class/MAPClass.cls` và `docs/Packages/ex_test.sty`. Khi chạy source đọc trực tiếp docs; build đồng bộ bản sao vào package. Preamble riêng trong Cài đặt vẫn được ưu tiên.
- Cache preview nhận biết thay đổi class/package. Gói bài giảng kèm class/package để biên dịch lại độc lập.

## Cài đặt và chạy trên máy Windows khác

Cần Git, Python **64-bit 3.12+** và TeX Live/pdfLaTeX cùng các package mà MAPClass khai báo. Môi trường đã kiểm tra: Python 3.14, PySide6 6.11.1, PyMuPDF 1.28.0, PyInstaller 6.21.0, TeX Live 2026.

```powershell
git clone https://github.com/letrieubavuong/MCPTest.git
cd MCPTest
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m pip install PyInstaller==6.21.0
.\scripts\run.ps1
```

Kiểm tra `pdflatex --version`. Trong Cài đặt, chọn đường dẫn pdfLaTeX nếu chưa có PATH; để trống **File preamble riêng** để dùng MAPClass/ex_test. Nếu PowerShell chặn script, dùng chính sách phù hợp cho phiên hiện tại hoặc chạy trực tiếp `.\.venv\Scripts\python.exe -m latex_question_studio`.

```powershell
.\scripts\test.ps1
.\scripts\build.ps1
.\.venv\Scripts\python.exe scripts/verify_ui_package.py
.\.venv\Scripts\python.exe scripts/package_release.py --dist-dir dist/0.5.2/LaTeXQuestionStudio --test-count 95
.\.venv\Scripts\python.exe scripts/verify_ui_package.py --zip release/LaTeXQuestionStudio-0.5.2-win64.zip
```

`--test-count` phải là số kiểm thử thực sự đạt trên máy build. EXE tạo tại `dist/0.5.2/LaTeXQuestionStudio/LaTeXQuestionStudio.exe`, ZIP tại `release/LaTeXQuestionStudio-0.5.2-win64.zip`. Giữ nguyên toàn bộ thư mục `_internal` khi chuyển bản chạy. `build.ps1` tải wheel bootloader khi chưa có và dừng nếu test/build/smoke lỗi. Báo cáo/screenshot lịch sử trong artifacts là tùy chọn khi đóng gói trên checkout mới.

Git chứa đầy đủ mã nguồn, tests, scripts, docs, examples, danh mục JSON và class/package. Thư mục `.venv`, `.runtime`, `dist`, `release`, `artifacts` là môi trường/kết quả sinh lại, không đưa vào Git. Ngân hàng cá nhân không đi theo source: dùng Backup/Restore trong ứng dụng để chuyển dữ liệu riêng nếu cần.

## Kiểm chứng tại mốc bàn giao

- **95/95 kiểm thử đạt**, 219,92 giây trên mã 0.5.2 trước cập nhật tài liệu bàn giao.
- PDF thật: trắc nghiệm, đúng/sai, đúng/sai bảng, trả lời ngắn, tự luận, TikZ và ảnh; kiểm tra bản học sinh không lộ lời giải.
- Gói TeX bài giảng biên dịch lại thành công.
- EXE và EXE giải nén ZIP: exit 0; integrity SQLite `ok`, schema 17, 641 node.
- Class/package trong bundle khớp byte-for-byte file docs; mã Compiler và xuất bài giảng trong build khớp source cuối cùng.
- Chưa thử trên Windows VM sạch. Cần xác minh trên máy mới.

## Việc tiếp theo cần ưu tiên

1. Chạy bộ test và nghiệm thu trên máy mới; kiểm tra thư viện, nhập/phân loại, ma trận đề, bài giảng bằng dữ liệu mẫu trước dữ liệu thật.
2. Xử lý launcher còn có thể hiện cửa sổ console: bản hiện tại dùng bootloader console x64 đã kiểm chứng. Bootloader windowed từng lỗi khởi động tại máy cũ; không đổi chỉ bằng cờ rồi bỏ qua smoke test.
3. Đồng bộ xuất **TeX đề thi độc lập** với profile MAPClass nếu người dùng yêu cầu: hiện TeX đề thi mặc định vẫn dùng article; preview/PDF dùng profile đã cấu hình.
4. Hoàn thiện đóng gói dependency cho **preamble riêng của bài giảng**: hiện chỉ gói tích hợp được hỗ trợ, custom profile sẽ báo lỗi khi xuất gói.
5. Tiếp tục nghiệm thu nghiệp vụ/UI theo các spec dưới đây; không coi mọi yêu cầu trong spec là đã hoàn thành chỉ vì có báo cáo phase.
6. Khi có bản build mới đã kiểm chứng, dọn build/ZIP cũ để tránh phình thư mục; giữ dữ liệu và môi trường chạy.

## Bản đồ mã nguồn và tài liệu

- `src/latex_question_studio/application/`: import, library/search, exams, lessons.
- `persistence/`: database/migrations/revisions/cache phân tích; `domain/data/`: danh mục môn học.
- `parsing/latex.py`: parser; `preview/compiler.py`: profile, biên dịch và cache PDF.
- `ui/main_window.py`: điều phối; `ui/pages`, `ui/panels`, `ui/components`, `ui/shell`, `ui/themes`: giao diện.
- [Kế hoạch nghiệp vụ](17_PRODUCT_REDESIGN_PLAN.md), [Thiết kế bài giảng](18_LESSON_AUTHORING_SPEC.md), [UI redesign](UI_REDESIGN_SPEC.md).
- [Ổn định kỹ thuật](CODEX_STABILIZATION_REPORT.md), [Sửa thư viện](UI_LIBRARY_CORRECTION.md), [Preview MAPClass](PREVIEW_MAPCLASS_REPORT.md), [Hướng dẫn dùng](USER_GUIDE.md).

## Telegram và bảo mật khi chuyển máy

`scripts/notify-telegram.ps1` giữ gửi text, hỗ trợ `-ImagePath`, `-Caption`, và `-AsDocument` để gửi ảnh nguyên bản. Cấu hình nằm ngoài repository tại `Join-Path $env:LOCALAPPDATA "CodexTelegram\config.json"`. Token Windows DPAPI phụ thuộc tài khoản/máy; cần tạo cấu hình mới tại máy đích, không copy token đã mã hóa rồi giả định giải mã được. Không giải mã DPAPI trực tiếp từ WSL/Linux. Không in token hoặc URL chứa token. Chỉ gửi ảnh đã kiểm tra không có mật khẩu/token/dữ liệu cá nhân; lỗi Telegram không được làm dừng phase.

Đã có quyền báo cáo tiến độ qua bot trong phiên hiện tại. Việc push lần này được người dùng yêu cầu rõ; các phiên sau cần theo phạm vi yêu cầu mới, không tự push chỉ dựa vào tài liệu bàn giao.
