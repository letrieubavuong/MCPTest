# Bàn giao MCPTest / LaTeX Question Studio

Ngày bàn giao ban đầu: 09/10/2026; cập nhật phát hành 11/10/2026. Repository: https://github.com/letrieubavuong/MCPTest — nhánh `main`. Phiên bản ứng dụng: **0.5.2**; source và EXE đã nghiệm thu dùng schema SQLite **19** (bảng file nguồn bài giảng và chỉ mục bài tập). Xem `STABILIZATION_20261011_REPORT.md`: ba lượt 162/162 đạt, bản EXE/ZIP được đối chiếu trực tiếp trước khi thay bản cũ.

## Mục tiêu và nguyên tắc sản phẩm

Ứng dụng desktop Windows quản lý ngân hàng câu hỏi từ TeX, phân loại, ra đề theo ma trận và thiết kế bài giảng. Một cửa sổ chính: thanh điều hướng bên trái, nội dung chức năng bên phải. Cây CSDL Môn → Chương → Bài → Dạng là điểm vào chính, phải giữ rõ ràng và dễ dùng ở thư viện, nhập câu hỏi và ra đề. Không chuyển mỗi chức năng thành cửa sổ riêng.

Bài giảng gồm lý thuyết, dạng toán, ví dụ, bài tập vận dụng; bài tập có thể lấy từ ngân hàng và lưu snapshot. Giữ nguyên nguồn TeX, đáp án, lịch sử sửa đổi; bản dành cho học sinh phải ẩn đáp án/lời giải. Các danh mục chương/bài dựa trên bộ Kết nối tri thức và danh sách người dùng đã cung cấp; không tự thêm nội dung còn thiếu.

## Trạng thái đã hoàn thành

- Ngân hàng, tìm kiếm FTS5, chống câu trùng, hàng chờ nhập và gán phân loại từ cây CSDL.
- Danh mục chương/bài JSON: 14 hồ sơ môn/lớp, 641 node; migration có backup.
- Toolbar gọn cho nhập/ra đề; thư viện có cây, danh sách và preview; bấm cây quay về danh sách đúng phạm vi.
- Editor LaTeX, tìm/thay thế, thụt dòng, giao diện sáng/tối; jobs nền có hủy và tránh kết quả preview cũ ghi đè.
- Ra đề theo ma trận/thống kê, snapshot câu hỏi, xáo phương án giữ đúng đáp án; xuất TeX/PDF.
- Ra đề có thêm hình thức trộn mã đề từ file TeX: giữ mẫu gốc, đảo trong từng phần, preview và xuất TeX/PDF cùng bảng đáp án/đối chiếu. Câu cần nằm trực tiếp trong file; chưa mở rộng câu qua input/include. Chi tiết trong `USER_GUIDE.md`.
- Thiết kế bài giảng, tự lưu, revisions, lấy câu từ ngân hàng, preview và xuất gói tài nguyên.
- Preview dùng nguyên `docs/Class/MAPClass.cls` và `docs/Packages/ex_test.sty`. Khi chạy source đọc trực tiếp docs; build đồng bộ bản sao vào package. Preamble riêng trong Cài đặt vẫn được ưu tiên.
- Cache preview nhận biết thay đổi class/package. Gói bài giảng kèm class/package để biên dịch lại độc lập.

## Cài đặt và chạy trên máy Windows khác

Cần Git, Python **64-bit 3.12+** và TeX Live/pdfLaTeX cùng các package mà MAPClass khai báo. Môi trường hiện tại đã kiểm tra trên máy này: Python 3.14.6, PySide6 6.11.2, PyMuPDF 1.28.0, PyInstaller 6.22.3, pytest 9.1.1, pytest-qt 4.5.0 và TeX Live 2026. Các báo cáo phase cũ giữ phiên bản công cụ tại thời điểm thực hiện.

