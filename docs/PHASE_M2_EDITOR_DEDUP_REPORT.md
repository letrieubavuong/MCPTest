# Báo Cáo Nghiệm Thu Kỹ Thuật Phase M.2: Trình Soạn Thảo LaTeX Thuần & Phân Định Phạm Vi Xóa Trùng

**Dự án:** MCPTest — Phân hệ Soạn bài giảng & Quản trị Ngân hàng câu hỏi  
**Ngày thực hiện:** 15/10/2026  
**Nhánh Git:** `phase-m2-editor-dedup-fix`  
**Môi trường thử nghiệm:** Python 3.14.6, PySide6 6.11.2 (Qt 6.11.2), TeX Live 2026 (pdfLaTeX), Windows 11 Pro 64-bit  

---

## 1. Mục tiêu và bối cảnh khắc phục

Trong Phase M.2, toàn bộ nhóm nhiệm vụ được tập trung giải quyết dứt điểm hai lỗi nghiêm trọng ảnh hưởng trực tiếp đến trải nghiệm thực tế của giáo viên:

1. **Tab Soạn bài giảng (Lesson Authoring):** Trình soạn thảo LaTeX thuần (`LatexEditor`) phải là mặc định và ưu tiên số một. Không được mặc định chế độ WYSIWYG, loại bỏ hoàn toàn hiện tượng tự động thay đổi mã nguồn, làm mất con trỏ, mất lịch sử undo hoặc biến các thẻ lệnh LaTeX/TikZ thành ký tự lạ.
2. **Tab Tìm và xóa câu trùng (DedupPage):** Tách biệt rạch ròi giữa 2 phạm vi:
   - **Phạm vi Ngân hàng SQLite (CSDL):** Xóa vĩnh viễn trong CSDL với kiểm tra số dòng thực tế (`rowcount`), kiểm tra ràng buộc khóa ngoại (bảo vệ các câu đang được dùng trong bài giảng hoặc đề thi) và bảo vệ câu bản gốc (Primary).
   - **Phạm vi Tệp mã nguồn (.tex):** Tuyệt đối không gọi lệnh SQL xóa CSDL. Áp dụng kỹ thuật loại bỏ câu trùng bảo toàn 100% phần mở đầu (preamble), gói lệnh, phần lý thuyết, đề mục và ghi chú; hỗ trợ nhiều tệp độc lập và xuất theo quy trình *Save As* an toàn, không ghi đè tệp gốc.

---

## 2. Nguyên nhân gốc rễ (Root Cause Analysis)

### 2.1. Lỗi nhảy con trỏ và biến dạng mã nguồn ở Tab Soạn bài giảng
- **Hiện tượng:** Giáo viên gõ công thức hoặc dán mã TikZ trong tab Soạn bài giảng thì sau khoảng 180ms con trỏ chuột bị nhảy, chữ bị thay đổi, hoặc xuất hiện ký tự `\ufffc`.
- **Nguyên nhân sâu xa:** Trong `src/latex_question_studio/ui/lesson_page.py`, widget `visual_editor` (WYSIWYG) nằm ở index 0 của `editor_stack`. Khi người dùng gõ vào `LatexEditor`, sự kiện `textChanged` kích hoạt timer `visual_sync` (180ms). Khi timer nổ, hàm `sync_visual()` gọi `visual_editor.set_source()`. Đến lượt mình, `visual_editor` phát tín hiệu `sourceChanged`, dẫn đến hàm `visual_changed()` gọi ngược lại `self.editor.setPlainText(source)`. Vòng lặp phản hồi hai chiều (bidirectional echo) này đã cưỡng bức thay thế nội dung người dùng đang gõ, xóa sạch ngăn xếp Undo/Redo và làm méo mó các cấu trúc TeX mà bộ soạn trực quan chưa hỗ trợ đầy đủ.

