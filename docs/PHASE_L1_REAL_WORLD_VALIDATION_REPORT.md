# Báo cáo Kiểm chứng Thực tế và Hoàn thiện LaTeX Converter (Phase L.1)
**Dự án:** MCPTest / LaTeX Question Studio  
**Mã báo cáo:** `PHASE_L1_REAL_WORLD_VALIDATION_REPORT`  
**Thời gian thực hiện:** 14/10/2026  
**Nhánh Git:** `main`  
**Hệ điều hành:** Windows 11 (build 26100)  
**Môi trường:** Python 3.14.6, PySide6 6.11.2, TeX Live 2026 (`pdfTeX 3.141592653-2.6-1.40.29`), SQLite Schema v19  

---

## 1. Tóm tắt Thực thi & Truy vết Baseline

| Thông số | Baseline L0 | Sau Phase L.1 |
| :--- | :--- | :--- |
| **Commit SHA đầu (L0)** | `ce45cc1` (Merge Phase L) | `ce45cc1` |
| **Commit SHA cuối (L5)** | — | `2a81113` |
| **Tổng số Pytest Suites** | 304 passed | **380 passed** (+76 tests mới) |
| **Thời gian chạy Full Suite** | 224s | 1086s (~18 phút, gồm compile hàng chục file TeX thật) |
| **Số lỗi P0 / Crash** | 0 | **0** |
| **Lỗi rò rỉ đáp án / lời giải** | 0 | **0** |
| **Thất thoát hình ảnh** | 0 | **0** |
| **SQLite Schema Version** | 19 | **19** (Bảo toàn tuyệt đối, không thay đổi) |

---

## 2. Bảng Truy vết Chi tiết (Traceability Matrix)

| Giai đoạn | Yêu cầu | Mã nguồn can thiệp | Kiểm thử tương ứng | Kết quả |
| :--- | :--- | :--- | :--- | :--- |
| **L0** | Thiết lập baseline, fix lỗi nền và lập bảng truy vết | `parsing/latex.py`, `tests/test_dashboard.py` | Toàn bộ 304 tests baseline | **PASS** (Commit `0c4d314`) |
| **L1** | Pipeline HTML $\to$ LaTeX có trạng thái text/math, xử lý MathML, KaTeX, Unicode, hóa học, an toàn macro | `scraping/html_to_latex.py` | `tests/test_phase_l1_latex_converter.py` (63 tests) | **PASS** (Commit `3c9cf35`) |
| **L2** | Adapter website thực tế, `AdapterStatus`, lazy image (`data-src`), SSRF protection, incomplete draft | `scraping/adapters/base.py`, `vietjack.py`, `tech24.py`, `loigiaihay.py`, `generic.py`, `web_import.py` | `tests/test_phase_l1_adapters_real.py` (8 tests) | **PASS** (Commit `4dd5a84`) |
| **L3** | Bộ dữ liệu trùng lặp $\ge 300$ cặp, chống O($N^2$), cảnh báo khác lời giải, cấm hoán vị `\choiceTF` | `application/dedup.py` | `tests/test_phase_l1_dedup_dataset.py` (4 tests, 310 pairs, 10k items) | **PASS** (Commit `d9f1695`) |
| **L4** | Chặn "duyệt tất cả" câu thiếu ảnh/lỗi, E2E scraping $\to$ staging $\to$ DB $\to$ 4 mã đề Phase K $\to$ ZIP $\to$ pdfLaTeX | `ui/pages/web_scraper_page.py`, `application/web_import.py` | `tests/test_phase_l1_e2e_export.py` (1 test E2E 8 PDF) | **PASS** (Commit `2a81113`) |
| **L5** | Chạy regression toàn dự án (380/380) và Windows EXE Smoke Test bytecode verification | `scripts/verify_ui_package.py`, `dist/0.5.3/` | Full Pytest suite + `verify_ui_package.py` | **PASS** |

---

## 3. Chi tiết Cải tiến & Nghiệm thu Kỹ thuật

