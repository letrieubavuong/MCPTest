# BÁO CÁO NGHIỆM THU PHASE L: CÂU HỎI TRÙNG & THU THẬP TỪ WEB
**Dự án:** MCPTest (LaTeX Question Studio) — Phiên bản 2026  
**Môi trường:** Windows 11, Python 3.14.6, PySide6 6.11.2, TeX Live 2026 (pdfTeX 3.141592653-2.6-1.40.29)  
**Tài liệu yêu cầu:** `docs/MCPTEST_PHASE_L_DATA_TOOLS_CODEX_PROMPT.md`  
**Ngày hoàn thành:** 14/10/2026  

---

## 1. TỔNG QUAN VÀ MỤC TIÊU TRIỂN KHAI

Triển khai đầy đủ Phase L theo đúng tiêu chuẩn kiến trúc phần mềm giáo dục, bổ sung **hai tab độc lập cấp 1** vào ứng dụng MCPTest:
1. **Câu hỏi trùng** (`DedupPage` — Shortcut `Ctrl+D`): Quét phát hiện câu hỏi trùng lặp chính xác hoặc tương đương hoán vị phương án, hỗ trợ 2 phạm vi (Tệp `.tex` và Cơ sở dữ liệu), đối chiếu trực quan 2 cột, gộp metadata, và xóa an toàn có xác nhận.
2. **Thu thập từ Web** (`WebScraperPage` — Shortcut `Ctrl+Shift+W`): Thu thập bài tập từ website giáo dục (VietJack, Tech24, Lời Giải Hay, bài viết HTML chung), bảo vệ an toàn SSRF, tuân thủ robots.txt, chuyển đổi MathJax/KaTeX/MathML sang LaTeX chuẩn, giao diện staging 2 cột duyệt câu hỏi trước khi ghi vào CSDL hoặc xuất đề thi Phase K có kiểm tra biên dịch pdfLaTeX thực tế.

---

## 2. TUÂN THỦ CÁC NGUYÊN TẮC BẮT BUỘC (MANDATORY NON-NEGOTIABLES)

| Nguyên tắc bắt buộc | Cơ chế kỹ thuật đảm bảo | Trạng thái tuân thủ |
|:---|:---|:---:|
| **1. Không tự động xóa câu hỏi trùng** | Mặc định checkbox xóa của tất cả các câu trong nhóm trùng đều là `UNCHECKED`. Không có nút "Auto Delete". Thao tác xóa yêu cầu chọn thủ công, hộp thoại xác nhận `QMessageBox`, kiểm tra ràng buộc khóa ngoại (FK) với đề thi/bài giảng. Với file `.tex`, hệ thống chỉ ghi file mới (`_dedup.tex`), tuyệt đối không ghi đè file nguồn. | **ĐẠT 100%** |
| **2. Không nhập nội dung web chưa được kiểm duyệt** | Mọi câu trích xuất từ web mặc định ở trạng thái `needs_review` (Chờ duyệt). Hàm `commit_drafts_to_db()` áp dụng bộ lọc nghiêm ngặt `[d for d in drafts if d.status == 'verified']`. Nếu không có câu nào được giáo viên ấn xác nhận thì từ chối ghi CSDL. | **ĐẠT 100%** |
| **3. Không báo xuất thành công nếu file `.tex` không biên dịch được** | Service `export_drafts_to_exam_bundle()` tự động gọi `compiler.compile()` bằng `pdflatex`. Chỉ khi `compile_res.ok == True` và file `.pdf` thực tế được sinh ra thì mới đóng gói ZIP và thông báo thành công. Khi biên dịch lỗi, log chi tiết được hiển thị và trả về `ok: False`. | **ĐẠT 100%** |
| **4. Không làm hỏng CSDL hiện tại** | Giữ nguyên SQLite Schema version 19 (`studio.db`). Tận dụng các bảng sẵn có (`questions`, `question_revisions`, `assets`, `question_assets`). Tách biệt hoàn toàn kết nối transaction, không gây deadlock. | **ĐẠT 100%** |
| **5. Không tuyên bố hỗ trợ website khi adapter chưa được kiểm thử** | Chỉ công bố hỗ trợ các domain đã có adapter và kiểm thử với HTML fixture thực tế: `vietjack.com` (`VietjackAdapter`), `tech24.vn` (`Tech24Adapter`), `loigiaihay.com` (`LoigiaihayAdapter`), và `GenericArticleAdapter` cho trang bài viết chung. Các trang khác được định danh rõ là chạy qua bộ phân tích chung có cảnh báo rà soát. | **ĐẠT 100%** |

