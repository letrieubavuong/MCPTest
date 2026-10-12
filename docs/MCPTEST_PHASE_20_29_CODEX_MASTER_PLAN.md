# MCPTest — MASTER IMPLEMENTATION PLAN: PHASE 20–29

**Repository:** https://github.com/letrieubavuong/MCPTest  
**Baseline tham chiếu:** `main`, commit `bd2c6b81434c325d7b632a5d17498341d705a612` (11/10/2026); ứng dụng 0.5.2, SQLite schema 19.  
**Lưu ý:** Baseline chỉ để đối chiếu. Codex PHẢI đọc lại HEAD và working tree trước khi thực hiện; không được reset về commit này.  
**Nền tảng:** Python, PySide6, SQLite, PyMuPDF, pdfLaTeX, MAPClass.cls và ex_test.sty. Windows desktop là đích phát hành chính.

## A. Mục tiêu sản phẩm

Xây dựng công cụ ngân hàng câu hỏi LaTeX dễ sử dụng cho giáo viên Toán, KHTN, Vật lí. Trọng tâm là nhập câu hỏi từ các nguồn `.tex` có hình và macro phức tạp, quản lý trực quan, chỉnh sửa không mất cấu trúc, chọn câu tạo đề, soạn bài giảng nhiều file, xuất tài liệu portable và sao lưu an toàn.

**KHÔNG** viết lại dự án, không chuyển sang web, không tự thay đổi nghiệp vụ đã được kiểm chứng, không dùng mockup làm ảnh nền. Giao diện tiếng Việt, sử dụng widget PySide6 thật. Mockup là mục tiêu tham khảo, không phải đặc tả pixel-perfect hoặc bằng chứng tính năng đã có.

## B. Quy tắc triển khai chung

1. Đầu mỗi phase: `git status --short`, `git rev-parse HEAD`, đọc file liên quan và test hiện hữu. Không xóa/ghi đè thay đổi chưa commit; nếu xung đột, báo rõ và chọn phương án an toàn.
2. Tạo fixture/database tạm; không mở, migrate hoặc dọn ngân hàng thật của người dùng để thử nghiệm.
3. Phân biệt **đã có**, **lỗi xác nhận**, **thiếu tính năng**, **đề xuất**. Không tạo lại `AssetResolver`, `AssetStore`, `question_assets`, wizard, card grid, WYSIWYG hay file-model đã tồn tại.
4. Mọi migration phải có backup, idempotent, kiểm thử nâng từ schema 17/18/19 và rollback rõ ràng. Không thay đổi ID câu hỏi, taxonomy, revision, snapshot hoặc đường dẫn kho dữ liệu khi chưa cần.
5. Source TeX gốc là dữ liệu bất biến để đối chiếu. Biên dịch/export có thể tạo bản dẫn xuất, nhưng không âm thầm rewrite source. Không làm sai `\True`, `\choice`, `\choiceTF`, `\choiceTFt`, `\shortans`, `\loigiai`, TikZ, `\includegraphics`, `\input`.
6. Không tin tưởng TeX nguồn: giữ `-no-shell-escape`, kiểm soát đường dẫn/traversal/symlink, kích thước tệp, độ sâu dependency và timeout. Không tự chạy script hay shell command nhúng trong TeX.
7. Tác vụ dài phải chạy worker, hỗ trợ hủy, progress, stale-result protection, không khóa UI.
8. Không tạo nút giả, báo cáo PASS giả, benchmark giả. Test không chạy được phải ghi BLOCKED và lý do.
9. Mỗi phase: thêm test, chạy test liên quan, lưu báo cáo `docs/PHASE_XX_REPORT.md` gồm: baseline SHA, thay đổi, test, hình ảnh nếu có, rủi ro và bước tiếp theo.
10. Không tự commit/push, không xóa bản EXE/ZIP cũ và không phát hành cho đến khi đạt Phase 29 hoặc người dùng cho phép.

## C. Các cổng chất lượng bắt buộc

