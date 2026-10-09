# Benchmark ngân hàng tổng hợp — 0.4.0

Ngày đo: 2026-10-09. Baseline commit `ce9dbd6aeb3a55bd98f0c0db9230fa2ea94254b9`. Không dùng hoặc sửa ngân hàng thật.

## Môi trường và phương pháp

- Windows 10 build 19045 x64; Intel Core i7-6820HQ 2,70 GHz, 4 cores/8 threads; RAM 31,8 GiB.
- Python embedded 3.14.0, SQLite 3.50.4; PySide6 6.11.1; PyMuPDF 1.28.0; pdfLaTeX TeX Live 2026. Không nâng phiên bản thư viện.
- Dữ liệu ở thư mục UUID riêng `.runtime/benchmark-*` trên workspace D:. Mỗi ngân hàng có 1k/10k/50k câu ngắn, bốn mức độ được gán tổng hợp, 1% archived, cùng môn/lớp/bài. Số đo truy vấn thực hiện trước khi nhập thêm.
- Mỗi thao tác đo một lần bằng `perf_counter`; trường median trong JSON là cùng một mẫu, không phải nhiều lần đo. Đây là số đo cục bộ, không phải SLA hoặc chứng nhận mọi ngân hàng có source/TikZ dài.
- Lượt sau cuối chạy riêng khi pytest và PyInstaller đã kết thúc. Có giữ lượt bị tải nền ảnh hưởng trong `artifacts/stabilization-after-contended.json`; không dùng nó trong bảng dưới.
- Khởi động ở đây là thời gian constructor MainWindow sau khi QApplication có sẵn, trên ngân hàng đã chạy thống kê. Không đo cold-start EXE hoặc thời gian mọi worker hoàn thành; thống kê async không còn chặn constructor.
- Import stage đọc một file chứa N câu; commit ghi thêm N câu vào ngân hàng N câu đã có. Các gợi ý trùng không tự xóa câu. Chi phí bao gồm revision, metadata, assets reference, FTS và cache phân tích mới.
- Preview đo biên dịch, cache hit, render và đổi source trong service; timer/đổi lựa chọn GUI được kiểm thử riêng.

## Trước và sau (giây)

| Thao tác | 1k trước | 1k sau | 10k trước | 10k sau | 50k trước | 50k sau |
|---|---:|---:|---:|---:|---:|---:|
| Khởi tạo MainWindow | 2.2517 | 1.3205 | 14.7642 | 0.7808 | 62.1826 | 1.5071 |
| Mở trang ngân hàng (100 câu) | 0.0034 | 0.0032 | 0.0041 | 0.0023 | 0.0030 | 0.0020 |
| Lọc cây bài học | 0.0047 | 0.0075 | 0.0598 | 0.0334 | 0.1999 | 0.1473 |
| FTS: tổng hợp 42 | 0.0032 | 0.0040 | 0.0161 | 0.0122 | 0.0542 | 0.0648 |
| Môn/lớp/mức độ | 0.0030 | 0.0049 | 0.0084 | 0.0160 | 0.0041 | 0.0697 |
| Cây và số câu subtree | 0.0240 | 0.0292 | 0.1457 | 0.1458 | 0.4280 | 0.4898 |
| Thống kê chưa có cache | 1.2677 | 0.2610 | 12.4911 | 2.8666 | 81.3282 | 18.4355 |
| Thống kê có cache | 1.1542 | 0.0173 | 12.2354 | 0.1120 | 79.7854 | 0.4998 |
| Gợi ý trùng/gần trùng | 0.1636 | 0.3216 | 1.9091 | 3.3286 | 10.5998 | 14.0514 |
| Nhập: phân tích và hàng chờ | 0.1746 | 0.2684 | 2.2439 | 2.0668 | 10.0331 | 10.6390 |
| Nhập: ghi ngân hàng | 0.4144 | 0.7840 | 7.5834 | 12.1257 | 38.0968 | 70.3021 |

## Preview (giây)

| Ngân hàng | Biên dịch source đầu | Cache hit | Render | Đổi câu chưa có cache | Quay lại câu đã có cache |
|---|---:|---:|---:|---:|---:|
| 1000 | 3.7504 | 0.0162 | 0.1928 | 2.6929 | 0.0119 |
| 10000 | 2.7237 | 0.0114 | 0.0085 | 2.6909 | 0.0132 |
| 50000 | 2.7751 | 0.0132 | 0.0099 | 2.7962 | 0.0116 |

Baseline 1k: compile 3.6224s; cache 0.0183s; render 0.1407s. Baseline không đo đổi câu hoặc preview ở 10k/50k, không điền số trước giả.

## Kết luận và giới hạn

- 50k thống kê có cache: 79.79s → 0.50s. Cache cold vẫn cần 18.44s cho ngân hàng seed SQL chưa từng được phân tích. Câu mới nhập/sửa được cập nhật cache cùng transaction.
- Không parse lại toàn ngân hàng cho mỗi lần thống kê. Thiếu cache được lấy ID một lần, source đọc theo batch 256. Metadata-only revisions không làm mất cache; source thay đổi hoặc parser version khác mới phân tích lại.
- Query plan xác nhận `ix_qt_taxonomy` cho subtree, `ix_taxonomy_parent` cho cây và `ix_analysis_normalized` cho hash. Planner vẫn có thể chọn index khác theo filter; không tuyên bố mọi expression index đều được dùng.
- CSDL hiển thị page 100, API tối đa 500. Review nhập hiển thị tối đa 200 câu mỗi trang, nhưng toàn batch vẫn được giữ; gán tất cả không bị giới hạn bởi trang đang xem.
- Thống kê/tạo đề/import/biên dịch/so trùng chạy worker. Hủy import commit rollback cả transaction; guard generation loại preview/thống kê lỗi thời. Các query trang/cây ngắn và dựng widget vẫn chạy trên UI; đây chưa phải bảo đảm mọi source cực lớn đều phản hồi tức thời.
- Phát hiện gần trùng vẫn quét ngân hàng, SequenceMatcher trên source gốc. Không đổi sang tìm gần đúng gây bỏ sót hoặc tự hợp nhất. Số đo sau không cải thiện đáng tin cậy; source dài có thể chậm hơn. Cảnh báo trong đề so các cặp được chọn, không tự loại câu khác ID.
- **Import commit chậm hơn baseline** do thêm validation cache/index/serialization. Đã tránh parse lặp từ stage bằng marker hash/version; chưa tuyên bố tối ưu thời gian ghi hàng loạt. Phần này và gần trùng còn là ưu tiên tiếp theo. Cải thiện lớn hiện nằm ở thống kê và tránh chặn UI.

## Tái lập

```powershell
& ./.runtime/python-embed/python.exe scripts/benchmark_stabilization.py after 1000 10000 50000
```

Lệnh tạo ngân hàng tổng hợp mới, không mở LOCALAPPDATA của sản phẩm. Baseline phải chạy trên checkout commit gốc riêng; không chạy mã hiện tại với nhãn before để giả số cũ. JSON đầy đủ ở `artifacts/stabilization-before.json` và `artifacts/stabilization-after.json`; release có bản sao trong `verification/`.
