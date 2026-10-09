# Phase 05 — Editor và preview

Editor QPlainTextEdit có highlighting/số dòng, tìm/thay, undo/redo, Ctrl+Space macro completion. Worker chạy pdfLaTeX process riêng, no-shell-escape/timeout/cancel, giữ log và map dòng source, render PyMuPDF. Cache hash source+preamble+assets+engine/version/flags; custom preamble hash các cls/sty/tex phụ thuộc. Result generation/question/source chống preview lỗi thời; cache được giới hạn theo dung lượng.

24 tests đạt, gồm compile thật công thức/choice/TikZ/includegraphics/tiếng Việt, render PNG, cache hit và invalidate khi asset đổi, lỗi UndefinedControlSequence có dòng nguồn, missing engine/asset/cancel/timeout. Không có MAPClass.cls hoặc ex_test.sty theo kpsewhich. Profile article tích hợp là renderer riêng, không tuyên bố thay thế hoàn toàn ex_test/MAPClass; custom preamble cần dependency thật để nghiệm thu tương thích. Chưa kiểm tra mọi macro legacy như ct.

Thay đổi preview/compiler.py, ui/editor.py, main_window, pyproject dependency PyMuPDF, tests/test_compiler.py. Không commit/push.