- **G0:** Full test suite trên HEAD mới nhất đạt trước khi bắt đầu sửa; nếu có test đỏ, phân loại lỗi nền và sửa hoặc ghi blocker.
- **G1:** Mỗi phase không làm hỏng test cũ và có test mới cho hành vi mới.
- **G2:** Không mất dữ liệu, tài nguyên, revision, đáp án hoặc lời giải; kiểm tra bằng snapshot/checksum.
- **G3:** Giao diện nghiệm thu trực quan với ảnh chụp từ ứng dụng thật ở 1366×768, 1600×900, 1920×1080; theme sáng/tối và DPI 125% nếu môi trường cho phép.
- **G4:** Xuất đề học sinh không rò đáp án/lời giải ở TeX, PDF và asset liên quan; đề giáo viên giữ đủ nội dung.
- **G5:** EXE/ZIP được build, smoke-test và đối chiếu với source hiện hành; thử trên Windows sạch nếu có môi trường.

---

## PHASE 20 — Baseline audit & hồi quy (P0)

**Kiểm tra:** `README.md`, `docs/HANDOVER.md`, `docs/STABILIZATION_20261011_REPORT.md`, `docs/ASSET_UX_IMPLEMENTATION_REPORT.md`, `tests/`, scripts build, dependency lock, cấu trúc `src/latex_question_studio/`.

**Công việc:**
- Xác định HEAD mới nhất và liệt kê thay đổi sau `bd2c6b8` nếu có.
- Chạy full pytest; phân loại pass/fail/skip, thời gian, môi trường, test flaky.
- Chạy smoke ứng dụng Qt, khởi tạo DB fixture, kiểm tra import, preview, exam, lesson.
- Xác minh 162 test của báo cáo trước có còn tương ứng với HEAD hay không; không sử dụng kết quả lịch sử làm bằng chứng của HEAD mới.
- Tạo ma trận chức năng: có sẵn/hoạt động/thiếu test/cần sửa, kèm đường dẫn file/hàm.
- Xác nhận trạng thái migration 17→18→19 và sao lưu trước nâng cấp.

**Đầu ra:** `docs/PHASE_20_BASELINE_AUDIT.md`, log pytest, ma trận chức năng.  
**Nghiệm thu:** baseline có thể tái lập; mọi lỗi nền có repro hoặc blocker rõ ràng.

## PHASE 21 — UI/UX theo luồng công việc giáo viên (P0)

**Kiểm tra:** `ui/main_window.py`, `ui/shell/application.py`, `ui/themes/design.py`, `ui/pages/library.py`, `ui/import_workflow.py`, `ui/import_dialog.py`, `ui/exam_dialog.py`, `ui/lesson_page.py`, `ui/dashboard.py`.

**Mục tiêu:** Một tác vụ = một luồng rõ ràng; hạn chế nút trùng, panel chồng chéo và chuyển màn hình không cần thiết.

**Công việc:**
- Audit các luồng: (1) nhập 100 câu/20 hình; (2) gán chương/bài/mức độ hàng loạt; (3) tìm câu và sửa; (4) chọn 20 câu tạo đề; (5) tạo bài giảng nhiều file.
- Tạo navigation map, wireframe chức năng và bảng primary/secondary actions cho từng màn hình.
- Chuẩn hóa application shell: activity bar, header, contextual toolbar, status bar, empty/loading/error states, tooltip và phím tắt.
- Tránh mở dialog nhiều lớp; chỉ dùng dialog cho quyết định nguy hiểm; inspector/panel hoặc wizard cho công việc dài.
- Lưu trạng thái splitter, filter, tab; có lệnh khôi phục bố cục mặc định.
- Đảm bảo bảng/card có cuộn đúng, không tràn/che ở 1366×768 và DPI cao; hỗ trợ bàn phím và focus.
- Đo số click và thời gian thao tác trước/sau trên fixture nhất quán; không bịa kết quả.