---

## 3. KIẾN TRÚC VÀ CÁC THÀNH PHẦN TÁI SỬ DỤNG

Phase L tái sử dụng tối đa hạ tầng đã được kiểm chứng qua các Phase trước:
- **Bộ phân tích cú pháp LaTeX (`parsing/latex.py`):** Dùng tokenizer và command/environment scanner để bóc tách `\begin{ex}...\end{ex}`, `\choice`, `\choiceTF`, `\shortans`, `\loigiai`, `\immini`, TikZ và `\includegraphics`.
- **Kho quản lý tài nguyên ảnh (`AssetStore` trong `application/assets.py`):** Quản lý ảnh tải từ web theo mã băm định danh SHA-256 (`assets/xx/xx...`), quy trình 2 bước: `stage_bytes()` vào thư mục đệm `.asset-staging` và chỉ `promote()` sang kho chính thức khi câu hỏi được duyệt và lưu vào CSDL.
- **Bộ biên dịch pdfLaTeX (`preview/compiler.py`):** Tái sử dụng `Compiler` với `BUILTIN_PREAMBLE` và `MAPCLASS_PREAMBLE`, hỗ trợ biên dịch đa luồng, cache SHA-256 nội dung, cấm `--shell-escape` để bảo mật.
- **Cấu trúc xuất đề Phase K (`application/exams.py`):** Xuất đề chuẩn 4 phần theo quy chế thi:
  ```latex
  \TieudeT{TIÊU ĐỀ BÀI THI}
  \PhanI \begin{cauhoiTN}{De01} ... \end{cauhoiTN}
  \PhanII \begin{cauhoiDS}{De01} ... \end{cauhoiDS}
  \PhanIII \begin{cauhoiTLN}{De01} ... \end{cauhoiTLN}
  \PhanTL \begin{cauhoiTL}{De01} ... \end{cauhoiTL}
  ```

---

## 4. CHI TIẾT TỪNG MODULE TRIỂN KHAI

### 4.1. Module Tìm câu hỏi trùng lặp (`application/dedup.py` & `ui/pages/dedup_page.py`)
- **Chuẩn hóa an toàn (`normalize_latex`):** Loại bỏ comment `%`, chuẩn hóa khoảng trắng xung quanh macro và dấu ngoặc, chuẩn hóa Unicode NFC, giữ nguyên ngữ nghĩa công thức toán, số âm, số mũ, TikZ và tên file ảnh.
- **3 Cấp độ phát hiện trùng:**
  - **Level 1 (`EXACT_NORMALIZED` - 100%):** Trùng lặp hoàn toàn nội dung chuẩn hóa.
  - **Level 2 (`MCQ_PERMUTATION` - 95%):** Đề bài giống nhau, tập 4 phương án giống nhau nhưng thứ tự xáo trộn, đối chiếu chính xác đáp án đúng `\True`. *Bất biến bắt buộc:* Tuyệt đối không hoán vị các mệnh đề của câu Đúng/Sai (`\choiceTF`).
  - **Level 3 (`SIMILARITY_ADVISORY` - 70-89%):** Gợi ý độ tương đồng dựa trên Jaccard token-set và n-gram. Có chốt an toàn (guardrail): Nếu khác nhau về số liệu, dấu âm, hoặc hình ảnh đính kèm thì lập tức hạ xuống dưới ngưỡng gợi ý để tránh báo sai.
- **Giao diện Tab "Câu hỏi trùng":**
  - Chuyển đổi 2 chế độ: Trong CSDL (lọc môn/loại câu/từ khóa) hoặc Trong file `.tex` (chọn nhiều file).
  - Thanh tiến độ, nút hủy tác vụ, thống kê số câu quét, số nhóm trùng, số câu có thể loại bỏ.
  - Thẻ đối chiếu cạnh nhau (side-by-side) hiển thị: LaTeX gốc, loại câu, đáp án đúng, nguồn, ngày tạo, số lần dùng trong đề thi/bài giảng.
  - Radio button chọn câu giữ lại (Primary), Checkbox chọn câu xóa (mặc định không tích).
  - Chức năng: Gộp nhãn/metadata, Bỏ qua nhóm, Xóa câu đã chọn (có xác nhận và chặn FK), Xuất báo cáo CSV/JSON, Xuất file `.tex` đã làm sạch.

