# Báo cáo nghiệm thu ổn định kỹ thuật — 0.4.0

## 1. Trạng thái gốc và phạm vi

HEAD gốc: `ce9dbd6aeb3a55bd98f0c0db9230fa2ea94254b9`. Working tree sạch khi bắt đầu. HEAD giữ nguyên; chưa commit hoặc push. Thay đổi chỉ thuộc nhiệm vụ này, không ghi đè công việc chưa commit của người dùng. Không viết lại kiến trúc; không nâng dependency; không sửa SQLite thật trong LOCALAPPDATA.

Thực hiện audit → cache/statistics/matrix → catalog → parser/tích hợp → benchmark → UI regression → nghiệm thu. Các lỗi lộ nội dung học sinh được xử lý trước cải tiến hiệu năng. Kết quả thử nghiệm trong báo cáo là dữ liệu tổng hợp, không chứng nhận mọi ngân hàng thực tế.

## 2. Lỗi đã xác nhận và giải pháp

| Mức | Vấn đề | Kết quả |
|---|---|---|
| P0 | TeX học sinh còn True/shortans/loigiai/comment; ảnh chỉ trong lời giải vẫn được chép | Sanitize body bằng scanner trước export; chỉ copy ảnh được body sau sanitize tham chiếu. Source ngân hàng/teacher giữ nguyên; macro chưa chứng nhận bị từ chối thay vì đoán. |
| P1 | Thống kê get/parse từng câu mỗi lần | question_analysis hash/version; invalidation trigger khi đổi source; aggregate SQL theo mức độ và validity. Không thay authoritative source/revisions. |
| P1 | Tạo đề/thống kê đồng bộ trên UI | Worker có hủy, guard cho thống kê, toolbar hủy tạo đề. Matching, số lượng và seed được giữ. |
| P1 | Import đọc toàn source để so trùng, thiếu hủy trong vòng câu/commit | Index normalized hash, batch lookup, kiểm tra hủy theo câu và rollback transaction. Cache commit dùng lại phân tích stage khớp hash/version, có fallback cho pending cũ. |
| P1 | Nhiều macro đáp án ghi đè kết quả; verb* nhận sai delimiter | Diagnostic câu mơ hồ, không dùng để xáo; scanner bỏ qua literal verb* và câu giả trong macro definition. Không thay spans/source toán học. |
| P1 | Xóa review không hủy preview; toolbar vẫn gán khi commit | Cleanup trước deleteLater, hủy toàn bộ preview jobs, guard generation; disable shared actions khi ghi batch. |
| P1 | Review batch dựng tất cả ô trên UI | Phân trang 200 câu, ánh xạ row → index batch cho chọn/gán/preview; giữ gán cả danh sách. |
| P2 | Root menu/catalog hardcode; thiếu dữ liệu sách/version/order | JSON registry + SQLite profiles/order; menu gốc động. Legacy migrations 8–15 giữ nguyên và giữ các ID/tên đã dùng. |
| P2 | Index subtree/hash thiếu; không cảnh báo trùng source khác ID | Bổ sung indexes, WHERE chung; cảnh báo exact/near trong snapshot và UI, không thay lựa chọn giáo viên. |

Hồi quy cache mới được kiểm tra và chặn: đáp án cache của source vừa sửa không được dùng với revision/source đã pin trước đó. Nếu có race source, phân tích source pinned; cache hiện tại không bị ghi đè.

Không xác nhận lỗi mất DB ở baseline: transaction/revision/backup đã có. Không suy đoán NB/TH/VD/VDC từ ID TeX hoặc nội dung.

## 3. File thay đổi

- `docs/CODEX_STABILIZATION_REPORT.md`
- `docs/CODEX_TECHNICAL_AUDIT.md`
- `docs/CURRICULUM_CATALOG.md`
- `docs/PERFORMANCE_BENCHMARK.md`
- `docs/RELEASE_NOTES.md`
- `pyproject.toml`
- `scripts/benchmark_stabilization.py`
- `scripts/build.ps1`
- `scripts/capture_stabilization_preview.py`
- `scripts/check_latex_integration.py`
- `scripts/finalize_windows_build.py`
- `scripts/package_release.py`
- `src/latex_question_studio/application/exams.py`
- `src/latex_question_studio/application/importing.py`
- `src/latex_question_studio/application/library.py`
- `src/latex_question_studio/application/search.py`
- `src/latex_question_studio/domain/catalog.py`
- `src/latex_question_studio/domain/curriculum.py`
- `src/latex_question_studio/domain/data/curricula.json`
- `src/latex_question_studio/parsing/latex.py`
- `src/latex_question_studio/persistence/analysis.py`
- `src/latex_question_studio/persistence/database.py`
- `src/latex_question_studio/persistence/questions.py`
- `src/latex_question_studio/ui/exam_dialog.py`
- `src/latex_question_studio/ui/import_dialog.py`
- `src/latex_question_studio/ui/jobs.py`
- `src/latex_question_studio/ui/main_window.py`
- `tests/test_import_classification.py`
- `tests/test_navigation.py`
- `tests/test_stabilization.py`
- `tests/test_stabilization_ui.py`