```powershell
git clone https://github.com/letrieubavuong/MCPTest.git
cd MCPTest
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e ".[test,build]"
.\scripts\run.ps1
```

Kiểm tra `pdflatex --version`. Trong Cài đặt, chọn đường dẫn pdfLaTeX nếu chưa có PATH; để trống **File preamble riêng** để dùng MAPClass/ex_test. Nếu PowerShell chặn script, dùng chính sách phù hợp cho phiên hiện tại hoặc chạy trực tiếp `.\.venv\Scripts\python.exe -m latex_question_studio`.

```powershell
.\scripts\test.ps1
.\scripts\build.ps1
.\scripts\clean-builds.ps1 -DryRun
```

`--test-count` phải là số kiểm thử thực sự đạt trên máy build. EXE tạo tại `dist/0.5.2/LaTeXQuestionStudio/LaTeXQuestionStudio.exe`, ZIP tại `release/LaTeXQuestionStudio-0.5.2-win64.zip`; script đọc phiên bản từ `pyproject.toml`. Giữ nguyên toàn bộ thư mục `_internal` khi chuyển bản chạy. `build.ps1` dùng `--windowed` và bootloader GUI PyInstaller đang cài, đóng gói đầy đủ PyMuPDF và dừng nếu test/build/smoke lỗi; không tải wheel cũ hoặc áp dụng bản sửa launcher/UCRT của máy trước. Kiểm tra subsystem GUI (2), chạy smoke không dùng cờ che console; script đóng gói từ chối EXE console. `finalize_windows_build.py` chỉ còn là công cụ sửa launcher thủ công khi có lỗi đã xác minh, cũng dùng bootloader GUI đang cài. Báo cáo/screenshot lịch sử trong artifacts là tùy chọn khi đóng gói trên checkout mới.

Build mặc định chỉ tạo icon, kiểm thử và dựng EXE trong staging; không tự tạo ZIP. Khi người dùng yêu cầu gói phát hành, dùng `scripts/build.ps1 -PackageRelease`; cả EXE và ZIP khi đó đều phải qua smoke trước khi thay bản. Sau khi đạt, tự xóa bản cũ và các thư mục build-test được nhận diện trong `.runtime`. Đóng ứng dụng trước bước thay EXE. Xem `APP_ICON_BUILD_RETENTION_REPORT.md`; `scripts/clean-builds.ps1 -DryRun` xem trước danh sách dọn.

Lượt kiểm thử icon/dọn build cuối: **156/156 đạt**, 222,94 giây, gồm đổi tên thư mục chỉ đọc/rollback và kiểm thử phản hồi UI ổn định. `build.ps1` tự lấy số test thực tế từ JUnit XML để ghi manifest, không cần gọi lại bước đóng gói thủ công sau khi build.

Đã thay EXE/ZIP có icon và dọn 132 mục build/tạm, tổng 6.116.444.732 bytes. Chỉ còn phiên bản 0.5.2 và ZIP/checksum hiện hành. Xem `APP_ICON_BUILD_RETENTION_REPORT.md`, `artifacts/build-current/cleanup.json` và `artifacts/app-icon/retention.json`.

Dashboard được polish và đóng gói trong lượt mới: **157/157 test đạt**, Dashboard focused/UI **13/13**, responsive 1024/1366/1600 px sáng/tối, ảnh bundle thật ở `artifacts/dashboard/bundle-dashboard.png`. EXE hash `3e99d7dd8211c598e048c573dccbbf32448a84a0aadc0c33839ef74d8408a3b7`; hash ZIP nằm trong file `.zip.sha256`.

Git chứa đầy đủ mã nguồn, tests, scripts, docs, examples, danh mục JSON và class/package. Thư mục `.venv`, `.runtime`, `dist`, `release`, `artifacts` là môi trường/kết quả sinh lại, không đưa vào Git. Ngân hàng cá nhân không đi theo source: dùng Backup/Restore trong ứng dụng để chuyển dữ liệu riêng nếu cần.