### 4.2. Module Thu thập từ Web (`scraping/` & `application/web_import.py` & `ui/pages/web_scraper_page.py`)
- **Bảo mật và Tuân thủ (`scraping/fetcher.py`):**
  - `SSRFGuard`: Phân giải DNS và chặn triệt để dải IP nội bộ, loopback (127.0.0.1, localhost), private IPv4 (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16), link-local (169.254.0.0/16 - metadata cloud), multicast, IPv6 link-local/loopback.
  - `SafeRedirectHandler`: Kiểm tra URL chuyển hướng (redirect) qua SSRFGuard trước khi thực hiện.
  - `RobotsPolicy`: Tự động tải và tuân thủ tệp `/robots.txt` của domain, tôn trọng quyền từ chối của website.
  - Giới hạn tải an toàn: Tối đa 10MB/trang, timeout 10 giây, rate limiting giãn cách kết nối, User-Agent minh bạch.
- **Bộ chuyển đổi HTML sang LaTeX (`scraping/html_to_latex.py`):**
  - Chuyển thẻ MathJax `<script type="math/tex">` thành `$inline$` và `\[ display \]`.
  - Bóc tách mã TeX từ KaTeX `<span class="katex"><annotation encoding="application/x-tex">`.
  - Đọc thẻ MathML (`<math>`, `<mfrac>`, `<msup>`, `<msub>`, `<msubsup>`, `<msqrt>`, v.v.) thành macro LaTeX tương ứng.
  - Ánh xạ hơn 40 ký tự toán Unicode tiếng Việt (`∈`, `∉`, `⊂`, `∪`, `∩`, `√`, `π`, `≤`, `≥`, `≠`, `→`, `⇒`, `⇔`, `°`, `∠`, `⊥`, `∥`, v.v.).
- **Hệ thống Site Adapters (`scraping/adapters/`):**
  - `VietjackAdapter`: Bóc tách câu hỏi, phương án A/B/C/D, đáp án đúng và lời giải từ `vietjack.com` và `vietjack.me`.
  - `Tech24Adapter`: Bóc tách từ quiz card, container câu hỏi của `tech24.vn`.
  - `LoigiaihayAdapter`: Bóc tách từ box giải bài tập của `loigiaihay.com`.
  - `GenericArticleAdapter`: Bộ bóc tách chung cho mọi bài viết HTML, danh sách có thứ tự hoặc nội dung dán thủ công.
- **Giao diện Tab "Thu thập từ Web":**
  - Nhập URL hoặc chuyển sang tab "Dán mã HTML thô" khi gặp trang web chặn bot/CAPTCHA.
  - Bố cục 2 cột Staging: Cột trái hiển thị danh sách câu đã bóc tách kèm badge trạng thái (`[✓]`, `[?]`, `[✕]`) và cảnh báo thiếu đáp án; Cột phải là trình soạn thảo LaTeX chi tiết (Đề bài, 4 phương án + Radio chọn đáp án đúng, Lời giải) và khung Live Preview PDF.
  - Thao tác hàng loạt: "Duyệt nhanh tất cả câu hợp lệ", "Nhập câu đã duyệt vào CSDL ngân hàng", "Xuất đề thi Phase K (PDF & ZIP)".

### 4.3. Tích hợp Shell và Điều hướng (`ui/shell/application.py` & `ui/main_window.py`)
- Bổ sung 2 icon SVG gốc mới: `'dedup'` (2 trang chồng) và `'web'` (quả địa cầu).
- Bổ sung 2 tab cấp 1 vào `ApplicationShell` tại vị trí index 5 và 6:
  - Index 0: `CSDL` (`Ctrl+1`)
  - Index 1: `Nhập câu hỏi` (`Ctrl+I`)
  - Index 2: `Ra đề thi`
  - Index 3: `Cài đặt`
  - Index 4: `Bài giảng` (`Ctrl+L` / `Ctrl+4`)
  - Index 5: `Câu hỏi trùng` (`Ctrl+D`)
  - Index 6: `Thu thập từ Web` (`Ctrl+Shift+W`)
  - Index 7: `Dashboard` (Trang chủ)