### 3.1. Pipeline HTML $\to$ pdfLaTeX an toàn và đúng ngữ nghĩa (L1)
- **DOM Tree Parsing:** Chuyển đổi hoàn toàn từ regex sang kiến trúc DOM Tree (`HTMLParser` chuẩn của thư viện chuẩn Python, không phụ thuộc third-party parser không ổn định).
- **State Machine Text vs. Math:**
  - Văn bản thông thường tự động escape các ký tự đặc biệt của TeX: `%`, `&`, `#`, `_`, `{`, `}`, `~`, `^`, `\`.
  - Không bao giờ sinh macro toán học ngoài math mode. Ký hiệu Unicode toán (`∈, ≤, ≥, √, ∑, ∫, π, α, ±, ×, °`) được bọc math mode tự động `$x \in \mathbb{R}$`, `$30^\circ$`.
  - Phân tích ngữ cảnh khoa học: Đơn vị đo (`m²`, `cm³`, `m/s²`, `kg/m³`) $\to$ `\text{m}^2`, `\text{m/s}^2`.
  - Công thức hóa học (`H₂O`, `CO₂`, `CaCO₃`, `H₂SO₄`, `Fe₂O₃`) $\to$ `\text{H}_2\text{O}`, `\text{H}_2\text{SO}_4`.
- **Recursive MathML & KaTeX Annotation:**
  - Hỗ trợ đầy đủ các thẻ MathML cốt lõi: `mfrac`, `msup`, `msub`, `msubsup`, `msqrt`, `mroot`, `mfenced`, `mtable`, `mover`, `munder`, `mtext`, `mi`, `mn`, `mo`.
  - Trích xuất ưu tiên chuỗi TeX gốc trong `<annotation encoding="application/x-tex">` của KaTeX trước khi fallback về MathML.
- **Bảo mật TeX Sandbox:**
  - Cô lập và triệt tiêu các macro gây rò rỉ I/O hoặc thực thi shell nguy hiểm: `\write18`, `\input`, `\include`, `\openin`, `\openout`, `\catcode`, `\def`.
- **Thực nghiệm TeX Live 2026:**
  - 60 ca corpus (Toán 6–12, KHTN 6–9, Vật lí 10–12, Hóa học) kiểm chứng độ chính xác ngữ nghĩa.
  - 20 ca đại diện biên dịch trực tiếp với **pdfLaTeX thật**: 100% biên dịch ra PDF hợp lệ, không lỗi nghiêm trọng.
  - 10 ca đối chiếu thủ công đạt độ tương đồng 100% với TeX chuẩn ex_test.

### 3.2. Adapter Web thực tế & Tuân thủ Bản quyền (L2)
- **AdapterStatus Enum:** Trả về trạng thái phân định rành mạch:
  - `supported`: Website được hỗ trợ chuyên biệt và đã kiểm thử cấu trúc selectors (VietJack, Tech24, Loigiaihay).
  - `generic_fallback`: Nguồn web thông thường trích xuất qua heuristic parser.
  - `blocked`: Phát hiện bảo vệ Cloudflare, CAPTCHA bot detection hoặc HTTP 403 Forbidden.
  - `parse_failed`, `partial`, `needs_review`: Phản hồi rõ ràng nếu DOM thay đổi hoặc thiếu thông tin.
- **Trích xuất ảnh Lazy-loaded:** Quét đồng thời các thuộc tính `data-original`, `data-src`, `data-lazy-src`, `src`, `srcset` và chuẩn hóa URL tương đối thành URL tuyệt đối an toàn.
- **Bảo vệ SSRF 2 lớp:** Ngăn chặn truy cập vào các dải IP nội bộ, loopback (`127.0.0.1`, `localhost`, `0.0.0.0`, RFC 1918 private IPs, link-local metadata `169.254.169.254`).
- **An toàn Câu hỏi Thiếu Ảnh:**
  - Nếu ảnh web bị lỗi mạng/timeout/hỏng: Draft được đánh dấu `has_missing_images = True`, giữ comment `% [THIẾU ẢNH: <url>]` trong mã TeX, cấm tự động duyệt và cấm ghi vào CSDL cho đến khi người dùng bổ sung ảnh thủ công.

### 3.3. Độ chính xác Tìm câu trùng & Hiệu năng 10,000 câu (L3)
- **Bộ dữ liệu có nhãn 310 cặp (Labeled Dataset):**
  1. Trùng nguyên văn: 35 cặp $\to$ Độ chính xác 100%.
  2. Khác biệt khoảng trắng / comment / xuống dòng: 35 cặp $\to$ Độ chính xác 100%.
  3. Hoán vị phương án MCQ có `\True`: 35 cặp $\to$ Bắt trùng 100%, 0 false-positive.
  4. Hoán vị mệnh đề `\choiceTF` (Đúng/Sai): 35 cặp $\to$ **TUYỆT ĐỐI KHÔNG COI LÀ TRÙNG LẶP** (bảo vệ thang chấm thi THPT vì mệnh đề a, b, c, d chấm điểm độc lập).
  5. Khác số liệu / dấu âm / số mũ: 35 cặp $\to$ 0 false-positive.
  6. Khác hình vẽ / TikZ / asset đồ họa: 35 cặp $\to$ 0 false-positive.
  7. Khác lời giải (cùng đề và đáp án): 35 cặp $\to$ Nhận diện trùng prompt/options kèm cảnh báo rõ: *"Chú ý: Lời giải hai câu khác nhau, cần giáo viên xem xét trước khi gộp!"* với confidence 0.90, không tự động xóa.
  8. Gần trùng nhưng khác khái niệm toán học (GTLN vs GTNN): 35 cặp $\to$ 0 false-positive.
  9. Câu hỏi lồng môi trường `\immini`: 30 cặp $\to$ Bóc tách nội dung chính xác.
- **Hiệu năng Scale 10,000 câu hỏi:**
  - Ứng dụng mô hình **Inverted Index (Chỉ mục đảo)** cho Step 3 fuzzy similarity thay cho vòng lặp lồng $O(N^2)$.
  - Thời gian quét 10,000 câu: **0.44 giây** (vượt xa chỉ tiêu < 5.0 giây).
  - Bộ nhớ RAM tiêu thụ đỉnh (Peak RAM): **24.8 MB** (vượt chỉ tiêu < 120 MB).
  - Cơ chế hủy bỏ (Cancellation responsiveness): Dừng ngay lập tức khi người dùng bấm Hủy mà không khóa giao diện UI.

### 3.4. Staging UI Moderation & Liên kết Xuất đề Phase K (L4)
- **Kiểm soát Duyệt hàng loạt:** Nút *"Duyệt tất cả"* (`_verify_all_valid`) bắt buộc kiểm tra `not d.has_missing_images` và `not d.warnings`. Bất kỳ câu nào thiếu ảnh hoặc chưa chọn đáp án đúng đều bị giữ lại ở trạng thái `needs_review`.
- **E2E Multi-Variant Exam Pipeline:**
  - Luồng khép kín: Web HTML $\to$ Trích xuất Drafts $\to$ Kiểm duyệt $\to$ Lưu vào SQLite CSDL ngân hàng câu hỏi $\to$ Tạo đề thi Phase K $\to$ Xuất 4 mã đề hoán vị (`De01`, `De02`, `De03`, `De04`) $\to$ Đóng gói ZIP $\to$ Giải nén tại thư mục độc lập hoàn toàn $\to$ Biên dịch cả bản học sinh và bản giáo viên của cả 4 mã đề bằng **pdfLaTeX thật**.
  - Kết quả: Tất cả 8 file PDF biên dịch thành công 100%, bản học sinh không có bất kỳ dấu hiệu rò rỉ `\True` hay lời giải nào.

### 3.5. Kiểm thử Đóng gói Windows EXE (L5)
- Đóng gói ứng dụng bằng PyInstaller ở chế độ Windows GUI Windowed (PE Subsystem 2, không console popup).
- Chạy công cụ kiểm chứng bytecode `scripts/verify_ui_package.py`:
  - Kiểm tra 54/54 module Python trong file thực thi: **100% khớp tuyệt đối** với mã nguồn mới nhất (`all_modules_current: true`).
  - Toàn bộ 22 module UI đã cập nhật đồng bộ.
  - CSDL ngân hàng câu hỏi SQLite schema version 19 nguyên vẹn (`integrity: ok`).
  - Mã thoát ứng dụng: `0`.

---

## 4. Những Gì Đã Kiểm Chứng & Chưa Kiểm Chứng

### 4.1. Đã kiểm chứng (Verified)
1. **Toán học & Khoa học:** Biến đổi chính xác các công thức từ HTML, MathML, KaTeX sang cú pháp LaTeX chuẩn của gói `ex_test.sty` và `MAPClass.cls`.
2. **Biên dịch pdfLaTeX thật:** Đã kiểm chứng trên môi trường Windows TeX Live 2026 với hơn 30 tài liệu TeX khác nhau (đơn lẻ và đa mã đề).
3. **An toàn dữ liệu:** Không xóa tự động câu hỏi trùng; không nhập câu hỏi thiếu thông tin hoặc chưa kiểm duyệt vào CSDL.
4. **Hợp đồng Phase K:** Đảm bảo cấu trúc 4 phần chuẩn THPT (Trắc nghiệm nhiều lựa chọn, Đúng/Sai, Trả lời ngắn, Tự luận), sinh đúng ma trận mã đề De01–De04 và bảng đáp án.
5. **Windows EXE:** Khởi động thành công, nhận diện đúng schema CSDL và bộ bytecode mới nhất.

### 4.2. Giới hạn & Những gì chưa kiểm chứng trên thực tế (Unverified / Known Boundaries)
1. **Cloudflare WAF / Đăng nhập / Paywall:** Khi các trang web mục tiêu bật Cloudflare Turnstile hoặc yêu cầu đăng nhập tài khoản giáo viên, adapter chủ động trả về trạng thái `AdapterStatus.BLOCKED`. Không vượt qua các cơ chế này nhằm tuân thủ pháp lý và điều khoản dịch vụ của bên thứ ba.
2. **Hình ảnh chứa nội dung công thức (Image-as-formula):** Một số bài tập cũ trên web nhúng công thức dưới dạng file ảnh GIF/PNG cắt sẵn. Hệ thống tải và nhúng ảnh qua `\includegraphics`, nhưng không thực hiện OCR toán học tự động để chuyển ngược thành mã TeX.

---

## 5. Hướng dẫn Dùng thử Thực tế

### 5.1. Dùng thử Tab "Thu thập từ Web" với URL hoặc HTML
1. Khởi động ứng dụng từ menu hoặc chạy:
   ```powershell
   .\.venv\Scripts\python.exe -m latex_question_studio
   ```
   *(Hoặc chạy trực tiếp `dist\0.5.3\LaTeXQuestionStudio\LaTeXQuestionStudio.exe`)*
2. Vào tab **Thu thập từ Web** trên thanh điều hướng bên trái.
3. Chọn chế độ:
   - **Nhập URL trực tiếp:** Điền một URL công khai cho phép (ví dụ một bài tập trên `tech24.vn` hoặc `vietjack.me`), nhấn **"Bắt đầu thu thập"**.
   - **Dán mã HTML (Khuyến nghị cho bài viết có bản quyền/đăng nhập):** Chuyển sang *"Dán mã HTML nguồn"*, copy đoạn mã chứa câu hỏi từ trình duyệt và paste vào ô soạn thảo, nhấn **"Trích xuất câu hỏi"**.
4. Các câu hỏi được bóc tách sẽ hiển thị ở cột bên trái:
   - Câu hỏi có cảnh báo hoặc thiếu ảnh sẽ có biểu tượng `⚠️`.
   - Chỉnh sửa đề bài, phương án hoặc đáp án đúng ở khung soạn thảo bên phải nếu cần.
   - Nhấn **"Biên dịch xem trước"** để kiểm tra biên dịch PDF tức thời qua pdfLaTeX.
5. Khi hoàn tất, nhấn **"✓ Đã kiểm duyệt"**, sau đó nhấn **"Nhập câu đã duyệt vào Ngân hàng CSDL"** hoặc **"Xuất đề thi Phase K (PDF & ZIP)"**.

### 5.2. Dùng thử Tab "Câu hỏi trùng" với File `.tex` Thực tế
1. Chuyển sang tab **Câu hỏi trùng**.
2. Chọn phạm vi quét:
   - *"Trong CSDL hiện tại"*: Quét toàn bộ kho câu hỏi trong ngân hàng.
   - *"Trong file .tex..."*: Chọn 1 hoặc nhiều file `.tex` bài tập từ máy tính (ví dụ file `data/sample_questions.tex`).
3. Nhấn **"Bắt đầu quét trùng lặp"**.
4. Bảng kết quả sẽ nhóm các câu hỏi theo 3 cấp độ:
   - **Trùng tuyệt đối (Exact):** Nội dung sau chuẩn hóa giống 100%.
   - **Hoán vị đáp án (Permutation):** Đề bài giống nhau, 4 phương án bị xáo trộn. Cảnh báo nếu lời giải giữa hai câu khác nhau.
   - **Tương đồng cao (Similarity):** Gợi ý đối chiếu văn bản, không cho phép xóa tự động.
5. Bấm vào từng nhóm để xem màn hình đối chiếu 2 cột có tô màu khác biệt trực quan. Giáo viên có toàn quyền chọn câu chính (Primary) và quyết định giữ lại hay loại bỏ.
