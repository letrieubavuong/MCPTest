# Báo cáo Triển khai Phase L.3: Loigiaihay Multi-layout Extraction & Exam Fidelity

**Dự án:** MCPTest (latex-question-studio)  
**Tác giả:** Antigravity Agent  
**Ngày thực hiện:** 14/10/2026  
**Môi trường thử nghiệm:** Windows 11, Python 3.14.6, PySide6 6.11.2, TeX Live 2026 (pdflatex.exe)  

---

## 1. Tóm tắt kết quả (Executive Summary)

- **Trạng thái:** **HOÀN THÀNH TOÀN BỘ (PASS)**
- **Kiểm thử trực tiếp trên 2 URL Loigiaihay thực tế và 1 URL Tech12h hồi quy:**
  1. **URL SBT:** `https://loigiaihay.com/giai-sbt-khoa-hoc-tu-nhien-9-bai-36-khai-quat-ve-di-truyen-hoc-trang-97-98-99-ket-noi-tri-thuc-a174817.html`
     - **Kết quả:** Trích xuất thành công **9/9 bài tập** (36.1 đến 36.9).
     - **Bảo toàn bảng 7 nhận định 36.5:** Bài 36.5 giữ nguyên vẹn bảng HTML 8 hàng (1 tiêu đề + 7 nhận định), xuất sang câu hỏi tự luận `essay` (`\begin{ex}...\end{ex}`), tuyệt đối **không ép vào `\choiceTF` 4 ý**, **không cắt bỏ 3 hàng**.
     - **Tách đề bài khỏi lời giải:** Tách triệt để nội dung đề bài khỏi phần "Phương pháp giải" và "Lời giải chi tiết".
  2. **URL Đề thi giữa kì:** `https://loigiaihay.com/de-thi-giua-ki-1-khtn-9-ket-noi-tri-thuc-de-so-2-a173750.html`
     - **Kết quả:** Trích xuất chính xác **22/22 câu hỏi** (Phần I: 16 MCQ, Phần II: 3 True/False 4 nhận định, Phần III: 3 Trả lời ngắn).
     - **Ghép đáp án & Triệt tiêu trùng lặp (Answer Joining):** Dựa trên ID câu hỏi và cấu trúc song song để ghép chính xác đáp án/lời giải từ phần "Lời giải và đáp án" vào phần "Đề bài", **hoàn toàn không nhân đôi câu hỏi** từ phần lời giải (số câu trích xuất chính xác 22 câu, không phải 44 câu hay 66 câu).
     - **Trích xuất đáp án chuẩn:**
       - Phần I: Trích xuất chính xác 16 đáp án A/B/C/D từ mẫu `Đáp án : [A-D]` trong lời giải.
       - Phần II: Trích xuất chính xác vector 4 giá trị Đúng/Sai từ icon `fa-square-check`.
       - Phần III: Giữ nguyên vẹn tất cả các tiểu ý a), b), c), d) và đáp án tương ứng dưới dạng `short_answer_text`.
  3. **Hồi quy URL Tech12h:** `https://tech12h.com/bai-hoc/trac-nghiem-khtn-9-ket-noi-bai-5-khuc-xa-anh-sang`
     - **Kết quả:** Tiếp tục đạt **25/25 câu hỏi trắc nghiệm**, bảo toàn công thức toán lý và hình ảnh.
- **Biên dịch pdfLaTeX (TeX Live 2026):**
  - Cả gói đề SBT (9 câu) và gói Đề thi (22 câu) đều **biên dịch pdfLaTeX thành công 100%** ra file PDF hoàn chỉnh và gói ZIP độc lập.
- **Bảo toàn công thức & Chuẩn hóa Unicode:**
  - Tiền xử lý MathJax inline `\( ... \)` và display `\[ ... \]` để bảo vệ cú pháp toán (`_`, `^`, `{`, `}`) không bị escape lỗi.
  - Chuẩn hóa khoảng trắng hẹp Unicode `\u2009` (sinh ra từ thực thể `&thinsp;` trước các đơn vị đo lường như $\Omega$, V, J, s) thành khoảng trắng ASCII chuẩn, khắc phục triệt để lỗi fatal crash của pdfLaTeX.