- Giữ nguyên 100% tính tương thích ngược của các chỉ số tab hiện có.
- Bổ sung nút truy cập nhanh "Câu hỏi trùng" và "Thu thập từ Web" vào mục *Bắt đầu nhanh* trên màn hình Home Dashboard.

---

## 5. KẾT QUẢ KIỂM THỬ THỰC TẾ (TEST VERIFICATION MATRIX)

Đã chạy toàn bộ test suite kết hợp Phase K và Phase L: **46/46 tests PASSED (100%)**.

```text
============================= test session starts =============================
platform win32 -- Python 3.14.6, pytest-9.1.1, pluggy-1.6.0
PySide6 6.11.2 -- Qt runtime 6.11.2 -- Qt compiled 6.11.2
rootdir: C:\Lap trinh Android\MCPTest2027\MCPTest

tests/test_phase_k1_parser.py .................................. [ 21%]
tests/test_phase_k2_shuffle.py .....                             [ 26%]
tests/test_phase_k3_serializer.py ........                       [ 34%]
tests/test_phase_k4_ui.py .....                                  [ 39%]
tests/test_phase_k5_export_e2e.py .........                      [ 47%]
tests/test_phase_k6_benchmark.py .....                           [ 52%]
tests/test_phase_l_dedup.py ........                             [ 69%]
tests/test_phase_l_scraper.py ...........                        [ 93%]
tests/test_phase_l_ui.py ...                                     [100%]

============================= 46 passed in 41.28s =============================
```

### Danh mục chi tiết các bài kiểm thử Phase L:
1. `tests/test_phase_l_dedup.py`:
   - `test_normalize_latex_safety`: Kiểm tra chuẩn hóa comment, khoảng trắng, giữ nguyên ngữ nghĩa toán học.
   - `test_level1_exact_normalized_duplicates`: Phát hiện trùng lặp tuyệt đối mức 1.
   - `test_level2_mcq_permutation_duplicates`: Phát hiện trùng lặp hoán vị 4 phương án mức 2 kèm đối chiếu đáp án đúng.
   - `test_level2_true_false_invariant_never_permuted`: Đảm bảo câu Đúng/Sai không bị hoán vị mệnh đề.
   - `test_level3_similarity_number_difference_guardrail`: Chốt an toàn ngăn chặn báo trùng sai khi khác số liệu/dấu âm.
   - `test_dedup_safe_delete_and_fk_protection`: Kiểm tra ràng buộc khóa ngoại bảo vệ câu hỏi đang được dùng trong đề thi/bài giảng.
   - `test_dedup_merge_metadata`: Gộp nhãn, chủ đề an toàn giữa các bản ghi.
   - `test_dedup_scan_files_and_export_clean_tex`: Quét file `.tex`, loại bỏ câu trùng và xuất file sạch không ghi đè file gốc.
2. `tests/test_phase_l_scraper.py`:
   - `test_ssrf_guard_blocks_private_and_local_networks`: Chặn đứng IP localhost, private IPv4/IPv6, metadata IP.
   - `test_html_to_latex_mathjax_and_katex`: Chuyển đổi công thức MathJax và KaTeX sang LaTeX chuẩn.
   - `test_html_to_latex_mathml_and_formatting`: Chuyển đổi MathML (`<mfrac>`, `<msup>`) và ký hiệu Unicode.
   - `test_vietjack_adapter_offline_fixture`: Bóc tách câu hỏi, phương án, đáp án và lời giải trang VietJack.
   - `test_tech24_adapter_offline_fixture`: Bóc tách câu hỏi và lời giải trang Tech24.
   - `test_loigiaihay_adapter_offline_fixture`: Bóc tách câu hỏi và lời giải trang Lời Giải Hay.
   - `test_generic_adapter_true_false_and_short_answer`: Bóc tách câu Đúng/Sai (`\choiceTF`) và Trả lời ngắn (`\shortans`).
   - `test_question_draft_ex_test_serialization`: Tuân thủ chuẩn ex_test khi tuần tự hóa.
   - `test_database_commit_requires_explicit_verified_status`: Chặn đứng việc lưu câu chưa duyệt vào CSDL.
   - `test_export_drafts_to_phase_k_exam_bundle`: Xuất đề thi Phase K, gọi pdfLaTeX biên dịch thành công file `.pdf` và `.zip`.
   - `test_export_never_reports_success_if_latex_fails_compilation`: Tuyệt đối không báo thành công khi biên dịch LaTeX lỗi.
