# MCPTest — BÁO CÁO AUDIT KIẾN TRÚC & BASELINE PHASE K
**Thời điểm thực hiện:** 14/10/2026  
**Mục tiêu:** Kiểm toán định nghĩa thực tế trong `MAPClass.cls` & `ex_test.sty`, rà soát pipeline tạo đề thi hiện tại, và thiết lập bảng khác biệt (Gap Analysis) giữa hệ thống hiện có và Hợp đồng Cấu trúc Đề thi bắt buộc Phase K.

---

## 1. KẾT QUẢ AUDIT ĐỊNH NGHĨA THỰC TẾ TRONG CLASS & PACKAGE

### 1.1. Lớp văn bản `MAPClass.cls` (`docs/Class/MAPClass.cls`)
- **Tùy chọn lớp (`\DeclareOptionX`):**
  - `company`: Mặc định `BookA4`.
  - `pagesize`: Mặc định `BookA4` (hoặc `DethiA4` cho đề thi).
  - `mausac`: Mặc định `01`.
  - `tuychon`: Mặc định `HS1` (dành cho học sinh) hoặc `GV1` (dành cho giáo viên, hiển thị đáp án và lời giải).
- **Lệnh tiêu đề `\TieudeT{#1}` (Dòng 1651):**
  - Nhận 1 tham số `#1` là Tiêu đề bài thi.
  - Sử dụng biến `\subject` (ví dụ: `\def\subject{TOÁN 12}`) để hiển thị môn học.
  - Sử dụng biến `\theMade` từ counter `Made` để hiển thị số đề.
- **Các lệnh phân chia phần thi (Dòng 2816–2819):**
  - `\PhanI`: In tiêu đề *"Phần 1: CÂU HỎI TRẮC NGHIỆM. Mỗi câu học sinh chỉ chọn một phương án"*, đồng thời tự động reset `\setcounter{ex}{0}`.
  - `\PhanII`: In tiêu đề *"Phần 2: CÂU HỎI TRẮC NGHIỆM ĐÚNG SAI. Trong mỗi ý a), b), c), d) ở mỗi câu học sinh chọn đúng hoặc sai."*, đồng thời `\setcounter{ex}{0}`.
  - `\PhanIII`: In tiêu đề *"Phần 3: CÂU HỎI TRẢ LỜI NGẮN. Học sinh ghi đáp án vào ô kết quả"*, đồng thời `\setcounter{ex}{0}`.
  - `\PhanTL`: In tiêu đề *"Phần 3: CÂU HỎI TỰ LUẬN. Học sinh làm bài vào giấy"*, đồng thời `\setcounter{ex}{0}`.

### 1.2. Gói mở rộng `ex_test.sty` (`docs/Packages/ex_test.sty`)
- **Các môi trường câu hỏi (Dòng 3862–3897):**
  - `\newenvironment{cauhoiTN}[1]`: Tự động reset counter `ex` và `bt` về 0. Mở file ghi lời giải và đáp án trắc nghiệm:
    - `\Opensolutionfile{ansbook}[Loigiai/LGTN#1]`
    - `\Opensolutionfile{ans}[Loigiai/TN#1]`
  - `\newenvironment{cauhoiDS}[1]`: Tự động reset counter `ex` và `bt` về 0. Mở file ghi lời giải và đáp án Đúng/Sai:
    - `\Opensolutionfile{ansbook}[Loigiai/LGDS#1]`
    - `\Opensolutionfile{ans}[Loigiai/DS#1]`
  - `\newenvironment{cauhoiTLN}[1]`: Tự động reset counter `ex` và `bt` về 0. Mở file ghi lời giải và đáp án Trả lời ngắn:
    - `\Opensolutionfile{ansbook}[Loigiai/LGTLN#1]`
    - `\Opensolutionfile{ans}[Loigiai/TLN#1]`
  - `\newenvironment{cauhoiTL}[1]`: Tự động reset counter `ex` và `bt` về 0. Mở file ghi lời giải và đáp án Tự luận:
    - `\Opensolutionfile{ansbook}[Loigiai/LGTL#1]`
    - `\Opensolutionfile{ans}[Loigiai/TL#1]`
- **Phát hiện chí mạng (Critical Finding):**
  - Lệnh `\Opensolutionfile` cố gắng mở các tệp trong thư mục con `Loigiai/`.
  - Nếu thư mục `Loigiai/` **không tồn tại** trên đĩa trong thư mục làm việc của pdfLaTeX, trình biên dịch sẽ gặp lỗi nghiêm trọng:
    `! I can't write on file 'Loigiai/LGTNDe01.tex'.`
    `! Emergency stop.`
  - **Bắt buộc:** Mọi tiến trình biên dịch (kể cả xem trước và xuất gói ZIP) phải bảo đảm tạo sẵn thư mục `Loigiai/` trước khi gọi `pdflatex`.

---