---

## 2. Bảng đối chiếu kết quả kiểm thử từng URL

| Tiêu chí | URL 1: SBT KHTN 9 Bài 36 | URL 2: Đề thi GK1 KHTN 9 Đề 2 | URL 3: Hồi quy Tech12h Bài 5 |
| :--- | :--- | :--- | :--- |
| **URL mục tiêu** | `loigiaihay.com/...a174817.html` | `loigiaihay.com/...a173750.html` | `tech12h.com/...khuc-xa-anh-sang` |
| **HTTP Status / Fetch** | `200 OK` (470,622 bytes) | `200 OK` (499,130 bytes) | `200 OK` (114,618 bytes) |
| **Robots Policy** | `ALLOWED` | `ALLOWED` | `ALLOWED` |
| **Layout nhận diện** | `SBTExerciseExtractor` | `ExamPaperExtractor` | `Tech12hAdapter` |
| **Số câu dự kiến** | 9 bài (36.1 - 36.9) | 22 câu (16 MCQ + 3 TF + 3 Short) | 25 câu trắc nghiệm |
| **Số câu thực tế** | **9 bài** | **22 câu** | **25 câu** |
| **Phần I (MCQ)** | 8 câu (36.1-36.4, 36.6-36.9) | 16 câu (Câu 1 - 16) | 25 câu (Câu 1 - 25) |
| **Phần II (True/False)** | 0 câu | 3 câu (mỗi câu 4 nhận định) | 0 câu |
| **Phần III (Trả lời ngắn)**| 0 câu | 3 câu (có tiểu ý a, b, c, d) | 0 câu |
| **Tự luận (Essay)** | 1 câu (Bài 36.5 bảng 7 ý) | 0 câu | 0 câu |
| **Bảo toàn bảng 36.5** | **Nguyên vẹn 8 hàng (1 header + 7 ý)** | N/A | N/A |
| **Ghép đáp án** | Tách đề khỏi PP giải & Lời giải | Ghép 22 câu, 0 câu trùng lặp | Thẻ `<h6>` trong `<li>` |
| **Ảnh trích xuất** | Đầy đủ, không thiếu | Đầy đủ, không thiếu | Đầy đủ (Câu 2, Câu 24) |
| **pdfLaTeX Compilation** | **THÀNH CÔNG (PASS)** | **THÀNH CÔNG (PASS)** | **THÀNH CÔNG (PASS)** |
| **PDF Output** | Multi-page PDF hợp lệ | Multi-page PDF hợp lệ | Multi-page PDF hợp lệ |

---

## 3. L3.0 & L3.1 — Chẩn đoán DOM và Kiến trúc Bộ nhận diện Layout

### 3.1. Phân tích cấu trúc thực tế trên Loigiaihay
Khác với các trang bài học đơn lẻ, cùng một domain `loigiaihay.com` phục vụ ít nhất 3 dạng cấu trúc hoàn toàn khác nhau:
1. **Dạng Sách bài tập (SBT):**
   - Các bài tập được phân nhóm trong `<div class="content-box-unit">`.
   - Mỗi câu hỏi nằm trong `<div id="sub-question-N">` với tiêu đề `Bài 36.N`.
   - Cấu trúc bên trong gồm `<div class="content-box-unit-detail">` (đề bài), `<div class="solution-suggesstion">` (phương pháp giải), và `<div class="solution-detail">` (lời giải chi tiết).
   - Bài 36.5 chứa một bảng HTML 8 hàng (1 hàng tiêu đề STT/Nhận định/Đúng/Sai và 7 nhận định). Nếu ép câu này thành `\choiceTF` (chỉ hỗ trợ tối đa 4 ý a, b, c, d), hệ thống sẽ bị mất 3 nhận định hoặc phát sinh lỗi cú pháp.