**Đầu ra:** `docs/PHASE_21_UI_UX_REPORT.md`, screenshot từng màn hình từ app thật, bảng before/after.  
**Nghiệm thu:** không có thao tác trùng lặp hoặc nút không hoạt động; 5 luồng chính hoàn tất không mất ngữ cảnh; UI không tràn tại kích thước nghiệm thu.

## PHASE 22 — Import TeX & vòng đời tài nguyên (P0)

**Kiểm tra:** `application/assets.py`, `application/importing.py`, `parsing/latex.py`, `persistence/database.py`, `ui/import_dialog.py`, `ui/import_workflow.py`, `preview/compiler.py`, `tests/test_assets.py`, `tests/test_asset_review_ui.py`.

**Công việc:**
- Lập bộ fixture TeX: `\includegraphics` có/không extension, `\graphicspath`, đường dẫn lồng, cùng tên khác nội dung, PDF/PNG/JPG, `\input`/`\include` lồng, TikZ rời, macro động, hình chỉ trong lời giải, thiếu ảnh, symlink, traversal, cycle.
- Kiểm tra resolver trả đúng source context, candidate paths, SHA-256, status READY/MISSING/AMBIGUOUS/NEEDS_REVIEW; không tự chọn ảnh khi mơ hồ.
- Wizard cho phép chọn lại ảnh, bổ sung thư mục tìm kiếm, preview trước nhập, bỏ qua câu lỗi và nhập câu hợp lệ.
- Xác nhận `AssetStore` copy nội bộ và reference mapping vẫn hoạt động sau khi đổi tên/di chuyển/xóa thư mục ảnh nguồn.
- Kiểm tra staging/commit/rollback/cleanup, tránh orphan do import hủy; không GC asset đang dùng trong question, exam snapshot, lesson snapshot.
- Tạo màn hình integrity report: missing, corrupt, shared, unlinked; GC mặc định dry-run, xóa phải xác nhận.
- Kiểm tra export ZIP portable trên thư mục giải nén mới; manifest checksum khớp và biên dịch được khi đủ dependency.

**Đầu ra:** `docs/PHASE_22_ASSET_IMPORT_REPORT.md`, bộ fixture có README.  
**Nghiệm thu:** import câu có hình rồi xóa nguồn gốc vẫn preview/export đúng; thiếu/ambiguous không bị đánh dấu READY; không mất asset khi GC; export portable không tham chiếu đường dẫn tuyệt đối.

## PHASE 23 — WYSIWYG ↔ LaTeX round-trip (P0)

**Kiểm tra:** `ui/wysiwyg.py`, `ui/editor.py`, `ui/lesson_page.py`, `application/lessons.py`, `preview/compiler.py`, `tests/test_wysiwyg*.py`.

**Công việc:**
- Thiết lập hợp đồng chuyển đổi: LaTeX gốc → mô hình trình bày → sửa trực quan → LaTeX xuất; phân biệt node hỗ trợ và opaque/raw TeX.
- Kiểm tra `$...$`, `\(...\)`, `\[...\]`, phân thức, căn, chỉ số, ma trận, môi trường toán nhiều dòng, ảnh, TikZ, `\choice`, `\True`, `\loigiai`, `listEX`, macro MAPClass/ex_test.
- Macro không hiểu phải giữ nguyên dưới dạng raw/opaque, không hiển thị như văn bản thuần gây lưu sai.
- Hỗ trợ undo/redo, autosave, dirty state, revisions; không tạo revision chỉ vì đổi theme hoặc preview.
- Cải thiện thao tác nhập công thức, dán LaTeX, sửa trực tiếp và preview mục hiện tại/toàn bài.
- So sánh round-trip bằng cấu trúc/semantic snapshot, không yêu cầu byte-for-byte với nội dung đã được người dùng chủ động sửa.
- Kiểm tra pdfLaTeX với MAPClass/ex_test thực khi dependency có sẵn.