Artifacts/bank tổng hợp/build/ZIP nằm trong các thư mục ignored; không đưa token/config/DB thật vào Git hoặc release.

## 4. Kiểm thử trước và sau

- Baseline: **61 passed trong 66,34s**.
- Bản mã cuối: **82 passed trong 103,15s**, gồm kiểm thử pdfLaTeX thật. Lượt này chạy cùng benchmark/build nên tổng thời gian pytest không dùng làm phép so tốc độ test suite.
- Phase 2 focused: 9 passed; phase 3: 24 passed; phase 4 parser/import/exam/lesson: 26 passed; hồi quy cache/import cuối: 26 passed. Kiểm thử UI cuối nằm trong 82 test, bao gồm ba kích thước yêu cầu 1024×768, 1366×768, 1920×1080.
- Migration fixture schema 15 → 17: so từng hàng tất cả bảng cũ, source/metadata/custom tên bài/taxonomy links/revisions, source_files/import_items/assets/question_assets, exam snapshots/history, lesson documents/revisions; ảnh/archive so bytes; backup có user_version 15; integrity_check=ok, foreign_key_check rỗng. Fixture schema 7 cũ và rollback migration lỗi vẫn đạt.
- Ma trận: phạm vi chồng lặp, thiếu nguồn hợp lệ, archived, chưa gán mức độ, source lỗi, không lặp ID, seed tái lập, đáp án MCQ sau xáo, cảnh báo trùng khác ID, cancellation không tạo đề dang dở.
- Import/export: giữ byte archive/raw/working source; repair/classification/revisions; hủy commit không ghi một phần; pending cũ có fallback; gán trang thứ hai đúng câu.
- Preview: compiler thật với math/TikZ/ảnh; thay bytes ảnh làm mất cache; cache hit; missing engine, timeout/cancel; old result sau đổi câu/hủy không đè UI hiện tại. Ảnh UI tổng hợp đã xem và gửi Telegram API ok=true (photo 98).
- PowerShell build.ps1 parse: PASS. Git diff --check: PASS.

## 5. Tích hợp ex_test/MAPClass

`scripts/check_latex_integration.py` dùng bản `docs/Class/MAPClass.cls` và `docs/Packages/ex_test.sty` nguyên gốc, không sửa gói hoặc nâng TeX. Bộ fixture có ex, choice, choiceTF, choiceTFt, shortans và loigiai. Cả article+ex_test và MAPClass đã tạo PDF giáo viên/học sinh thành công. Trích text PDF: TEACHERSECRET hiện ở teacher, không hiện ở student. Parser/math/TikZ/includegraphics/nested groups/comments/custom macro preservation có tests riêng.

Profile article cần amsmath, amssymb, fontawesome, colortbl, ex_test[loigiai], definecolor Mapcolor. Profile MAPClass dùng company=BookA4, pagesize=DethiA4, mausac=01, tuychon=GV1. Teacher dùng AtBeginDocument showansEX{ex}, student hideansEX{ex} và body đã sanitize. Có đủ dependency cho fixture đã chạy, missing_files rỗng; không tuyên bố mọi macro/chế độ/class đều tương thích. JSON kết quả trong verification/latex-integration.json của release.

## 6. Hiệu năng

Xem `PERFORMANCE_BENCHMARK.md` để có đủ 1k/10k/50k, phương pháp và số đo gốc. Điểm cải thiện chính là thống kê SQL có cache và UI không chờ parse toàn ngân hàng. Cold validation và ghi cache vẫn có chi phí một lần. Import commit và gần trùng chưa cải thiện đáng tin cậy, được ghi rõ trong bảng; không đánh dấu PASS hiệu năng cho hai thao tác này.

## 7. Windows build và phạm vi đã kiểm chứng

Build 0.4.0 Windows x64 bằng PyInstaller 6.21.0, có catalog JSON trong `_internal/latex_question_studio/domain/data/`. Kiểm tra bytecode PYZ của analysis/importing/exams/import_dialog/main_window khớp source hiện tại. Finalize bằng bootloader run.exe nguyên gốc từ wheel đã có; dùng UCRT hệ thống theo workaround đang tồn tại.

