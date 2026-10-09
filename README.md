Bản 0.2.4: thêm CSDL → KHTN 8 (46 bài, Bài 1 trực tiếp dưới môn và 8 chương) và TOÁN 8 (10 chương, 39 bài) theo danh sách người dùng. Tự điền môn/lớp 8/chương/bài; schema 12 nâng cấp có backup.

Bản 0.2.3: thêm CSDL → TOÁN 7 (Kết nối tri thức), 10 chương và 37 bài theo danh sách người dùng. Tự điền môn Toán, lớp 7 và chương/bài; schema 11 nâng cấp có backup.

Bản 0.2.2: thêm CSDL → KHTN 7, 10 chương và 41 bài (Bài 2–42) theo danh sách người dùng. Tự điền môn Khoa học tự nhiên, lớp 7, chương/bài; schema 10 nâng cấp có backup.

CSDL → TOÁN 6: 9 chương, 43 bài và 2 mục luyện tập chung theo danh sách người dùng. Chọn chương/bài để lọc ngân hàng; tạo câu tại mục đã chọn tự điền môn Toán, lớp 6 và chương/bài. Database nâng cấp lên schema 9 có backup trước migration.

Bản 0.2.1: menu **CSDL → KHTN 6 → Chương → Bài**, đủ 10 chương và 55 bài. Chọn mục để lọc ngân hàng; chọn phân loại bài sẽ đồng bộ môn/khối/chương/bài. Gói mới `release/LaTeXQuestionStudio-0.2.1-win64.zip`. [Báo cáo KHTN 6](docs/20_KHTN6_CURRICULUM_REPORT.md).

Bản mới: `release/LaTeXQuestionStudio-0.2.0-win64.zip`. Có trang Bài giảng với lý thuyết/dạng toán/ví dụ/bài tập từ ngân hàng, tự lưu/revisions, preview và xuất TeX/PDF. [Báo cáo triển khai](docs/19_LESSON_IMPLEMENTATION_REPORT.md). Các gói 0.1.x bên dưới là lịch sử.

# LaTeX Question Studio 0.2.0

Sản phẩm desktop Windows: nhập LaTeX có review/hàng chờ, thư viện/phân loại/nhãn/revisions, editor tab, pdfLaTeX/TikZ/ảnh/cache preview, FTS5/dedup, tạo đề ma trận/xáo phương án và xuất TeX/PDF/đáp án/lời giải, backup/restore.

Mở `dist/LaTeXQuestionStudio/LaTeXQuestionStudio.exe` hoặc giải nén gói phát hành rồi mở EXE. Giữ nguyên _internal; không cần Python. Preview/PDF cần TeX distribution bên ngoài. [Hướng dẫn](docs/USER_GUIDE.md), [Khắc phục lỗi](docs/TROUBLESHOOTING.md), [Benchmark](artifacts/phase08_benchmark.json).

## Phát triển

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\scripts\run.ps1
.\scripts\test.ps1
.\scripts\build.ps1
```

Python 3.12+, đã kiểm thử Python 3.14.6/PySide6 6.11.1/PyMuPDF 1.28.0. Build cần PyInstaller 6.21.0 (`python -m pip install pyinstaller==6.21.0`). Không tự chuyển dữ liệu cũ, không suy diễn mapping nhận thức. Profile article tích hợp đã compile test; MAPClass/ex_test thiếu dependency nên chưa chứng nhận tương thích. Không commit/push.

Bản 0.1.0 dùng launcher console x64; có thể xuất hiện thêm cửa sổ console. Đã kiểm tra EXE sau giải nén ZIP trên máy hiện tại, PATH không có Python; chưa kiểm thử trên VM Windows sạch. Xem [biên bản bàn giao](docs/15_PHASE09_REPORT.md).

Bản layout 0.1.1: menu drawer bên trái; Xem CSDL, Nhập câu hỏi, Ra đề thi và Cài đặt tải ở bên phải trong cùng cửa sổ. Gói mới: `release/LaTeXQuestionStudio-0.1.1-win64.zip`. [Chi tiết sửa layout](docs/16_LAYOUT_CORRECTION.md).