**Đầu ra:** `docs/PHASE_23_WYSIWYG_ROUNDTRIP.md`, bảng trường hợp hỗ trợ/không hỗ trợ.  
**Nghiệm thu:** không mất đáp án, macro, TikZ, tài nguyên hoặc lời giải; round-trip không làm thay đổi các phần chưa được sửa; lỗi unsupported được cảnh báo rõ.

## PHASE 24 — Bài giảng nhiều file, revision & chốt xuất (P0)

**Kiểm tra:** `application/lessons.py`, `ui/lesson_page.py`, `persistence/database.py`, `tests/test_lesson_files.py`, `tests/test_lessons.py`.

**Công việc:**
- Hoàn thiện file navigator độc lập với outline: `theory.tex`, `dang-XX-*.tex`, `bai-tap-van-dung.tex`, `main.tex` (file ghép khi xuất).
- Mỗi file có trạng thái dirty/saved/locked/exported, số câu, thứ tự; chọn file chỉ hiển thị outline và editor tương ứng.
- Thêm/đổi tên/sắp xếp dạng toán an toàn; không đổi question ID hoặc pinned revision.
- Chèn câu từ ngân hàng có hiển thị preview và thông tin revision; khi câu gốc thay đổi, hiển thị cảnh báo và lựa chọn giữ snapshot hoặc cập nhật có kiểm soát.
- Chốt file bài tập và chỉ mục xuất; sửa sau chốt phải mở khóa có thông báo; không xuất âm thầm dữ liệu chưa chốt.
- Export các file `.tex` + `main.tex` với `\input`, ảnh, profile, manifest và PDF; mở trên thư mục mới và compile.
- Migration và mở tài liệu bài giảng cũ giữ nguyên nội dung/revision.

**Đầu ra:** `docs/PHASE_24_LESSON_FILES_REPORT.md`.  
**Nghiệm thu:** tạo bài giảng gồm lý thuyết, 3 dạng, ví dụ và vận dụng; lưu/đóng/mở lại, sửa, chốt, xuất và biên dịch độc lập thành công.

## PHASE 25 — Ngân hàng câu hỏi trực quan & thao tác hàng loạt (P1)

**Kiểm tra:** `ui/pages/library.py`, `ui/panels/question_preview.py`, `application/search.py`, `application/library.py`, `persistence/questions.py`.

**Công việc:**
- Card preview mặc định; list compact cho dữ liệu lớn; toggle không làm mất selection/filter/scroll.
- Thumbnail được cache và render lazy; không chạy pdfLaTeX cho toàn bộ trang khi mở.
- Lọc kết hợp môn/lớp/chương/bài/dạng/mức độ/loại câu/trạng thái tài nguyên; breadcrumb rõ.
- Multi-select: gán metadata, nhãn, thêm vào giỏ đề, archive/restore; có preview tác động và undo hoặc xác nhận cho hành động nguy hiểm.
- Hiển thị trạng thái asset, duplicate suggestion, last edited/revision; tìm theo nội dung/metadata.
- Khi câu có nhiều trang PDF, thumbnail chỉ trang cần thiết; preview chi tiết có điều hướng trang.

**Đầu ra:** `docs/PHASE_25_LIBRARY_UX_REPORT.md`.  
**Nghiệm thu:** duyệt 1.000 câu không treo UI; chọn và phân loại 100 câu đúng; không mất selection do refresh/đổi chế độ; thumbnail khớp câu.

## PHASE 26 — Ra đề, trộn mã đề & xuất an toàn (P1)

**Kiểm tra:** `application/exams.py`, `application/tex_exams.py`, `ui/exam_dialog.py`, `ui/tex_exam_page.py`, `preview/compiler.py`.