## Kiểm chứng tại mốc bàn giao

- **95/95 kiểm thử đạt**, 219,92 giây trên mã 0.5.2 trước cập nhật tài liệu bàn giao (mốc lịch sử).
- PDF thật: trắc nghiệm, đúng/sai, đúng/sai bảng, trả lời ngắn, tự luận, TikZ và ảnh; kiểm tra bản học sinh không lộ lời giải.
- Gói TeX bài giảng biên dịch lại thành công.
- EXE và EXE giải nén ZIP: exit 0; integrity SQLite `ok`, schema 17, 641 node (mốc lịch sử trước migration tài nguyên).
- Class/package trong bundle khớp byte-for-byte file docs; mã Compiler và xuất bài giảng trong build khớp source cuối cùng.
- Chưa thử trên Windows VM sạch. Cần xác minh trên máy mới.

Kiểm chứng lại trên máy hiện tại với bộ công cụ cập nhật ngày 09/10/2026: **95/95 kiểm thử đạt**, 107,23 giây (mốc trước asset phases). `scripts/build.ps1` hoàn tất mà không tải dependency; EXE khởi động exit 0, integrity SQLite `ok`, schema 17, 641 node; 13 module UI trong bundle khớp mã nguồn.

Sau bổ sung trộn mã đề từ file TeX: **107/107 kiểm thử đạt**, 167,31 giây (mốc trước asset phases); UI sáng/tối đã xem ở 1366×768 và 1024×768. Báo cáo/ảnh trong `artifacts/tex-exams/`.

Sau các phase bảo toàn tài nguyên và UX: **118/118 kiểm thử đạt**, 109,89 giây ở lượt build cuối; schema SQLite **18**; benchmark 1k/10k/50k và báo cáo nghiệm thu ở `ASSET_UX_IMPLEMENTATION_REPORT.md`. Build nghiệm thu hiện tại đã hoàn tất: EXE exit 0, integrity `ok`, schema 18, 641 node; ZIP `release/LaTeXQuestionStudio-0.5.2-win64.zip` đã verify, SHA-256 `7e597d8699ac3e7817106ed4967e644cdcec1ad48cd898118bbb1d9f2521234d`, không chứa database người dùng hoặc config bí mật. Máy Windows VM sạch vẫn chưa có.

Dashboard trang chủ đã bổ sung sau đó; xem `DASHBOARD_IMPLEMENTATION_REPORT.md`. Lượt build cuối có **119/119 test**, 109,84 giây; EXE smoke schema 18/integrity `ok`, ZIP SHA-256 `6e12977a29d1918f4f628e0495cff962e29761729b77697527c74e8757f76518`, 47 module bundle khớp source.

## Việc tiếp theo cần ưu tiên

Cập nhật WYSIWYG ngày 10/10/2026: **143/143 test đạt** trong 249,82 giây. Bài giảng mặc định có editor trực quan đồng bộ LaTeX và render công thức nền; source/revision/schema giữ cùng mô hình hiện tại. EXE đã smoke và kiểm tra trực quan với dữ liệu mẫu; 50 module khớp source, schema 18/integrity `ok`. Xem `WYSIWYG_IMPLEMENTATION_REPORT.md` và `artifacts/wysiwyg/`.

Sửa lỗi nhập công thức cùng ngày: **150/150 test đạt** trong 267,76 giây. Công thức/lệnh định dạng nhập hoặc dán không còn bị in thành chữ; có khôi phục nội dung đã escape với undo/revision. Preview mặc định chỉ mục đang soạn, vẫn chọn được toàn bài. Bằng chứng riêng ở `artifacts/formula-input-fix/`; chi tiết build/ZIP trong `WYSIWYG_IMPLEMENTATION_REPORT.md`.

