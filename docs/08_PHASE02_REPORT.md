# Phase 02 — VS Code shell

Hoàn thành Activity Bar, Explorer, bảng Model/View phân trang 100 câu, tab source, preview/log docks, menu/phím tắt, dark/light và workspace JSON atomic. Dirty tab Lưu/Bỏ/Hủy; layout và tab khôi phục theo ID. Không có import/compile trong phase này.

Thay đổi: ui/main_window.py, tests/test_shell.py. Kiến trúc Qt Model/View + repository inject, không SQL trong UI. Kiểm thử: 15 passed, gồm mở trùng tab, dirty cancel, save/revision, reopen tab/theme. Hạn chế: tree phân loại và preview PDF được bổ sung trong phase tương ứng. Không commit/push.