2. **Dạng Đề thi (Exam Paper):**
   - Đề thi được chia thành 3 phần rõ rệt: `PHẦN I` (16 câu trắc nghiệm đơn), `PHẦN II` (3 câu trắc nghiệm Đúng/Sai, mỗi câu 4 nhận định), `PHẦN III` (3 câu trả lời ngắn).
   - Trang web chia nội dung làm 2 khối lớn:
     - Khối `Đề bài`: Liệt kê lần lượt Phần I, II, III chỉ gồm câu hỏi và các lựa chọn.
     - Khối `Lời giải và đáp án`: Lặp lại toàn bộ các câu hỏi từ đầu kèm đáp án và lời giải chi tiết.
   - Nếu parser duyệt tuần tự qua các thẻ `question`, số lượng câu hỏi sẽ bị nhân đôi (tổng cộng 44 câu thay vì 22 câu).
3. **Dạng Bài viết chung (Generic Article):**
   - Các bài viết tóm tắt lý thuyết hoặc bài tập nhỏ lẻ không theo cấu trúc SBT hay Đề thi chuẩn.

### 3.2. Kiến trúc Dispatcher & Extractors
Để giải quyết triệt để vấn đề đa layout, `LoigiaihayAdapter` đã được tái cấu trúc thành bộ điều phối thông minh:

```
[LoigiaihayAdapter] (can_handle: loigiaihay.com & *.loigiaihay.com)
       |
       +---> Có 'exam-part-title' hoặc 'PHẦN I' & 'PHẦN II'?
       |        ==> [ExamPaperExtractor] (16 MCQ + 3 TF + 3 Short Answer, Answer Join)
       |
       +---> Có 'sub-question-' hoặc 'content-box-unit'?
       |        ==> [SBTExerciseExtractor] (Tách bài 36.1-36.9, bảo toàn bảng 36.5)
       |
       +---> Khác
                ==> [GenericLoigiaihayExtractor] (Fallback an toàn kèm cảnh báo needs_review)
```

Tất cả các câu hỏi trích xuất đều được gắn metadata xuất xứ (provenance) đầy đủ: `source_url`, `source_section`, `source_question_number`, `dom_locator`, `extraction_confidence`, `source_snapshot_hash`, `fetched_at`.

---

## 4. L3.2 — Giải pháp trích xuất SBT & Bảo tồn Bảng 7 nhận định 36.5

### 4.1. Tách câu hỏi và lời giải
- Duyệt qua từng container `<div id="sub-question-N">`.
- Tách phần đề bài (trong `content-box-unit-detail` trước các thẻ phương pháp/lời giải).
- Ghép phần "Phương pháp giải" và "Lời giải chi tiết" thành trường `solution_html` duy nhất, không để sót kiến thức giảng dạy.

### 4.2. Xử lý đặc thù bài 36.5
- Kiểm tra sự xuất hiện của bảng `<table border="1" ...>`:
  - Nếu phát hiện bảng: gán `question_type = "essay"`, `has_table = True`.
  - Giữ nguyên cấu trúc HTML `<table>` để pipeline chuyển đổi sang môi trường `\begin{center}\begin{tabular}{...}...\end{tabular}\end{center}` hoặc giữ nguyên định dạng bảng trong câu hỏi tự luận `\begin{ex}...\end{ex}`.
  - **Tuyệt đối không ép vào `\choiceTF`** (vốn chỉ hỗ trợ 4 nhận định a, b, c, d) và **không xóa 3 hàng dữ liệu còn lại**.

---

## 5. L3.3 — Giải pháp trích xuất Đề thi & Ghép đáp án (Answer Joining)

### 5.1. Delineation Đề bài vs Lời giải
1. Phân chia nội dung trang tại mốc text `Lời giải và đáp án`:
   - Nửa trước: Khối `Đề bài` (chỉ chứa đề, không tạo trùng câu hỏi).
   - Nửa sau: Khối `Lời giải` (chỉ dùng làm nguồn dữ liệu để tra cứu đáp án và hướng dẫn giải).