**Công việc:**
- Test ma trận chồng phạm vi, thiếu nguồn, câu lưu trữ, duplicate IDs/content, seed tái lập và thống kê NB/TH/VD/VDC.
- Test trộn câu/đáp án: `\True` không lệch đáp án; không xáo câu không đủ điều kiện parser; giữ phần, cấu trúc mẫu và asset.
- Student TeX/PDF/ZIP phải không lộ lời giải, đáp án, comment riêng tư và hình chỉ dùng trong lời giải; teacher output giữ đủ.
- Xem trước cấu hình đề và báo lỗi thiếu nguồn/tài nguyên trước export.
- Xuất portable: file TeX, asset, preamble/profile, manifest/checksum; test compile sau giải nén.
- Thử các bộ đề thật trên fixture copy, không dùng dữ liệu người dùng trực tiếp.

**Đầu ra:** `docs/PHASE_26_EXAM_EXPORT_REPORT.md`.  
**Nghiệm thu:** đáp án chính xác qua nhiều seed; không leak ở đề học sinh; ZIP độc lập thư mục gốc; có test regression cho mọi lỗi sửa.

## PHASE 27 — Performance & concurrency (P1)

**Kiểm tra:** `application/search.py`, `application/exams.py`, `application/assets.py`, `ui/pages/library.py`, `ui/jobs.py`, `preview/compiler.py`, SQLite indexes/FTS.

**Công việc:**
- Fixture 1k/10k/50k câu, tách benchmark parser/resolver khỏi benchmark end-to-end GUI/SQLite.
- Đo khởi động, tìm kiếm, lọc, cuộn card, preview, thống kê ma trận, import 1k và export đề.
- Profile N+1 queries, FTS, cache, số job chạy đồng thời, memory và độ trễ tương tác; chỉ tối ưu nơi có số liệu.
- Thêm debounce, pagination/virtualization, bounded preview workers, cancel/stale-generation và cache invalidation theo source+asset+profile hash.
- Kiểm thử đóng cửa sổ khi worker đang chạy, chuyển câu nhanh, import hủy, timeout pdfLaTeX.

**Đầu ra:** `docs/PHASE_27_PERFORMANCE_REPORT.md` gồm cấu hình máy, script, số đo trước/sau và giới hạn benchmark.  
**Nghiệm thu:** không treo UI, không hiển thị preview sai câu; các đường nóng cải thiện hoặc có lý do định lượng nếu giữ nguyên.

## PHASE 28 — Backup, restore, migration & chuyển máy (P1)

**Kiểm tra:** `application/library.py`, `persistence/database.py`, cấu hình data_dir, backup/restore, scripts phát hành.

**Công việc:**
- Backup toàn bộ DB, sources, assets, lesson exports, manifests, profiles cần thiết; kiểm tra checksum, không đưa cache không cần thiết vào backup.
- Restore vào data_dir trống và vào môi trường test có dữ liệu; có cảnh báo overwrite, backup trước restore, rollback khi lỗi.
- Kiểm thử migration schema 17/18/19 và mở dữ liệu cũ sau upgrade; không downgrade DB âm thầm.
- Tính năng chuyển kho dữ liệu: copy → verify → switch config → smoke → chỉ xóa bản cũ sau xác nhận.
- Thử mất điện/gián đoạn giả lập khi copy và restore; dữ liệu cũ vẫn còn.
- Không phụ thuộc đường dẫn tuyệt đối ổ D: hoặc thư mục nguồn TeX ban đầu.

**Đầu ra:** `docs/PHASE_28_DATA_PORTABILITY_REPORT.md`.  
**Nghiệm thu:** backup/restore trên thư mục khác, toàn bộ câu có hình và bài giảng vẫn preview/export; hash và liên kết hợp lệ.

## PHASE 29 — Release candidate Windows (P2)

**Kiểm tra:** `scripts/`, PyInstaller spec, assets icon, `README.md`, `docs/USER_GUIDE.md`, `docs/RELEASE_NOTES.md`.

