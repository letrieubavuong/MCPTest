# Phase 07 — Đề thi

Tạo đề từ selection hoặc ma trận metadata/type/cognitive; matching giữa slot và candidate giải quyết ma trận chồng lặp, không lặp question ID, tối đa 500 câu/đề. Seed xác định thứ tự/xáo MCQ; parser group AST bảo toàn True và lưu permutation/answer/revision/source snapshot. TF giữ thứ tự và truth map; shortans giữ giá trị. Lịch sử xuất lại được. TeX đi kèm assets hash; PDF compile nền, đề học sinh ẩn True/loigiai/shortans, bản lời giải/đáp án xuất riêng.

27 tests đạt. 12 seeds được đối chiếu True với đáp án sau xáo và tái lập snapshot; ma trận chồng lặp, thiếu nguồn, manual duplicate, history và source gốc không đổi. Compile PDF thật đề học sinh không lộ lời giải SECRET, bản lời giải có lời giải, answer PDF đạt. Thay đổi migration v4, application/exams.py, ui/exam_dialog.py, main_window, compiler preamble_extra và tests/test_exams.py. Chưa nghiệm thu custom MAPClass/ex_test thiếu dependency. Không commit/push.