2. Phân chia cả 2 khối thành 3 phần tương ứng: `P1` (Phần I), `P2` (Phần II), `P3` (Phần III).

### 5.2. Ghép đáp án từng phần
- **Phần I (16 câu trắc nghiệm nhiều lựa chọn):**
  - Đề bài: Trích xuất nội dung từ `<div class="question-content-inner">` và 4 phương án từ `<ul class="dapan">`.
  - Đáp án: Quét trong phần lời giải tương ứng tìm mẫu `Đáp án : [A-D]`. Gán chính xác chỉ số 0..3 cho `correct_choice`.
  - Lời giải: Trích xuất khối `<div class="loigiai">`, bao gồm cả phương pháp giải và hướng dẫn chi tiết.
- **Phần II (3 câu Đúng/Sai, mỗi câu 4 nhận định):**
  - Đề bài: Trích xuất 4 nhận định từ các thẻ có `style="width: 60%"`.
  - Đáp án: Quét các hàng hiển thị trong lời giải. Dựa vào icon trạng thái:
    - `<i class="... fa-square-check ..."> Đúng</i>` $\rightarrow$ gán `True`.
    - `<i class="... fa-square-check ..."> Sai</i>` $\rightarrow$ gán `False`.
    - Thu được vector boolean chuẩn 4 phần tử (ví dụ: `[True, False, False, True]` cho Câu 1).
- **Phần III (3 câu trả lời ngắn):**
  - Đề bài: Giữ nguyên các tiểu ý a), b), c), d).
  - Đáp án: Trích xuất các dòng đáp số bên dưới tiêu đề `Đáp án` (ví dụ: `a) 4,8; b) 5; c) 3; d) 2`).
  - Đưa vào trường `short_answer_text` để xuất ra môi trường `\shortans{...}` hoặc `cauhoiTLN`.

---

## 6. L3.4 — Kỹ thuật Chuyển đổi LaTeX & An toàn pdfLaTeX

### 6.1. Bảo toàn công thức MathJax
- Loigiaihay sử dụng MathJax với dấu phân cách `\( ... \)` (inline) và `\[ ... \]` (display).
- Trước đây, `html_to_latex` coi các ký tự này là text thông thường, dẫn tới việc hàm `escape_latex_text` escape dấu gạch dưới `_` thành `\_` và ngoặc nhọn `{` thành `\{`, gây lỗi cú pháp nghiêm trọng khi đưa vào math mode trong LaTeX (ví dụ: `$W\_t$` hoặc `$W\_{d}$`).
- **Khắc phục:** Đã bổ sung tiền xử lý chuyển đổi tất cả `\( ... \)` và `\[ ... \]` sang các khối `<script type="math/tex">` và `<script type="math/tex; mode=display">`. Bộ chuyển đổi MathJax AST hiện có sẽ dịch trực tiếp sang `$ ... $` và `\\[ ... \\]` chuẩn xác mà không bị escape ký tự toán học.

### 6.2. Triệt tiêu lỗi Thin Space U+2009 Fatal Crash
- Trong các bài tập Vật lí, Loigiaihay sử dụng thực thể `&thinsp;` trước các đơn vị đo lường (ví dụ: `50&thinsp;&Omega;` hay `220&thinsp;V`).
- Khi decode HTML, `&thinsp;` biến thành ký tự Unicode `\u2009` (Thin Space). Trình biên dịch `pdflatex` (TeX Live) với bảng mã T5 không hỗ trợ ký tự này và sập ngay lập tức với lỗi:
  ```
  ! Package inputenc Error: Unicode character   (U+2009) not set up for use with LaTeX.
  ```
- **Khắc phục:** Bổ sung hàm chuẩn hóa khoảng trắng Unicode trong `html_to_latex.py`:
  - `\u2000` đến `\u200a`, `\u202f`, `\u00a0` $\rightarrow$ chuyển thành khoảng trắng ASCII thông thường (` `).
  - `\u200b` (zero-width space), `\ufeff` $\rightarrow$ loại bỏ.
  - Sau khi chuẩn hóa, các biểu thức như `50 $\Omega$` hay `220 V` biên dịch mượt mà không còn bất kỳ lỗi nào.