EXE `dist/0.4.0/LaTeXQuestionStudio/LaTeXQuestionStudio.exe` đã smoke-test exit=0 với thư mục DB tổng hợp mới: schema17, 641 taxonomy nodes, integrity_check=ok. Không ghi đè EXE phiên bản cũ đang chạy. Source tests/ảnh Qt kiểm tra UI/preview; smoke EXE xác nhận khởi tạo, không thay kiểm thử tương tác đầy đủ trên máy khác.

**BLOCKED: máy/VM Windows sạch chưa có trong môi trường.** Chưa chứng nhận vận hành trên mọi Windows. Launcher vẫn là console, vẫn có thể hiện CMD khi double-click; windowed bootloader là vấn đề môi trường còn tồn tại, không ghi nhận đã sửa trong đợt này.

## 8. Giới hạn còn lại

- Full-scan SequenceMatcher cho gần trùng và so cặp trong đề có thể chậm với source dài/nhiều câu; chỉ là gợi ý, không tự hợp nhất.
- Ghi hàng loạt tăng chi phí vì cache/index mới; worker/hủy giữ UI hoạt động nhưng chưa đạt cải thiện thời gian commit. Không đặt mục tiêu số liệu giả.
- Cache validity là cấu trúc scanner, không phải bằng chứng mọi source biên dịch. Macro tự định nghĩa ngoài vocabulary học sinh bị chặn; source/preamble tự viết cần giáo viên xem lại. Một số diagnostics kỹ thuật/log TeX giữ ngôn ngữ engine.
- Catalog thêm bằng API quản trị, chưa có màn hình chỉnh catalog; mở lại app để các cây đã khởi tạo nhận chương trình mới. Thống kê là snapshot lần refresh; dùng nút cập nhật sau sửa nguồn.
- Export TeX profile riêng không tự đóng gói mọi dependency tùy biến. Fixture tích hợp xác minh profile được nêu, không xác minh mọi bộ tài liệu của giáo viên.

## 9. Đánh giá bảo toàn dữ liệu

Không chạy migration trên database thật; mọi thử nghiệm dùng thư mục riêng. Schema 16/17 chỉ thêm cache/index/profile/order và trigger invalidation, không xóa/đổi source hoặc ID cũ. Cache có thể tái tạo và không thay revision history. Migration có backup trước, transaction và rollback; catalog installation có backup, validate ID/tree, không ghi đè tên đã tùy chỉnh. Bằng chứng synthetic tốt cho các luồng đã test; không thay thế backup/đối chiếu một ngân hàng thật tùy biến ngoài schema hỗ trợ.

## 10. Kiểm thử thủ công Windows

1. Giữ bản cũ và backup thư mục dữ liệu. Chạy EXE mới trước với `--data-dir` trỏ một thư mục thử riêng; không dùng DB thật cho phép thử đầu.
2. CSDL: mở cây cũ, search/phân trang, mở câu, sửa metadata, so source và revision. Kiểm tra cả cây Toán/KHTN/Vật lí và chương trình mới cài từ catalog.
3. Nhập file TeX có dấu/khoảng trắng, TikZ và ảnh đi kèm. Duyệt Preview/Source; gán bài/dạng/mức độ; đổi qua trang tiếp; gán đúng hàng, gán toàn danh sách; hủy phân tích và hủy ghi, kiểm tra pending vẫn còn.
4. Ra đề: cập nhật thống kê, chọn scope, tạo ma trận chồng lặp và thiếu nguồn; thử seed hai lần; xem cảnh báo trùng; hủy; kiểm tra đáp án sau xáo và lịch sử.
5. Xuất học sinh/giáo viên vào thư mục riêng cho từng đối tượng. Kiểm tra TeX học sinh không có True/loigiai/shortans/comment riêng và không có ảnh lời giải; teacher giữ nguyên lời giải. Không phân phối thư mục teacher kèm student.
6. Preview: đổi câu nhanh, hủy/đóng khi compile, đổi ảnh/profile rồi compile lại. Kiểm tra cache không hiển thị nhầm câu và toolbar có tooltip/overflow menu ở cửa sổ nhỏ.
7. Bài giảng: thêm câu bank, theory/method/example/exercise; pin revision; lưu/mở lại, xuất teacher/student theo policy. Cài đặt: thử engine sai/đúng và đổi theme.
8. Trên máy Windows sạch, cài TeX riêng nếu cần PDF và chạy lại phép thử. Đây là mục BLOCKED môi trường, cần xác nhận thủ công trước khi tuyên bố tương thích máy khác.

Lệnh tự kiểm thử: `./.runtime/python-embed/python.exe -m pytest -q`; tích hợp: `./.runtime/python-embed/python.exe scripts/check_latex_integration.py`; build: `./scripts/build.ps1 -PythonPath ./.runtime/python-embed/python.exe`. Các helper tạo dữ liệu tổng hợp riêng.