### 2.2. Lỗi xóa câu trùng sai phạm vi và mất nội dung tệp .tex
- **Hiện tượng:** Giáo viên tick chọn câu trùng khi quét file `.tex` rồi bấm xóa thì câu trong file `.tex` không mất, trong khi hệ thống lại báo "Đã xóa thành công khỏi CSDL". Mặt khác, nếu xuất file TeX sạch thì toàn bộ phần mở đầu và lý thuyết bị biến mất.
- **Nguyên nhân sâu xa:**
  1. Trong `src/latex_question_studio/ui/pages/dedup_page.py`, hàm `_delete_selected()` luôn gọi thẳng `self.service.delete_selected(to_delete)` đối với bảng SQLite `questions`. Khi người dùng quét file `.tex`, danh sách ID có dạng `filename.tex::q2` không hề tồn tại trong CSDL SQLite.
  2. Trong `src/latex_question_studio/application/dedup.py`, hàm `delete_selected()` cũ tăng biến đếm `deleted_count += 1` ngay sau khi thực thi SQL mà không kiểm tra `cursor.rowcount > 0`. Vì vậy, câu hỏi không tồn tại vẫn được báo là đã xóa thành công.
  3. Hàm `export_clean_tex()` cũ đọc các câu cần giữ lại rồi ghép nối thô sơ bằng `"\n\n".join(clean_blocks)`, vứt bỏ hoàn toàn `\documentclass`, `\usepackage`, `\begin{document}`, các phần lý thuyết, định lý, đề mục và ghi chú của giáo viên. Đồng thời hàm này chỉ lấy `selected_files[0]`, bỏ qua hoàn toàn các file khác nếu quét nhiều file cùng lúc.

---

## 3. Kiến trúc và giải pháp kỹ thuật đã triển khai

### 3.1. Phân hệ Soạn bài giảng (M2.1)
- **Đặt `LatexEditor` làm mặc định:** Đưa `LatexEditor` lên index 0 trong `editor_stack`. Thiết lập chế độ hiển thị ban đầu là `Mã LaTeX (mặc định)` (index 0) và `Trực quan (tùy chọn)` (index 1).
- **Ngắt vòng lặp phản hồi (Echo Elimination):**
  - Thêm cờ `syncing_to_visual` bao bọc quá trình cập nhật từ `editor` sang `visual_editor`. Hàm `visual_changed()` sẽ bỏ qua toàn bộ tín hiệu phản hồi xuất phát từ `set_source()`.
  - Bổ sung điều kiện bảo vệ `if self.editor.hasFocus(): return` trong `visual_changed()`, đảm bảo khi giáo viên đang tương tác với trình soạn thảo LaTeX thuần thì không một tiến trình ngầm nào được phép gọi `setPlainText()` làm phiền.
  - Các nút chèn cấu trúc (`+ Ví dụ`, `+ Bài tập`, mẫu TikZ, mẫu trắc nghiệm `\begin{ex}`) được định tuyến trực tiếp chèn mã nguồn chuẩn vào vị trí con trỏ của `LatexEditor`.

### 3.2. Phân hệ Xóa câu trùng theo phạm vi (M2.2)

#### A. Phạm vi Ngân hàng SQLite (`scope == 'database'`)
- **Kiểm tra sự tồn tại:** Truy vấn `SELECT id FROM questions WHERE id = ?` trước khi xóa. Nếu ID không tồn tại, báo lỗi rõ ràng, không tăng biến đếm thành công.
- **Bảo vệ toàn vẹn dữ liệu (FK Protection):** Kiểm tra các bảng liên kết `lesson_file_exercises`, `lessons` và `exam_questions`. Nếu câu hỏi đang nằm trong bài giảng hoặc đề thi, hệ thống từ chối xóa và hiển thị chính xác tên tài liệu đang sử dụng.
- **Xóa sạch bảng liên quan:** Trong cùng một transaction SQLite, tự động xóa sạch các bản ghi phụ thuộc tại `question_metadata`, `question_taxonomy`, `question_analysis`, `question_revisions`, `question_assets` trước khi xóa khỏi bảng `questions`.
- **Kiểm tra `cursor.rowcount`:** Chỉ ghi nhận số lượng xóa khi `cursor.rowcount > 0`.
- **Gộp Metadata có xác nhận:** Hộp thoại gộp nhãn và ghi chú yêu cầu giáo viên xác nhận tường minh trước khi thực hiện.