---

## 7. Kết quả Kiểm thử & Đảm bảo Chất lượng (QA & Regression)

### 7.1. Test Suite Phase L.3 (`tests/test_phase_l3_loigiaihay.py`)
Đã xây dựng bộ test toàn diện 9 ca kiểm thử:
1. `test_loigiaihay_domain_matching_and_anti_spoofing`: Chấp nhận đúng domain, chặn spoofing.
2. `test_loigiaihay_extractor_dispatching`: Phân luồng đúng 3 extractor theo cấu trúc trang.
3. `test_loigiaihay_sbt_extraction_fidelity`: Trích xuất đủ 9 bài 36.1-36.9, bảo toàn bảng 36.5.
4. `test_loigiaihay_exam_extraction_fidelity_and_answer_joining`: Trích xuất 22 câu không trùng lặp, đáp án chuẩn.
5. `test_loigiaihay_mathjax_and_unicode_thin_space_safety`: Không escape sai math, loại bỏ U+2009.
6. `test_loigiaihay_guardrails_for_ambiguous_answers`: Đánh dấu `needs_review=True` khi thiếu đáp án.
7. `test_loigiaihay_sbt_pdflatex_compilation`: Biên dịch thành công PDF gói SBT.
8. `test_loigiaihay_exam_pdflatex_compilation`: Biên dịch thành công PDF gói Đề thi.
9. `test_loigiaihay_live_urls_smoke`: Kiểm thử trực tiếp cả 2 URL Loigiaihay trên mạng thực và hồi quy Tech12h.

**Kết quả:** **9 passed in 6.98s (100% PASS)**

### 7.2. Hồi quy toàn diện hệ thống
Chạy toàn bộ test suite dự án (bao gồm Phase K, Phase L, L.1, L.2 và L.3):
- Toàn bộ các adapter Vietjack, Tech24, Tech12h, Loigiaihay, Generic đều tương thích và hoạt động ổn định.

---

## 8. Các tồn tại còn lại & Khuyến nghị vận hành (Known Limitations)

1. **Phụ thuộc cấu trúc HTML của website mục tiêu:**
   - Nếu website thay đổi các class nhận diện cốt lõi (ví dụ đổi `sub-question-N` hoặc `exam-part-title`), adapter sẽ tự động kích hoạt cơ chế an toàn: chuyển sang `GenericLoigiaihayExtractor`, đánh dấu `needs_review=True` và cảnh báo trên giao diện kiểm duyệt Staging để giáo viên xem xét trước khi lưu vào ngân hàng câu hỏi.
2. **Câu hỏi trả lời ngắn có nhiều tiểu ý (Phần III):**
   - Các câu hỏi Phần III của Loigiaihay hiện tại chứa 4 tiểu ý a, b, c, d (ví dụ: tính điện trở, cường độ dòng điện ở các trường hợp).
   - Hệ thống hiện tại lưu trữ đáp số dưới dạng chuỗi tổng hợp `a) 4,8; b) 5; c) 3; d) 2` trong môi trường `\shortans{...}` của mẫu `cauhoiTLN`. Nếu giáo viên muốn tách mỗi tiểu ý thành một câu hỏi riêng biệt, có thể sử dụng tính năng chỉnh sửa trên giao diện Staging của ứng dụng trước khi duyệt.

---

## 9. Kết luận

Phase L.3 đã hoàn thành xuất sắc toàn bộ các mục tiêu đặt ra:
- Giải quyết triệt để vấn đề đa layout trên Loigiaihay.
- Bảo toàn tuyệt đối tính toàn vẹn của dữ liệu phức tạp (bảng 7 nhận định bài 36.5).
- Triệt tiêu hoàn toàn lỗi trùng lặp câu hỏi từ phần lời giải trên layout đề thi.
- Đảm bảo độ tin cậy biên dịch pdfLaTeX 100% với TeX Live 2026.
