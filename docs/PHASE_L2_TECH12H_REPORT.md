# Báo cáo Triển khai Phase L.2: Tech12h Adapter & Real-Page Import Reliability

**Dự án:** MCPTest (latex-question-studio)  
**Tác giả:** Antigravity Agent  
**Ngày thực hiện:** 14/10/2026  
**Môi trường thử nghiệm:** Windows 11, Python 3.14.6, PySide6 6.11.2, TeX Live 2026 (pdflatex.exe)  
**URL bắt buộc kiểm thử:** `https://tech12h.com/bai-hoc/trac-nghiem-khtn-9-ket-noi-bai-5-khuc-xa-anh-sang`

---

## 1. Tóm tắt kết quả (Executive Summary)

- **Trạng thái:** **HOÀN THÀNH TOÀN BỘ (PASS)**
- **Kiểm thử trực tiếp trên URL thực tế:** Đã fetch và trích xuất thành công **25/25 câu hỏi trắc nghiệm** (100% đúng cấu trúc 4 phương án, đầy đủ công thức toán/lý, ký hiệu độ `$^\circ$`, và hình ảnh đính kèm).
- **Phân định tên miền:** Tách biệt tuyệt đối `tech12h.com` và `tech24.vn`. Cơ chế anti-spoofing chặn đứng các tên miền giả mạo (`fake-tech12h.com`, `tech12h.com.evil.org`, `tech12h.vn`).
- **Cơ chế xác thực đáp án DOM/Semantics:** Khám phá và kiểm chứng logic đáp án thực tế của Tech12h qua mã nguồn JavaScript phía client: phương án đúng được bọc trong thẻ `<h6>...</h6>` bên trong thẻ `<li>`.
- **Bảo vệ an toàn (Guardrails):** Không bao giờ tự ý gán `\True` nếu đánh dấu đáp án bị thiếu hoặc có nhiều hơn 1 đáp án; tự động chuyển sang `needs_review=True` và `correct_choice=None`.
- **Biên dịch pdfLaTeX & Xuất đề:** Biên dịch thành công 100% với TeX Live 2026 ra PDF chuẩn MAPClass/ex_test và gói ZIP đề thi hoàn chỉnh.
- **Hồi quy & Đóng gói:** Toàn bộ test suite chạy thành công, không làm phá vỡ hợp đồng Phase K, L, L.1.

---

## 2. L2.0 — Chẩn đoán chính xác nguyên nhân lỗi (Root Cause Diagnosis)

### 2.1. Đo kiểm kết nối và phản hồi từ URL mục tiêu

| Tham số | Giá trị thực tế ghi nhận | Đánh giá |
| :--- | :--- | :--- |
| **URL mục tiêu** | `https://tech12h.com/bai-hoc/trac-nghiem-khtn-9-ket-noi-bai-5-khuc-xa-anh-sang` | Đạt chuẩn |
| **HTTP Status** | `200 OK` | Thành công |
| **Redirect Chain** | 0 redirects (truy cập trực tiếp) | Không bị chuyển hướng |
| **Content-Type** | `text/html; charset=UTF-8` | Chuẩn UTF-8 |
| **Response Length** | 114,618 bytes | Đầy đủ nội dung |
| **Robots.txt Policy** | `ALLOWED` (Cho phép Agent truy cập `/bai-hoc/*`) | Hợp lệ |
| **SSRF Guard** | `ALLOWED` (Phân giải IP công cộng hợp lệ) | Đạt bảo mật |
| **Thời gian fetch** | ~ 450 ms | Ổn định |

### 2.2. Chi tiết 7 nguyên nhân gốc khiến ứng dụng trước đây không lấy được dữ liệu

1. **Chưa có Adapter chuyên biệt cho Tech12h:**
   - Trước Phase L.2, hệ thống chỉ có `Tech24Adapter` và `GenericArticleAdapter`.
   - Khi người dùng dán URL `tech12h.com`, hệ thống rơi vào `GenericArticleAdapter`.
2. **Nhiễu cấu trúc DOM từ GenericAdapter:**
   - `GenericArticleAdapter` quét toàn bộ thẻ HTML của trang (bao gồm thanh điều hướng, bài viết liên quan, quảng cáo, sidebar), chia nhỏ trang thành hơn 350 đoạn rời rạc không chứa đủ 4 phương án A-D.
3. **Ký tự khoảng trắng không ngắt (`&nbsp;` / `\u00a0`):**
   - Từ câu 20 đến câu 24, mã HTML của Tech12h sử dụng `Câu&nbsp;21:&nbsp;` thay vì khoảng trắng thông thường. Regex `\s+` không xử lý triệt để dẫn tới việc các câu bị dính liền vào nhau.
