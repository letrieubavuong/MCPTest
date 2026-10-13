# BÁO CÁO BENCHMARK THUMBNAIL LATEX THỰC TẾ — PHASE I.3
*Dự án: MCPTest — Phân hệ Preview & Cache Thumbnail*  
*Môi trường: Windows 11 x64, Python 3.12, MiKTeX pdfLaTeX, PyMuPDF, PySide6 (Qt 6.8)*  
*Thời gian thực hiện: 2026-10-13*

---

## 1. Mục tiêu và Phương pháp luận

Khác với benchmark tổng hợp của Phase F cũ (vốn sử dụng một ảnh cố định giả lập để đo cache disk/RAM), benchmark **Phase I.3** đo đạc **toàn bộ chu trình render thực tế (Full LaTeX Pipeline)** từ mã nguồn TeX thô đến hiển thị trên giao diện người dùng.

Bộ dữ liệu kiểm thử gồm **200 câu hỏi LaTeX thực tế độc lập**, chia đều thành 8 nhóm chuyên biệt (mỗi nhóm 25 câu) đại diện đầy đủ cho ngân hàng câu hỏi THPT/THCS:
1. **Công thức toán thông thường:** Phân thức, căn thức, tích phân, giới hạn, ma trận.
2. **Câu trắc nghiệm 4 lựa chọn (`\choice`):** Môi trường trắc nghiệm chuẩn.
3. **Câu đúng / sai (`\choiceTF`):** Định dạng 4 mệnh đề a, b, c, d của Bộ GD&ĐT 2025.
4. **Câu trả lời ngắn (`\shortans`):** Điền số hoặc biểu thức.
5. **Câu có hình ảnh nhúng (`\includegraphics`):** Chèn tệp PNG/JPG từ thư mục assets.
6. **Câu có TikZ / hình học phẳng:** Đường cong, hệ trục Oxy, đồ thị hàm số, hình học không gian.
7. **Câu có bảng biểu (`tabular`, `tabularx`):** Bảng biến thiên, bảng số liệu thực nghiệm.
8. **Câu sử dụng macro MAPClass:** Các macro `\TieudeT`, `\haicot`, `\bacot`, `\boncot`, `\heva`, `\hoac`.

---

## 2. Kết quả Tổng quan

| Chỉ số | Giá trị thực tế | Đánh giá |
| :--- | :--- | :--- |
| **Tổng số câu kiểm thử** | **200 / 200 câu** | Đạt 100% mẫu quy định |
| **Số câu biên dịch thành công** | **200 câu (100.0%)** | Tỷ lệ lỗi 0% |
| **Tổng thời gian pipeline thực tế** | **538.74 giây** | ~2.69 giây / câu đầy đủ |
| **Peak RAM toàn tiến trình (Process Working Set)** | **130.18 MB** | Nằm trong ngưỡng an toàn (~130 MB) |
| **Dung lượng RAM cache ThumbnailManager** | **40.24 MB** | Kiểm soát chặt chẽ < 128 MiB |
| **Số mục lưu trữ trong RAM cache** | **101 mục** | LRU giữ cả data nén và QPixmap giải mã |

---

## 3. Chi tiết Đo lường Từng Công đoạn (Latency Breakdown)

Các công đoạn được đo đạc bằng đồng hồ độ chính xác cao (`time.perf_counter()`):

| Công đoạn | Thời gian TB (ms) | Min (ms) | Max (ms) | Ghi chú kỹ thuật |
| :--- | :--- | :--- | :--- | :--- |
| **1. Biên dịch pdfLaTeX** | **2606.58 ms** | 2365.84 ms | 4274.35 ms | Khởi chạy process MiKTeX độc lập, nạp gói tiếng Việt và TikZ |
| **2. Chuyển PDF sang ảnh (PyMuPDF)** | **29.54 ms** | 14.49 ms | 111.94 ms | Scale 1.2, auto-crop bounding box bảo toàn lề 12pt |
| **3. Mã hóa WebP (Lossless/Q92)** | **32.91 ms** | 4.67 ms | 178.36 ms | Nén ảnh chất lượng cao để lưu disk cache |
| **4. Mã hóa PNG (đối chứng)** | **12.13 ms** | 0.63 ms | 57.99 ms | Mã hóa PNG qua Qt QImage |
| **5. Đọc Cold Disk Cache** | **9.66 ms** | 4.17 ms | 28.55 ms | Đọc file `.webp` từ đĩa SSD/HDD vào bộ nhớ |
| **6. Đọc Hot RAM Cache** | **0.050 ms (50 µs)** | 0.004 ms | 0.495 ms | Truy xuất trực tiếp QPixmap đã giải mã trong RAM |

