# Phase 00 — Khảo sát MCPTest2020

Khảo sát ngày 09/10/2026, chỉ đọc `D:\OneDrive\B - MCPTEST 2020\MCPTest2020`. Không chạy EXE/build, không sửa/xóa/di chuyển dự án tham khảo. Tài liệu được ghi lại UTF-8 ở Phase 01 để sửa lỗi mất dấu của báo cáo trước.

## Bằng chứng và inventory
Đường dẫn dưới đây tương đối với root tham khảo. `phase00_evidence.json` lưu DDL thực tế và SHA-256 của 53 tệp nguồn/cấu hình/DB. DB được truy vấn bằng SQLite URI mode=ro. Bản kiểm tra hash cuối Phase 00: 53 tệp, 0 thay đổi. Các đề xuất mới không phải tính năng đã triển khai trong phần mềm cũ.

```text
MCPTest2020.sln
MCPLibrary/MCPLibrary.cs
MCPTest2020/
  App.xaml, MainWindow.xaml(.cs)
  Viewmodel/MainViewModel.cs, BaseViewModel.cs
  Model/QuanlyID.cs
  MCPUsercontrol/*.xaml(.cs)
  NewForm/frmEditcau.xaml(.cs)
  Properties/, ResourceXAML/, Images/
  bin/Debug/MCPDatabase.db
packages/
MCPDatabase.db                 0 byte
```

## Stack và entrypoint
MCPTest2020.sln có một project C#. MCPTest2020/MCPTest2020.csproj khai báo WPF WinExe, .NET Framework v4.6.1, tham chiếu EntityFramework 6.3.0, System.Data.SQLite 1.0.113, MaterialDesignThemes 3.2.0 và Extended.Wpf.Toolkit 4.0.1/AvalonDock. Luồng đã khảo sát dùng SQLiteCommand trực tiếp; reference EF không chứng minh có ORM thực thi. App.xaml dùng StartupUri=MainWindow.xaml. MainWindow.MainWindow gọi InitializeComponent, HideTab, đọc settings người dùng và GetHDDserial. MCPLibrary.MCPLibrary chỉ đăng ký DefaultStyleKey; csproj đã đọc không có project reference tới thư viện này.

## Bản đồ module
| File dưới MCPTest2020 | Class/method thực tế | Chức năng đã đọc |
|---|---|---|
| Viewmodel/MainViewModel.cs | LoadDSID, LoadIDTreeview, SubFolder | DanhsachID, TYPE là parent; ObservableCollection static |
| Model/QuanlyID.cs | CauTeX, HTDang | DTO STT/ID/NDID/TYPE/PATH và nhóm phân loại |
| MainWindow.xaml.cs | HideTab, Btn_*_Selected | Điều hướng tab/màn hình |
| MCPUsercontrol/UseNhapCSDL.xaml.cs | Btn_FileTeX_Click:149; Btn_Loccau_Click:292; Btn_GanID_Click:364 | Nhập ex/vidu, ID comment, ND/LG, INSERT DanhsachCH |
| MCPUsercontrol/UserQLID.xaml.cs | MoMapID_Click, ThemIDCSDL, LoadlaibangID, XoaID_Click | Nhập map TeX; thêm/xem/xóa phân loại; một số handler còn trống |
| MCPUsercontrol/UserXemCSDL.xaml.cs | LoadXemCSDL, BangHTcau_SelectionChanged, Btn_ChuyenBeamer_Click | Lọc TMC/MD/LC/EX; chuyển ND/LG và Beamer |
| NewForm/frmEditcau.xaml.cs | constructor | Hiển thị ND/LG từ static state; chưa có lưu DB trong class đã đọc |
| MCPUsercontrol/UserEditTeX.xaml.cs | Fixenumerate, Btn_Fixchoice_Click | Chèn macro và chuyển A/B/C/D bằng regex |
| MCPUsercontrol/UserDethiTeX.xaml.cs | Btn_FileTeX_Click | Đọc file, tách/đếm TN/TL; chưa có xuất đề hoàn chỉnh trong class |
| MCPUsercontrol/UserRutdeHH.xaml.cs | LoadXemCSDL, Laycaungaunhien_Click:187 | Lọc và chọn câu không lặp STT vào collection |
| MCPUsercontrol/UserMatrande.xaml.cs | Btn_Laycau_Click:96 | Thêm quota Y/B/K/G/T và cộng tổng; chưa chứng minh sinh đề hoàn chỉnh |
| MCPUsercontrol/UserTimcautrung.xaml.cs | TimTrung_Click, CalculateSimilarity, CompareStrings | Levenshtein/cặp ký tự; ngưỡng 50–100% |
| MCPUsercontrol/UserXuatBeamer.xaml.cs | Btn_LoadTeX_Click, Btn_ClipBoard_Click, Btn_TaoFrame_Click, Btn_Saochep_Click | Chuỗi frame và clipboard; luồng riêng loại True/lời giải |
| MCPUsercontrol/UserWebsite.xaml.cs | LoadWeb_Click, Lamsachcode | Đọc file và làm sạch text; không suy ra tải web từ tên màn hình |
| MCPUsercontrol/UserTimkiem.xaml.cs | constructor | Chỉ InitializeComponent, chưa có search engine |
| MCPUsercontrol/UserChinhcau, UserHienthi, UserIntro, UserQLBaigiang | constructor | Không suy diễn chức năng hoàn thiện từ tên màn hình |
| MCPUsercontrol/UserNumber.xaml.cs | CmdUp_Click, CmdDown_Click, TxtNum_TextChanged | Điều khiển số lượng |

