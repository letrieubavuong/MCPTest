# Điều chỉnh được người dùng xác nhận — layout 0.1.1

Cấu trúc chính theo MCPTest C#: hai cột. Cột 1 là menu drawer điều hướng; cột 2 tải control Xem CSDL/Nhập câu hỏi/Ra đề thi/Cài đặt trong cùng cửa sổ. Dock/editor/preview là bố cục nội bộ trang CSDL. Không dùng cửa sổ riêng cho từng chức năng. Quy định này thay mô tả shell tổng thể bên dưới nếu có mâu thuẫn.

# Đặc tả UI/UX

Giao diện tiếng Việt kiểu VS Code theo master plan. WPF MainWindow.HideTab/UserControl chứng minh nhóm nghiệp vụ cũ; UI mới dùng Qt Model/View nhiều tab/dock. Ảnh Phase 00 là mockup, ảnh Phase 01 là cửa sổ skeleton chạy thật.

## Bố cục đích Phase 02
Activity Bar: Thư viện/Tìm kiếm/Nhập dữ liệu/Đề thi/Cài đặt. Explorer QTreeView lazy-load, counts, giữ Dạng/Loại. Trung tâm danh sách phân trang + editor tab. Preview dock phải/dưới resize/ẩn. Bottom Panel Parser/Biên dịch/Tác vụ; Status Bar lưu/loại/engine/count/progress. Theme tối/sáng và persist layout có version.

## Luồng
1. Nhập file/nhiều file/thư mục → scan nền/Hủy → staging mới/trùng/lỗi + vị trí → review metadata/source → commit transaction → báo ghi và chờ. Không bỏ lỗi.
2. Mở câu theo ID không trùng tab; preview theo revision hiện tại. Chuyển câu không mất source dirty và không nhận result cũ.
3. Ctrl+S tạo revision atomic; đóng dirty tab Lưu/Bỏ/Hủy. Undo editor độc lập lịch sử DB.
4. Trùng: hai câu/diff nguồn-đáp án-lời giải, score gợi ý; giữ cả hai mặc định, merge xác nhận/revision/provenance.
5. Đề: chọn tay/ma trận, quota/nguồn/thiếu; thiếu thì chặn sinh, review đề/đáp án trước export.

## Trạng thái và lỗi
Preview chưa chọn/cache/chờ/chạy/thành công/lỗi/thiếu dependency/hủy. Parser có file/dòng/cột và đi tới nguồn. Compile log ở panel, không spam dialog. DB lỗi phân biệt câu trùng. Không engine thì cấu hình và kiểm tra. Search rỗng hiển thị bộ lọc.

Ctrl+F tìm, Ctrl+H thay, Ctrl+P mở nhanh, Ctrl+Shift+P palette, Ctrl+W đóng tab, F5 preview; accessible labels/focus tiếng Việt, kiểm tra DPI 100/150/200%, contrast, cửa sổ nhỏ. Nghiệm thu Phase 02: dock/theme/layout/tab/keyboard không crash, worker không treo UI. Phase 01 mới có cửa sổ, trạng thái DB và nút kiểm tra; chưa claim shell hoàn chỉnh.
