# MCPTest — BÁO CÁO BASELINE VÀ TRUY VẾT PHASE L.1
**Thời gian thiết lập:** 2026-10-14  
**Nhánh:** `main`  
**HEAD SHA ban đầu:** `ce45cc137da04512429c159bb004d480c628985d`  
**Môi trường:**
- Hệ điều hành: Windows 11 (win32)
- Python: 3.14.6
- Qt / PySide6: 6.11.2 (runtime & compiled)
- TeX Engine: pdfTeX 3.141592653-2.6-1.40.29 (TeX Live 2026/W32TeX)
- Cơ sở dữ liệu: SQLite schema v19 (`analysis_version=19`)
- Tổng số test hiện tại: 304 test cases trên 60 test files (100% PASS sau khi căn chỉnh index dashboard và xử lý ảnh solution trong `parsing/latex.py`)

---

## 1. Traceability Matrix (Yêu cầu → Module → Test → Kết quả)

| Hạng mục | Yêu cầu kỹ thuật | Module mã nguồn | Test suite | Trạng thái Baseline |
| :--- | :--- | :--- | :--- | :--- |
| **L0: Baseline** | Ghi nhận môi trường, HEAD SHA, chạy regression toàn bộ test suite, phân loại lỗi | Repository MCPTest | `tests/test_*.py` (304 tests) | **PASSED (304/304)** |
| **L1: LaTeX Converter** | Viết lại converter HTML/MathJax/KaTeX/MathML sang pdfLaTeX có trạng thái text/math, escape ký tự đặc biệt, phân biệt `<sup>/<sub>`, bảo mật macro, corpus $\ge 60$ ca | `src/latex_question_studio/scraping/html_to_latex.py` | `tests/test_phase_l1_latex_converter.py`, `tests/test_phase_l_scraper.py` | Chưa triển khai L.1 (bản cũ dính lỗi macro ngoài math mode) |
| **L2: Web Adapters** | Audit & hardening VietJack, Tech24, Loigiaihay, trả về trạng thái rõ ràng (`supported`, `generic_fallback`, `blocked`, `parse_failed`, `partial`, `needs_review`), lazy loading (`data-src`, `srcset`), chống SSRF, cấm auto-verify khi thiếu ảnh | `src/latex_question_studio/scraping/adapters/` | `tests/test_phase_l1_adapters_real.py` | Cần bổ sung status enum, lazy image extraction, fixture thật |
| **L3: Deduplication** | Inverted index candidate generation cho 10k/50k câu (thay $O(N^2)$), bộ dữ liệu có nhãn $\ge 300$ cặp, không nhầm hoán vị `\choiceTF`, an toàn dữ liệu | `src/latex_question_studio/application/dedup.py` | `tests/test_phase_l1_dedup_dataset.py`, `tests/test_phase_l_dedup.py` | Cần blocking/index, dataset 300+ cặp |
| **L4: Staging & Phase K** | Kiểm soát UI staging, không cho duyệt hàng loạt câu thiếu ảnh/lỗi TeX, kiểm tra hợp đồng 4 phần Phase K khi xuất từ web import | `src/latex_question_studio/ui/pages/web_scraper_page.py`, `application/web_import.py` | `tests/test_phase_k5_export_e2e.py`, `tests/test_phase_l_ui.py` | Cần chặn auto-verify câu lỗi, gắn cảnh báo |
| **L5: Regression & EXE** | Chạy toàn bộ pytest suite, kiểm thử Windows EXE, stress test tắt ứng dụng an toàn, xuất báo cáo | Toàn bộ codebase & `release/` | Pytest toàn dự án, CLI EXE smoke test | Sẽ chạy nghiệm thu cuối |

---

## 2. Nhật ký khắc phục lỗi nền (Baseline Fixes)
1. **Lỗi `solution.png` trong xuất đề học sinh / giáo viên (`parsing/latex.py`):**
   - *Nguyên nhân:* Commit trước đó đã bỏ qua các lệnh nằm trong span lời giải (`solution_spans`) để tránh nhầm macro đáp án (`\choice`), nhưng đặt lệnh `continue` trước khi nhận dạng `\includegraphics`, dẫn tới ảnh trong `\loigiai` không được lưu vào `item.assets` và bảng `question_assets`.
   - *Khắc phục:* Tách lệnh bóc tách `\includegraphics` lên trước lệnh kiểm tra `solution_spans`. Nhờ đó mọi hình ảnh (cả thân bài và lời giải) đều được lập chỉ mục đầy đủ, đáp ứng trọn vẹn hợp đồng an toàn đề thi học sinh của Phase B.
2. **Lỗi index Dashboard (`tests/test_dashboard.py`):**
   - *Nguyên nhân:* Khi Phase L thêm 2 tab "Câu hỏi trùng" và "Thu thập từ Web", index của Dashboard trong `pages` chuyển từ 5 sang 7. Test cũ gán cứng `== 5`.
   - *Khắc phục:* So sánh động với `window.pages.indexOf(window.dashboard_page)` đảm bảo tương thích mọi cấu hình tab.