---

## 4. Hiệu năng Hiển thị Giao diện (Display Throughput)

Đo thời gian hiển thị danh sách câu hỏi khi cuộn trên giao diện (Grid Card / List View) từ trạng thái cache có sẵn:

- **Hiển thị 20 câu đầu tiên:** **39.03 ms** (~1.95 ms / câu) — Hoàn toàn mượt mà, vượt xa yêu cầu 60 FPS (16.6 ms cho mỗi frame cuộn).
- **Hiển thị 50 câu liên tiếp:** **89.76 ms** (~1.80 ms / câu).
- **Hiển thị 100 câu liên tiếp:** **180.23 ms** (~1.80 ms / câu).

*Kết luận:* Sau khi cache được tạo ở chế độ nền (worker thread), trải nghiệm duyệt ngân hàng câu hỏi trên UI thread diễn ra tức thì, không có hiện tượng giật lag khung hình.

---

## 5. So sánh Dung lượng Cache Thực tế (WebP vs PNG)

| Định dạng | Tổng dung lượng (200 câu) | Dung lượng TB / ảnh | Tỷ lệ tiết kiệm |
| :--- | :--- | :--- | :--- |
| **PNG (gốc)** | 4,848,839 bytes (~4.62 MB) | 24,244 bytes (~23.68 KB) | Gốc |
| **WebP (tối ưu)** | 3,690,688 bytes (~3.52 MB) | 18,453 bytes (~18.02 KB) | **Tiết kiệm 23.9%** |

Với ngân hàng 10,000 câu hỏi thực tế:
- Lưu trữ PNG: ~240 MB
- Lưu trữ WebP: ~180 MB (tiết kiệm ~60 MB đĩa lưu trữ, tải đĩa nhanh hơn 24%).

---

## 6. Đo lường Chi tiết theo 8 Nhóm Câu hỏi

| Nhóm câu hỏi | Số câu | Thành công | pdfLaTeX (ms) | PDF $\to$ Ảnh (ms) | WebP (ms) | Cold Disk (ms) | Hot RAM (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1. Công thức toán** | 25 | 25 (100%) | 2522.13 | 24.06 | 12.86 | 9.65 | 0.020 |
| **2. Trắc nghiệm `\choice`** | 25 | 25 (100%) | 2521.55 | 27.97 | 24.51 | 12.60 | 0.062 |
| **3. Đúng/Sai `\choiceTF`** | 25 | 25 (100%) | 2843.23 | 27.34 | 21.58 | 8.84 | 0.042 |
| **4. Ngắn `\shortans`** | 25 | 25 (100%) | 2528.32 | 29.32 | 27.89 | 7.74 | 0.025 |
| **5. Có `\includegraphics`** | 25 | 25 (100%) | 2547.90 | 33.18 | 42.96 | 9.86 | 0.049 |
| **6. TikZ Diagram** | 25 | 25 (100%) | 2543.07 | 27.76 | 37.13 | 9.93 | 0.057 |
| **7. Bảng `tabular`** | 25 | 25 (100%) | 2728.22 | 30.77 | 48.36 | 9.60 | 0.114 |
| **8. Macro MAPClass** | 25 | 25 (100%) | 2618.19 | 35.90 | 48.00 | 9.10 | 0.029 |

---

## 7. Phân tích Hiện tượng và Đánh giá

1. **Thời gian pdfLaTeX:** Thời gian biên dịch trung bình ổn định ở mức 2.5 – 2.8s/câu trên Windows (chi phí tạo process `pdflatex.exe` và nạp format `pdflatex.fmt`). Đây là đặc tính tự nhiên của engine TeX; việc chuyển sang cơ chế Background Job và Disk Cache vĩnh viễn giúp người dùng chỉ phải chịu chi phí này 1 lần duy nhất cho mỗi câu hỏi.
2. **Quản lý RAM QPixmap:** Khi duyệt 200 câu hỏi, ThumbnailManager đã tự động kích hoạt LRU 2 tầng (bỏ giữ decoded `QPixmap` của các mục cũ, chỉ giữ compressed WebP bytes trong RAM). Do đó, Peak RAM của tiến trình dừng ở 130.18 MB, không hề xảy ra tràn bộ nhớ RAM (OOM) hay rò rỉ bộ nhớ.
3. **Tương thích TeX:** 100% các cú pháp toán phổ biến, Tiếng Việt có dấu, ảnh nhúng, sơ đồ TikZ và bảng biểu đều được biên dịch thành công mà không có lỗi.