## Dữ liệu thực tế
DB có dữ liệu: MCPTest2020/bin/Debug/MCPDatabase.db, 3.010.560 byte; integrity_check=ok. Root MCPDatabase.db 0 byte không dùng làm nguồn migration. Có 828 DanhsachID, 3.075 DanhsachCH; sqlite_sequence là bảng hệ thống. DDL đầy đủ trong manifest; DanhsachCH.ND UNIQUE, không có FK khai báo.

| Thuộc tính | Kết quả |
|---|---|
| EX | 0 ở cả 3.075 câu; không có mẫu vidu trong DB |
| LC, schema TEXT | '0': 3.010; '1': 65 |
| MD | 0:683; 1:1.429; 2:906; 3:42; 4:15 |
| SL | 0 toàn bộ; ý nghĩa chưa xác minh |
| LG không rỗng | 2.645 |
| TMC câu thiếu DanhsachID.STT | 0 |
| TYPE phân loại khác 0 thiếu cha STT | 3 |
| Level/Ten | CSDL:1, Khối:7, Môn:23, Chương:57, Bài:305, Dạng:293, Loại:142 |

Cây cũ Khối→Môn có thêm Dạng/Loại; không ép mất cấp vào cây mới. TYPE là parent theo MainViewModel.LoadIDTreeview. DanhsachID.TMC chưa rõ ý nghĩa.

Đếm literal trong ND hoặc LG: choice=3.010, True=3.015, tikzpicture=31, listEX=34; choiceTF/choiceTFt/shortans/includegraphics/loigiai/hdan=0. Cả 3.010 câu LC='0' có đúng một literal True trong ND: chưa phải kiểm chứng parser ngữ nghĩa. Lời giải lưu riêng nên không có loigiai là điều có thể xảy ra.

Mẫu: STT355 là choice với True CO_2; STT1613 có tikzpicture/shade, ball color, node distance và >=latex'; STT381 có listEX/align* và macro ct trong lời giải. Không tìm thấy .tex/.cls/.sty trong toàn cây tham khảo. MAPClass.cls, ex_test.sty, macro ct và TikZ libraries chưa có định nghĩa thực tế để nghiệm thu pdfLaTeX.

## Rủi ro từ source
- UseNhapCSDL.Btn_FileTeX_Click:182 đọc FileName dù Multiselect=true; sửa whitespace/ex*/vidu*/hdan và bỏ môi trường gốc. ND/LG không khôi phục byte TeX trước nhập.
- Btn_Loccau_Click:303–351 chỉ xử lý ID không rỗng, INSERT từng câu, catch chung báo trùng; không thấy transaction batch. Bản mới giữ hàng chờ và phân biệt lỗi.
- UserTimcautrung.LoadFiletim_Click:90 ghi đè file bằng StreamWriter(...,false); Xoacautrung và Themphantram_Click cũng ghi file. Không chạy các handler này khi audit.
- UserRutdeHH.Laycaungaunhien_Click dùng random.Next(0,Count-1), loại phần tử cuối; kiểm tra quota dùng TongY dù lọc mức khác. Cần viết lại sampling.
- UserTimcautrung.Simplify bỏ ký tự ngoài a-z, gồm số/ký hiệu toán; không dùng làm exact dedup.

## Giới hạn nghiệm thu
Đã đọc source/schema, kiểm tra integrity, counts, orphan, macro và hash. Chưa chạy app cũ, build, TeX hay migration thử. Thiếu nguồn TeX/preamble/assets/class/style, mapping 5 mức sang 4 nhận thức, ý nghĩa SL/TMC phân loại và corpus đúng/sai/trả lời ngắn. Không coi các phần chưa kiểm chứng là đã đạt.