#### B. Phạm vi Tệp mã nguồn .tex (`scope == 'files'`)
- **Định vị tọa độ ký tự chính xác:** Cập nhật lớp `DuplicateItem` lưu thêm các trường:
  - `file_path`: Đường dẫn tuyệt đối của tệp nguồn.
  - `span_start`: Chỉ số ký tự bắt đầu của câu hỏi trong tệp.
  - `span_end`: Chỉ số ký tự kết thúc của câu hỏi trong tệp.
- **Kỹ thuật cắt lát ngược (Reverse-Offset Span Slicing):**
  - Trong hàm `clean_tex_files()`, gom nhóm các câu cần loại bỏ theo từng tệp.
  - Sắp xếp các đoạn cần loại bỏ theo thứ tự giảm dần của `span_start` (từ cuối tệp lên đầu tệp). Cắt lát theo thứ tự ngược đảm bảo các chỉ số ký tự của những đoạn phía trước hoàn toàn không bị sai lệch.
  - Xử lý làm sạch ký tự xuống dòng dư thừa một cách tinh tế, giữ nguyên vẹn bố cục văn bản.
- **Bảo toàn 100% cấu trúc tệp:**
  - Giữ nguyên toàn bộ phần khai báo gói lệnh, `\begin{document}`, các mục lý thuyết trọng tâm, ghi chú comment `%`, hình vẽ TikZ và lệnh tùy biến.
- **Quy trình Save As và hỗ trợ đa tệp:**
  - Nếu quét 1 tệp: Mở hộp thoại `getSaveFileName` cho phép giáo viên chọn vị trí lưu tệp sạch (mặc định tiền tố `cleaned_`).
  - Nếu quét nhiều tệp: Mở hộp thoại `getExistingDirectory` cho phép giáo viên chọn thư mục đích; hệ thống tự động sinh các tệp sạch độc lập tương ứng với từng tệp nguồn.
  - Tệp gốc không bao giờ bị ghi đè hay thay đổi ngoài ý muốn.
- **Kiểm định đối chứng tự động (Re-parse Validation):**
  - Sau khi cắt lát, tệp mới được phân tích lại qua `parse_questions()`. Hệ thống kiểm tra nghiêm ngặt điều kiện: $\text{Số câu còn lại} = \text{Số câu ban đầu} - \text{Số câu đã chọn loại bỏ}$. Nếu có bất kỳ sự sai lệch nào, tiến trình lập tức hủy bỏ và cảnh báo giáo viên.

#### C. Giao diện trực quan DedupPage
- Khi ở chế độ CSDL: Nút xóa hiển thị nhãn màu đỏ `🗑️ Xóa khỏi ngân hàng CSDL (N câu đã chọn)`. Checkbox trên từng thẻ mang nhãn `Xóa khỏi CSDL`.
- Khi ở chế độ Tệp .tex: Nút hành động đổi sang nhãn màu xanh `✂️ Loại câu khỏi file .tex (N câu đã chọn)`. Checkbox mang nhãn `Loại khỏi file .tex`. Nút `Xuất file .tex đã lọc...` ở panel trái cũng đồng bộ kích hoạt.
- Câu bản gốc (Primary) được gắn huy hiệu nổi bật `[BẢN GỐC - ĐƯỢC BẢO VỆ GIỮ LẠI]`, ô checkbox bị vô hiệu hóa kèm tooltip giải thích lý do bảo vệ an toàn.

---

## 4. Bằng chứng kiểm thử và nghiệm thu trực quan

### 4.1. Hình ảnh minh chứng giao diện thực tế