4. **Cơ chế đánh dấu đáp án bằng thẻ `<h6>`:**
   - Tech12h không dùng class `.dung` hay thuộc tính `data-correct`.
   - Phân tích file JavaScript của trang `js_rQiIaisqxlUB-QiSQLp5m-Iuozq-55pdckh4RZfoNtg.js` cho thấy đoạn code kích hoạt khi nhấn nút "Xem đáp án":
     ```javascript
     jQuery('.kqua').click(function() {
         jQuery('.accordion-detail h6').css({"color": "green", "font-weight": "bold"});
         ...
         jQuery('.kqua').text('... Dòng màu xanh ở trên là đáp án');
     });
     ```
     Như vậy, trong DOM tĩnh, phương án đúng đã được tác giả bọc sẵn trong thẻ `<h6>...</h6>`. Các phương án sai là text thuần trong `<li>`.
5. **Lỗi thế chỗ ảnh trong phương án lựa chọn (`options_latex`):**
   - Trong `WebScraperService._convert_raw_questions()`, mã nguồn cũ chỉ thay thế `[IMG:...]` trong `prompt_latex` và `sol_latex`, bỏ quên `options_latex`.
   - Điều này dẫn tới câu hỏi có hình ảnh ở phương án (như Câu 2 phương án C) bị sót mã `[IMG:...]` khi xuất sang đề thi LaTeX.
6. **Lỗi macro `max width` khi biên dịch pdfLaTeX:**
   - Khi tải ảnh về, hệ thống chèn `\includegraphics[max width=0.85\linewidth]{...}`. Tuy nhiên gói `adjustbox` không được nạp trong preamble mặc định, gây lỗi fatal `Package keyval Error: max width undefined`.
   - Đã khắc phục bằng cách chuẩn hóa sang `\includegraphics[width=0.65\linewidth]{...}`.
7. **Lỗi ký tự đặc biệt trong tiêu đề đề thi:**
   - `\TieudeT{...}` không escape các ký tự `_` hoặc `%` từ tiêu đề bài học, làm sập trình biên dịch pdfLaTeX. Đã bổ sung `escape_latex_text()`.

---

## 3. L2.1 — Triển khai Tech12hAdapter

Đã tạo mới file `src/latex_question_studio/scraping/adapters/tech12h.py` và đăng ký trong `adapters/__init__.py`:

```python
class Tech12hAdapter(BaseSiteAdapter):
    @property
    def name(self) -> str:
        return "Tech12h (tech12h.com)"

    @property
    def supported_domains(self) -> list[str]:
        return ["tech12h.com"]
```

### Các tính năng chính:
- **Kiểm tra tên miền nghiêm ngặt:** Phương thức `can_handle(url)` chỉ chấp nhận host `tech12h.com` hoặc `*.tech12h.com`. Tuyệt đối từ chối `tech24.vn` và các domain lừa đảo/spoofing.
- **Cô lập vùng câu hỏi:** Hàm `_isolate_quiz_container()` trích xuất chính xác khối `<div class="block-content-body trac_nghiem">` hoặc `<div id="accordionExample">`, loại bỏ toàn bộ banner, quảng cáo, danh sách bài liên quan.
- **Trích xuất phương án & Nhận diện đáp án:**
  - Tách các thẻ `<li>` trong `<ul>`.
  - Kiểm tra sự xuất hiện của thẻ `<h6>` bên trong `<li>`.
  - Nếu đúng 1 thẻ `<h6>`: gán `correct_choice = index`.
  - Nếu không có hoặc có nhiều hơn 1 thẻ `<h6>`: gán `correct_choice = None`, bật `needs_review = True`, cảnh báo rõ ràng. Tuyệt đối không tự đoán mò `\True`.
- **Cảnh báo phương án chỉ chứa hình ảnh hoặc rỗng:** Ghi nhận và thông báo trên UI staging để giáo viên rà soát.

---

## 4. L2.2 & L2.3 — Pipeline Chuyển đổi HTML → LaTeX → Assets → Staging → Xuất đề

1. **Chuẩn hóa ký hiệu độ và chỉ số:**
   - Trong `html_to_latex.py`: Tự động chuyển `30<sup>o</sup>`, `45<sup>0</sup>`, `60<sup>°</sup>` thành `$^\circ$`.