Build Windows GUI cùng ngày: **150/150 test đạt** trong 181,98 giây. EXE mới không mở cửa sổ CMD; subsystem 2, smoke bình thường không che console, PDF công thức render từ cache trống. Báo cáo và ảnh ở `WINDOWED_BUILD_REPORT.md`, `artifacts/windowed-build/`. Bản console trước là lịch sử, không dùng khi phát hành.

1. Chạy bộ test và nghiệm thu trên máy mới; kiểm tra thư viện, nhập/phân loại, ma trận đề, bài giảng bằng dữ liệu mẫu trước dữ liệu thật.
2. Khi build trên máy mới, giữ chế độ Windows GUI và chạy smoke bản EXE/ZIP thật. Console đã được sửa trong bản build hiện tại; xem `WINDOWED_BUILD_REPORT.md`. Không dùng cờ che console trong smoke vì sẽ che lỗi cấu hình launcher.
3. Đồng bộ xuất **TeX đề thi độc lập** với profile MAPClass nếu người dùng yêu cầu: hiện TeX đề thi mặc định vẫn dùng article; preview/PDF dùng profile đã cấu hình.
4. Hoàn thiện đóng gói dependency cho **preamble riêng của bài giảng**: hiện chỉ gói tích hợp được hỗ trợ, custom profile sẽ báo lỗi khi xuất gói.
5. Tiếp tục nghiệm thu nghiệp vụ/UI theo các spec dưới đây; không coi mọi yêu cầu trong spec là đã hoàn thành chỉ vì có báo cáo phase.
6. Khi có bản build mới đã kiểm chứng, dọn build/ZIP cũ để tránh phình thư mục; giữ dữ liệu và môi trường chạy.

## Bản đồ mã nguồn và tài liệu

- `src/latex_question_studio/application/`: import, library/search, exams, lessons.
- `persistence/`: database/migrations/revisions/cache phân tích; `domain/data/`: danh mục môn học.
- `parsing/latex.py`: parser; `preview/compiler.py`: profile, biên dịch và cache PDF.
- `application/tex_exams.py`, `ui/tex_exam_page.py`: đọc file TeX, ghim tài nguyên, trộn mã đề và xuất bộ mã đề.
- `ui/main_window.py`: điều phối; `ui/pages`, `ui/panels`, `ui/components`, `ui/shell`, `ui/themes`: giao diện.
- [Kế hoạch nghiệp vụ](17_PRODUCT_REDESIGN_PLAN.md), [Thiết kế bài giảng](18_LESSON_AUTHORING_SPEC.md), [UI redesign](UI_REDESIGN_SPEC.md).
- [Ổn định kỹ thuật](CODEX_STABILIZATION_REPORT.md), [Sửa thư viện](UI_LIBRARY_CORRECTION.md), [Preview MAPClass](PREVIEW_MAPCLASS_REPORT.md), [Hướng dẫn dùng](USER_GUIDE.md).

## Telegram và bảo mật khi chuyển máy

`scripts/notify-telegram.ps1` giữ gửi text, hỗ trợ `-ImagePath`, `-Caption`, và `-AsDocument` để gửi ảnh nguyên bản. Cấu hình nằm ngoài repository tại `Join-Path $env:LOCALAPPDATA "CodexTelegram\config.json"`. Token Windows DPAPI phụ thuộc tài khoản/máy; cần tạo cấu hình mới tại máy đích, không copy token đã mã hóa rồi giả định giải mã được. Không giải mã DPAPI trực tiếp từ WSL/Linux. Không in token hoặc URL chứa token. Chỉ gửi ảnh đã kiểm tra không có mật khẩu/token/dữ liệu cá nhân; lỗi Telegram không được làm dừng phase.

Đã có quyền báo cáo tiến độ qua bot trong phiên hiện tại. Việc push lần này được người dùng yêu cầu rõ; các phiên sau cần theo phạm vi yêu cầu mới, không tự push chỉ dựa vào tài liệu bàn giao.