**Công việc:**
- Chạy full pytest trên HEAD và tất cả smoke/integration trọng yếu; lập danh sách skipped/blocked.
- Build Windows GUI EXE `--windowed`, icon nhiều kích thước, bundle MAPClass/ex_test, PyMuPDF và dependency thực sự được sử dụng.
- Không xóa bản release cũ khi chưa kiểm tra bản mới; staging/verify/atomic replace; ZIP chỉ khi yêu cầu hoặc theo option build.
- Kiểm tra subsystem không bật CMD, mở app, DB schema, preview PDF, import ảnh, xuất đề, soạn bài giảng.
- Test clean Windows VM nếu có; nếu không ghi BLOCKED, không tuyên bố tương thích máy sạch.
- Cập nhật hướng dẫn cài, cách chuyển data_dir, import ảnh, sửa ảnh thiếu, WYSIWYG, backup/restore và troubleshooting.
- Tạo release checklist và báo cáo với commit SHA, version, hashes, test evidence, screenshot thật.

**Đầu ra:** `docs/PHASE_29_RELEASE_ACCEPTANCE.md`, release candidate trong staging (không tự phát hành).  
**Nghiệm thu:** G0–G5 đạt hoặc giới hạn được ghi rõ; không có lỗi P0 chưa xử lý; release chỉ khi người dùng đồng ý.

---

## D. Bộ kịch bản nghiệm thu end-to-end tối thiểu

1. Nhập 100 câu TeX có 20 hình, `\graphicspath`, một ảnh thiếu và hai ảnh cùng tên khác bytes → review → gán ảnh → commit → kiểm tra 100 câu.
2. Đổi tên/xóa thư mục nguồn sau nhập → preview từng câu và xuất đề portable vẫn đúng.
3. Tạo câu có TikZ, macro MAPClass/ex_test, lời giải và đáp án → chỉnh WYSIWYG một phần → source ngoài phần sửa không thay đổi; PDF vẫn đúng.
4. Chọn 20 câu theo ma trận → xuất đề học sinh và giáo viên → kiểm tra đáp án không rò vào student artifact.
5. Soạn bài giảng có lý thuyết + 3 dạng toán + ví dụ + bài tập vận dụng → chốt file → xuất `main.tex` và các file con → biên dịch thư mục độc lập.
6. Backup → chuyển data_dir sang thư mục khác → restore → xác minh hash, câu hỏi, bài giảng, ảnh và preview.
7. Tải ngân hàng 10.000 câu, lọc nhanh, đổi card/list, chọn 100 câu, chuyển preview liên tục → không freeze, không stale preview.
8. Đóng ứng dụng khi preview/import đang chạy → không crash, không hỏng database hoặc để lại trạng thái READY sai.

## E. Quy trình chạy Codex

**Prompt mở đầu cho Codex:**

> Đọc toàn bộ `MCPTEST_PHASE_20_29_CODEX_MASTER_PLAN.md`. Kiểm tra HEAD và working tree hiện tại; giữ nguyên mọi thay đổi chưa commit. Bắt đầu PHASE 20 để thiết lập baseline, chạy test thật và viết báo cáo. Sau đó thực hiện tuần tự PHASE 21–29, không viết lại kiến trúc đã có. Sau mỗi phase phải chạy test liên quan, kiểm tra hồi quy và tạo `docs/PHASE_XX_REPORT.md`. Ưu tiên P0; không tự commit/push, không xóa release cũ, không dùng dữ liệu người dùng thật để test. Nếu gặp rủi ro mất dữ liệu hoặc quyết định nghiệp vụ chưa chốt, dừng ở điểm đó và báo cáo rõ phương án.

**Khi giới hạn phiên Codex:** Chỉ hoàn tất phase hiện tại; cập nhật `docs/PHASE_PROGRESS.md` gồm trạng thái, test, blocker, HEAD và việc cần làm tiếp; không báo toàn bộ kế hoạch đã hoàn thành.

**Definition of Done:** Các phase P0 hoàn tất và có bằng chứng, không regressions, nguồn TeX và tài nguyên an toàn, UI dùng được theo kịch bản giáo viên, đề/bài giảng portable, dữ liệu có thể sao lưu và khôi phục, bản Windows có báo cáo phát hành đáng tin cậy.