2. **Tải và quản lý ảnh an toàn:**
   - Tải ảnh qua `SafeFetcher` với cơ chế kiểm tra SSRF, chặn IP nội bộ, kiểm tra Content-Length và MIME type.
   - Lưu trữ tại `AssetStore` với tên file theo mã băm SHA-256 để chống trùng lặp.
   - Nhúng vào câu hỏi LaTeX với đường dẫn tương đối an toàn `images/<hash>.<ext>`.
3. **Định dạng xuất đề thi chuẩn Phase K:**
   - Định dạng từng câu hỏi: `\begin{ex} ... \choice ... \loigiai{...} \end{ex}`.
   - Định dạng gói đề kiểm tra:
     ```latex
     \TieudeT{Đề trắc nghiệm KHTN 9 Bài 5}
     \PhanI
     \begin{cauhoiTN}{De01}
     ...
     \end{cauhoiTN}
     ```
   - Sinh file `.tex`, file `.pdf` qua `pdflatex`, và file `.zip` độc lập chứa toàn bộ tài nguyên ảnh và mã nguồn LaTeX.

---

## 5. L2.4 — Kết quả đối soát thực tế trên URL bắt buộc

**URL:** `https://tech12h.com/bai-hoc/trac-nghiem-khtn-9-ket-noi-bai-5-khuc-xa-anh-sang`

### Bảng đối soát 25 câu hỏi trích xuất từ dữ liệu thực tế:

| Câu | Tiêu đề | Số lựa chọn | Đáp án nhận diện | Đáp án DOM (`<h6>`) | Hình ảnh | Trạng thái |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| 1 | Câu 1 | 4 | **D** | D (`<h6>D. Góc khúc xạ luôn bằng góc tới.</h6>`) | Không | PASS |
| 2 | Câu 2 | 4 | **B** | B (`<h6>B. Hiện tượng khúc xạ ánh sáng.</h6>`) | Option C (image_354.png) | PASS |
| 3 | Câu 3 | 4 | **B** | B (`<h6>B. tia sáng bị gãy khúc tại mặt phân cách...</h6>`) | Không | PASS |
| 4 | Câu 4 | 4 | **C** | C (`<h6>C. không đổi.</h6>`) | Không | PASS |
| 5 | Câu 5 | 4 | **B** | B (`<h6>B. nằm trong mặt phẳng tới và ở bên kia pháp tuyến...</h6>`) | Không | PASS |
| 6 | Câu 6 | 4 | **B** | B (`<h6>B. lớn hơn góc tới.</h6>`) | Không | PASS |
| 7 | Câu 7 | 4 | **B** | B (`<h6>B. nhỏ hơn góc tới.</h6>`) | Không | PASS |
| 8 | Câu 8 | 4 | **D** | D (`<h6>D. góc tới bằng 0 độ thì góc khúc xạ bằng 0 độ.</h6>`) | Không | PASS |
| 9 | Câu 9 | 4 | **B** | B (`<h6>B. tia khúc xạ bị gãy khúc theo hướng ra xa pháp tuyến.</h6>`) | Không | PASS |
| 10 | Câu 10 | 4 | **C** | C (`<h6>C. Chiếu tia sáng theo phương vuông góc...</h6>`) | Không | PASS |
| 11 | Câu 11 | 4 | **A** | A (`<h6>A. Tia khúc xạ nằm trong mặt phẳng tới.</h6>`) | Không | PASS |
| 12 | Câu 12 | 4 | **A** | A (`<h6>A. tỉ số giữa sin của góc tới và sin của góc khúc xạ...</h6>`) | Không | PASS |
| 13 | Câu 13 | 4 | **D** | D (`<h6>D. góc khúc xạ r tăng.</h6>`) | Không | PASS |
| 14 | Câu 14 | 4 | **A** | A (`<h6>A. khúc xạ.</h6>`) | Không | PASS |
| 15 | Câu 15 | 4 | **B** | B (`<h6>B. 41 độ.</h6>`) | Không | PASS |
| 16 | Câu 16 | 4 | **B** | B (`<h6>B. tia sáng bị gãy khúc khi truyền qua mặt phân cách...</h6>`) | Không | PASS |
| 17 | Câu 17 | 4 | **B** | B (`<h6>B. góc khúc xạ nhỏ hơn góc tới.</h6>`) | Không | PASS |
| 18 | Câu 18 | 4 | **B** | B (`<h6>B. $48^\circ 35'$.</h6>`) | Không | PASS |
| 19 | Câu 19 | 4 | **D** | D (`<h6>D. Cả A, B và C.</h6>`) | Không | PASS |
| 20 | Câu 20 | 4 | **A** | A (`<h6>A. hiện tượng khúc xạ ánh sáng.</h6>`) | Không | PASS |
| 21 | Câu 21 | 4 | **C** | C (`<h6>C. Chiết suất của môi trường tới lớn hơn môi trường khúc xạ.</h6>`) | Không | PASS |
| 22 | Câu 22 | 4 | **D** | D (`<h6>D. Đũa uốn cong tại mặt nước.</h6>`) | Không | PASS |
| 23 | Câu 23 | 4 | **B** | B (`<h6>B. lớn hơn góc tới.</h6>`) | Không | PASS |
| 24 | Câu 24 | 4 | **B** | B (`<h6>B. 1,5.</h6>`) | Prompt (image_355.png) | PASS |
| 25 | Câu 25 | 4 | **A** | A (`<h6>A. tia sáng đi từ môi trường chiết quang kém sang môi trường chiết quang hơn.</h6>`) | Không | PASS |

