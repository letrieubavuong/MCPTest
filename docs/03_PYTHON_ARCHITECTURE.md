# Kiến trúc Python

C# WPF code-behind/static collections là chứng cứ nghiệp vụ; không port nguyên cấu trúc. Python 3.12+, PySide6, SQLite, PDF rendering là lựa chọn theo master plan.

```text
src/latex_question_studio/
  app/          bootstrap/config/logging
  domain/       Question và invariants, không Qt/SQL
  application/  use cases, inject repository/services
  persistence/  SQLite, migrations, repositories, FTS
  ui/           PySide6 shell/models/editor/docks
  parsing/      scanner/adapter/diagnostics (Phase 03)
  assets/       resolver/hash/store (Phase 03+)
  preview/      compiler/renderer/cache (Phase 05)
  jobs/         cancellation/queue/events (khi cần)
```

Phase 01 dùng sqlite3 chuẩn và migration có kiểm soát; chưa cần ORM. QPlainTextEdit là baseline editor tương lai; QScintilla cần review license/đóng gói. Runtime đã kiểm tra Python 3.14.6 và PySide6 6.11.1; dependency test trong pyproject.

## Parser
Scanner nhận command/comment/escape/brace/environment stack, trả offset vào nguyên văn. Adapter đọc nhóm bắt buộc/tùy chọn của choice/TF/shortans/loigiai; ex/vidu variants giữ tên gốc. hdan là alias adapter, không replace toàn file. Macro lạ giữ opaque; không giả định giải TeX expansion tổng quát. Mỗi vùng nguồn đều có parsed/error/explicitly-ignored và diagnostic file/line/column; nguồn gốc bất biến.

## Jobs và preview
QThreadPool cho scan/hash; writer riêng; QProcess cho pdfLaTeX với argv độc lập, no-shell-escape mặc định, temp workdir/timeout/cancel. UI không compile đồng bộ. Result mang question/revision/generation, loại kết quả lỗi thời. Cache hash source+preamble+class/style/assets+engine version/config, missing assets phải báo lỗi. Render PyMuPDF; atomic output và giới hạn LRU. Standalone chỉ sau kiểm thử, fallback full document cần corpus. Thiếu MAPClass/ex_test/preamble nên hiện chưa xác minh biên dịch.

## Đề và dedup
Sampling không hoàn lại, kiểm tra quota và candidate trùng giữa ô ma trận. Lưu seed/revision/permutation. Xáo nhóm AST giữ True, opaque không xáo phương án. Exact normalization giữ số/công thức/đáp án, có algorithm version. Near dedup chỉ gợi ý review.

## Kiểm thử
Unit parser offsets/comment/nested/escape/malformed và answer permutation; repository transaction/FTS/migration restore; Qt tab dirty/worker cancellation/stale preview/layout; TeX corpus với dependency thật. Phase 01 có 14 tests hạ tầng/Qt, chưa chạy parser/TeX tests chưa được viết. Thiếu dependency là skipped/blocked có báo cáo, không pass giả.