## 2. BẢNG KHÁC BIỆT THỰC TRẠNG (GAP ANALYSIS)

| Tiêu chí | Thực trạng hiện tại (As-Is) | Hợp đồng bắt buộc Phase K (To-Be) | Trạng thái |
| :--- | :--- | :--- | :---: |
| **Cấu trúc phân phần đề thi** | Liệt kê câu hỏi liên tục trong 1 danh sách phẳng, không phân phần. | Bắt buộc chia 4 phần đúng thứ tự: `\PhanI`, `\PhanII`, `\PhanIII`, `\PhanTL`. | **Chưa đạt** (Cần làm mới Serializer) |
| **Môi trường câu hỏi** | Chỉ có `\begin{ex}...\end{ex}` đơn lẻ, không bọc môi trường phân loại. | Bọc từng nhóm câu trong `cauhoiTN{DeXX}`, `cauhoiDS{DeXX}`, `cauhoiTLN{DeXX}`, `cauhoiTL{DeXX}`. | **Chưa đạt** (Cần làm mới Serializer) |
| **Quy tắc xáo Phần I (MCQ)** | Xáo câu và xáo đáp án, nhưng bị trộn chung với các loại câu khác. | Tách riêng Phần I: xáo câu trong Phần I; xáo 4 phương án A/B/C/D bảo toàn `\True`. | **Chưa đạt** (Cần tách phân nhóm) |
| **Quy tắc xáo Phần II (TF)** | Câu hỏi TF bị trộn ngẫu nhiên với câu MCQ và tự luận. | **Chỉ xáo câu trong Phần II; tuyệt đối giữ nguyên thứ tự 4 mệnh đề a, b, c, d.** | **Chưa đạt** (Cần bảo toàn thứ tự ý) |
| **Quy tắc xáo Phần III (TLN)** | Bị trộn chung danh sách với MCQ và TF. | Chỉ xáo thứ tự câu hỏi trong Phần III. Giữ nguyên giá trị `\shortans`. | **Chưa đạt** (Cần tách phân nhóm) |
| **Quy tắc xáo Tự luận (Essay)** | Bị trộn ngẫu nhiên vị trí với các câu trắc nghiệm. | **Mặc định giữ nguyên thứ tự**, không tự ý xáo. | **Chưa đạt** (Cần giữ nguyên thứ tự) |
| **Đa mã đề (Multi-codes)** | Chỉ sinh 1 mã đề hoặc các snapshot độc lập chưa có thư mục DeXX chuẩn. | Xuất đồng thời các mã đề `De01`, `De02`, `De03`, `De04`... vào thư mục/tệp riêng với mã tương ứng. | **Cần nâng cấp** |
| **Thư mục `Loigiai/`** | Chưa tự động tạo thư mục `Loigiai/` khi biên dịch hoặc xuất đề. | Tự động tạo thư mục `Loigiai/` trong thư mục biên dịch và gói ZIP portable. | **Cần bổ sung ngay** |
| **Hiệu năng UI (Chọn thẻ)** | Gọi `sync_cards()` hủy và tạo lại toàn bộ thẻ, gây trễ ~150–350ms. | Tối ưu cập nhật trạng thái chọn thẻ tại chỗ, không rebuild toàn bộ widget. | **Cần tối ưu** |

---

## 3. KẾ HOẠCH TRIỂN KHAI THEO TỪNG GIAI ĐOẠN

1. **Phase K0 (Hoàn tất):** Audit chi tiết định nghĩa macro/class, xác định rủi ro `Loigiai/`, thiết lập baseline.
2. **Phase K1:** Chuẩn hóa domain model và AST parser nhận diện chính xác 4 loại câu hỏi (`mcq`, `true_false`, `short_answer`, `essay`).
3. **Phase K2:** Xây dựng Shuffle Engine mới tuân thủ nghiêm ngặt ma trận xáo Phase K (MCQ: xáo câu + lựa chọn; TF: chỉ xáo câu, cấm xáo mệnh đề; ShortAns: chỉ xáo câu; Essay: không xáo).
4. **Phase K3:** Cải tiến Serializer xuất chuẩn MAPClass 4 phần (`\TieudeT`, `\PhanI..IV`, `cauhoiTN/DS/TLN/TL`), tự động tạo `Loigiai/`.
5. **Phase K4:** Nâng cấp Builder UI với 4 khu vực hiển thị rõ ràng, xem trước theo mã đề, và tối ưu `sync_cards()` không block main thread.
6. **Phase K5:** Xuất gói di động đa mã đề (`De01`–`De04`), kiểm tra PDF thực tế qua pdfLaTeX, kiểm toán rò rỉ đáp án.
7. **Phase K6:** Chạy full regression test, benchmark hiệu năng, lập báo cáo nghiệm thu `docs/PHASE_K_EXAM_STRUCTURE_REPORT.md` và push GitHub.