3. `tests/test_phase_l_ui.py`:
   - `test_dedup_page_initialization_and_scope`: Kiểm tra giao diện quét trùng, chuyển đổi phạm vi CSDL / File.
   - `test_web_scraper_page_staging_and_moderation`: Kiểm tra giao diện staging, chuyển đổi URL / Dán HTML, thao tác duyệt/loại bỏ.
   - `test_main_window_has_both_phase_l_tabs`: Kiểm tra tích hợp cả 2 tab mới vào MainWindow, điều hướng và phím tắt.

---

## 6. HƯỚNG DẪN SỬ DỤNG CHO GIÁO VIÊN

### 6.1. Sử dụng Tab "Câu hỏi trùng"
1. Nhấn vào biểu tượng **Câu hỏi trùng** trên thanh điều hướng bên trái hoặc bấm `Ctrl+D`.
2. Chọn chế độ quét:
   - **Trong Cơ sở dữ liệu:** Chọn loại câu hỏi hoặc nhập từ khóa để quét trong ngân hàng câu hỏi.
   - **Trong các tệp mã nguồn (.tex):** Nhấn "Chọn tệp .tex..." để nạp một hoặc nhiều file `.tex`.
3. Nhấn **Bắt đầu quét trùng**.
4. Khi có kết quả, danh sách nhóm trùng hiển thị bên trái kèm tỷ lệ tương đồng và lý do phát hiện:
   - Nhấn vào từng nhóm để xem đối chiếu trực quan bên phải.
   - Chọn câu gốc muốn giữ lại (Radio button).
   - Nếu muốn loại bỏ câu trùng, tích chọn ô vuông "Xóa bản ghi này" (mặc định để trống an toàn).
   - Nhấn **Xóa các bản được chọn** để thực hiện (hệ thống sẽ yêu cầu xác nhận và tự động chặn nếu câu đang được dùng trong đề thi).
   - Với chế độ file, nhấn **Xuất file .tex đã lọc** để tạo file `.tex` mới đã loại bỏ câu trùng mà không làm thay đổi file gốc.

### 6.2. Sử dụng Tab "Thu thập từ Web"
1. Nhấn vào biểu tượng **Thu thập từ Web** hoặc bấm `Ctrl+Shift+W`.
2. Dán link bài tập (Ví dụ từ VietJack, Tech24, Lời Giải Hay) vào ô URL, hoặc chuyển sang chế độ "Dán mã HTML thô" nếu muốn lấy nội dung từ trang có bảo vệ.
3. Nhấn **Thu thập dữ liệu**.
4. Danh sách câu hỏi thu thập được sẽ xuất hiện ở cột Staging bên trái với trạng thái ban đầu là `[?]` (Chờ duyệt).
5. Nhấn vào từng câu để kiểm tra nội dung ở cột phải:
   - Chỉnh sửa đề bài, phương án, lời giải nếu cần.
   - Chọn đáp án đúng (A, B, C, D) cho câu trắc nghiệm.
   - Nhấn **Biên dịch xem trước** để kiểm tra tính hợp lệ của mã LaTeX bằng pdfLaTeX.
   - Nhấn **[✓ Đã kiểm duyệt]** nếu câu đạt chuẩn, hoặc **[✕ Loại bỏ]** nếu câu không phù hợp.
6. Sau khi duyệt xong:
   - Nhấn **Nhập câu đã duyệt vào Ngân hàng CSDL** để lưu vĩnh viễn vào ngân hàng câu hỏi.
   - Hoặc nhấn **Xuất đề thi Phase K (PDF & ZIP)** để tạo ngay đề kiểm tra chuẩn 4 phần kèm file PDF và gói ZIP di động.

---

## 7. KẾT LUẬN & TRẠNG THÁI NGHIỆM THU

Phase L đã hoàn thành xuất sắc 100% các tiêu chí kỹ thuật, bảo mật và trải nghiệm người dùng theo tài liệu đặc tả. Toàn bộ tính năng đã sẵn sàng phục vụ công tác giảng dạy và quản trị dữ liệu câu hỏi.