- **Tổng số câu hỏi trích xuất thành công:** 25/25 câu (100%).
- **Số câu có đáp án được xác thực qua DOM:** 25/25 câu (100%).
- **Số hình ảnh tải về và nhúng hợp lệ:** 2 hình ảnh (Câu 2 và Câu 24).
- **Kết quả biên dịch pdfLaTeX:** PASS (Tạo ra file PDF nhiều trang hoàn chỉnh, không có cảnh báo nghiêm trọng).

---

## 6. Kiểm thử tự động & Đóng gói sản phẩm

### 6.1. Bộ test chuyên biệt Phase L.2 (`tests/test_phase_l2_tech12h.py`)
- `test_tech12h_domain_matching_and_anti_spoofing`: **PASSED**
- `test_tech12h_extraction_25_questions_structure`: **PASSED**
- `test_tech12h_guardrails_for_ambiguous_and_missing_answers`: **PASSED**
- `test_tech12h_adapter_status_and_security_blocking`: **PASSED**
- `test_tech12h_pdflatex_compilation_and_export`: **PASSED**
- `test_tech12h_live_url_smoke`: **PASSED** (chạy trực tiếp trên mạng tới tech12h.com).

### 6.2. Kiểm thử hồi quy toàn bộ hệ thống
- **Tổng số tests chạy:** 386 passed (100% PASS trên Windows, thời gian chạy: 803.50s / 13 phút 23 giây).
- **Hồi quy:** Toàn bộ các bài kiểm thử Phase K (multivariant exam export), Phase L (staging/web import), Phase L.1 (anti-spoofing/Generic/Tech24) và Phase L.2 (Tech12h) đều vượt qua, không phát sinh lỗi hồi quy.

### 6.3. Đóng gói và xác thực Windows Executable Bundle
- Đã rebuild gói PyInstaller `dist/0.5.3/LaTeXQuestionStudio` chứa đầy đủ bytecode mới của module `latex_question_studio.scraping.adapters.tech12h`.
- Chạy `scripts/verify_ui_package.py`:
  - `integrity`: ok
  - `schema`: 19
  - `taxonomy_nodes`: 641
  - `pe_subsystem`: 2 (windowed application, không hiện cửa sổ console)
  - `all_modules_current`: **true** (55/55 modules)
  - `source_modules_not_bundled`: [] (không còn module nào bị thiếu)
  - `exe_icon_current`: true (10 kích thước icon đầy đủ)
  - `application_icon_current`: true

---

## 7. Kết luận & Cam kết tuân thủ

1. **Không dùng HTML mẫu giả định:** Đã đối soát và xác thực 100% trên dữ liệu mạng thực tế được phép truy cập từ URL `https://tech12h.com/bai-hoc/trac-nghiem-khtn-9-ket-noi-bai-5-khuc-xa-anh-sang`.
2. **Không vi phạm bản quyền bài viết:** Không lưu trữ toàn bộ văn bản trang web có bản quyền vào git repository.
3. **Bảo tồn toàn vẹn kiến trúc:** Không phá vỡ CSDL schema v19, không tự ý gán `\True` khi thiếu tín hiệu tin cậy, và giữ nguyên vẹn luồng biên tập duyệt đề của giáo viên trước khi nhập kho.
4. **Git Commit:**
   - Commit triển khai: `5d6f31c` (`feat(phase-l2): implement Tech12hAdapter and fix option image export pipeline`)
   - Báo cáo hoàn thành: `docs/PHASE_L2_TECH12H_REPORT.md`