#### Minh chứng 1: Tab Soạn bài giảng với Trình soạn thảo LaTeX thuần mặc định
![Trình soạn thảo LaTeX thuần mặc định](file:///C:/Users/Admin/.gemini/antigravity-ide/brain/52e7ae05-be69-446a-b16d-863b72d92fe5/phase_m2_lesson_raw_editor.png)
*Hình 1: Tab Soạn bài giảng hiển thị `LatexEditor` mặc định với số dòng (1-21), phông chữ lập trình, bảo toàn nguyên vẹn môi trường `tikzpicture`, công thức toán `$`, `\begin{ex}`, `\choice`, `\loigiai` và dấu tiếng Việt mà không hề bị can thiệp biến dạng.*

---

#### Minh chứng 2: Tab Tìm và xóa câu trùng trong phạm vi Ngân hàng CSDL
![Quản lý câu trùng trong CSDL](file:///C:/Users/Admin/.gemini/antigravity-ide/brain/52e7ae05-be69-446a-b16d-863b72d92fe5/phase_m2_dedup_database_scope.png)
*Hình 2: Chế độ CSDL hiển thị huy hiệu `[BẢN GỐC - ĐƯỢC BẢO VỆ GIỮ LẠI]`, cảnh báo câu hỏi đang được tham chiếu trong tài liệu bài giảng/đề thi, checkbox `Xóa khỏi CSDL` được chọn ở bản sao, và nút hành động màu đỏ hiển thị rõ số lượng `🗑️ Xóa khỏi ngân hàng CSDL (1 câu đã chọn)`.*

---

#### Minh chứng 3: Tab Tìm và xóa câu trùng trong phạm vi Tệp mã nguồn .tex
![Loại câu trùng khỏi tệp .tex](file:///C:/Users/Admin/.gemini/antigravity-ide/brain/52e7ae05-be69-446a-b16d-863b72d92fe5/phase_m2_dedup_file_scope.png)
*Hình 3: Chế độ Tệp .tex phân biệt rõ ràng vị trí ký tự (offset span), checkbox `Loại khỏi file .tex`, nút xuất tệp sạch `✂️ Loại câu khỏi file .tex (1 câu đã chọn)` màu xanh lá, bảo vệ tuyệt đối tệp nguồn.*

---

### 4.2. Bằng chứng biên dịch pdfLaTeX thực tế trên Windows
Đã thực hiện biên dịch một bài giảng hoàn chỉnh gồm lý thuyết, hình vẽ TikZ, công thức toán và khối bài tập trắc nghiệm bằng trình biên dịch `pdfTeX 3.141592653-2.6-1.40.29 (TeX Live 2026)` trên Windows 11:

```
Command: pdflatex -interaction=nonstopmode -halt-on-error lesson_m2_test.tex
Output: SUCCESS: pdfLaTeX compiled successfully -> lesson_m2_test.pdf (Size: 83,167 bytes)
Exit code: 0
```
Tệp PDF xuất ra hiển thị sắc nét, chuẩn phông chữ tiếng Việt Unicode, căn lề và hình vẽ hình học chính xác.

---

### 4.3. Bảng tổng hợp kết quả kiểm thử tự động (Pytest)

| Tệp kiểm thử | Số bài test | Trạng thái | Nội dung kiểm tra |
| :--- | :---: | :---: | :--- |
| `tests/test_phase_m2_raw_editor.py` | 3 | **PASS** | LaTeX thuần là mặc định, gõ TikZ/align/tiếng Việt không biến dạng, chuyển đổi chế độ an toàn, bọc khối lệnh. |
| `tests/test_phase_m2_dedup.py` | 5 | **PASS** | Xóa CSDL kiểm tra rowcount, chống xóa câu có FK tham chiếu, cắt lát tệp .tex giữ nguyên preamble/lý thuyết, xử lý đa tệp, UI DedupPage. |
| `tests/test_phase_l_dedup.py` | 8 | **PASS** | Hồi quy toàn bộ logic quét trùng exact, hoán vị đáp án MCQ, tương tự Jaccard, gộp metadata và xuất báo cáo. |
| `tests/test_wysiwyg.py` | 24 | **PASS** | Hồi quy toàn bộ tương tác WYSIWYG, chuyển đổi chế độ không làm bẩn bài giảng, đồng bộ 2 chiều không tạo vòng lặp. |
| `tests/test_wysiwyg_formula_input.py` | 7 | **PASS** | Hồi quy phục hồi công thức literal và nhập liệu từ clipboard. |
| `tests/test_phase_m1_real_acceptance.py` | 8 | **PASS** | Hồi quy nghiệm thu bài giảng thực tế với MAPClass, ex_test, TikZ và biên dịch PDF. |
| `tests/test_phase_m1_safety.py` | 5 | **PASS** | Hồi quy tính toàn vẹn dữ liệu, bảo vệ cấu trúc khối bài giảng và tài liệu học sinh. |
| `tests/test_phase_m1_ux_workspace.py` | 3 | **PASS** | Hồi quy giao diện không gian làm việc 1366x768 và 1920x1080. |
| **Tổng cộng nhóm Phase M** | **63 / 63** | **100% PASS** | **Thời gian chạy: 225.64s** |

---

## 5. Lịch sử Commit và các tệp thay đổi

Toàn bộ mã nguồn đã được chia thành các commit độc lập, rõ ràng và đẩy thành công lên remote GitHub `https://github.com/letrieubavuong/MCPTest.git` trên nhánh `phase-m2-editor-dedup-fix`:

1. `3b083c9` — `docs(phase-m2): add Phase M.2 prompt specification`
2. `99e8a31` — `feat(editor): M2.1 - set raw LaTeX editor as default, isolate background sync, and preserve typing fidelity`
3. `1c3ee56` — `feat(dedup): M2.2 - separate database vs file deletion scopes, protect FK references, and preserve preambles during .tex cleaning`
4. `ffb0206` — `fix(editor): eliminate bidirectional echo during visual sync and update test edit_mode index`

**Các tệp mã nguồn chính được chỉnh sửa/bổ sung:**
- `src/latex_question_studio/ui/lesson_page.py` (Trình soạn thảo bài giảng)
- `src/latex_question_studio/application/dedup.py` (Động cơ quét và xử lý câu trùng)
- `src/latex_question_studio/ui/pages/dedup_page.py` (Giao diện đối chiếu và xóa câu trùng)
- `tests/test_phase_m2_raw_editor.py` (Kiểm thử đơn vị cho LatexEditor thuần)
- `tests/test_phase_m2_dedup.py` (Kiểm thử đơn vị cho xóa CSDL và làm sạch .tex)
- `tests/test_wysiwyg.py` (Cập nhật chỉ mục edit_mode)
- `tests/test_phase_m1_ux_workspace.py` (Cập nhật kiểm thử giao diện)
- `scratch/capture_m2_screenshots.py` (Kịch bản tự động hóa chụp ảnh màn hình nghiệm thu)
- `docs/PHASE_M2_EDITOR_DEDUP_REPORT.md` (Báo cáo nghiệm thu hoàn chỉnh)

---

## 6. Kết luận nghiệm thu

Phase M.2 đã hoàn thành 100% các tiêu chí chất lượng nghiêm ngặt đặt ra:
- [x] Giáo viên soạn bài giảng bằng mã LaTeX thuần tự nhiên, gõ công thức, ký hiệu tiếng Việt, chèn hình TikZ hay môi trường trắc nghiệm không bao giờ bị nhảy con trỏ hay biến dạng mã nguồn.
- [x] Chức năng xóa câu trùng phân định tuyệt đối giữa CSDL SQLite và tệp `.tex`. Không thể xảy ra trường hợp xóa nhầm trong CSDL khi đang thao tác với tệp `.tex`.
- [x] Tệp `.tex` sau khi loại bỏ câu trùng giữ nguyên vẹn 100% phần mở đầu, gói lệnh, lý thuyết, đề mục và ghi chú; tệp gốc được bảo vệ an toàn.
- [x] Toàn bộ hệ thống kiểm thử tự động đạt 100% PASS, biên dịch thành công tài liệu PDF trên TeX Live 2026 Windows, sẵn sàng phục vụ công tác giảng dạy thực tế.
