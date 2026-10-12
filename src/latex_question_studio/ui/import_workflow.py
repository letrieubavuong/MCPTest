"""Compact five-step import workflow shell."""
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QToolButton, QPlainTextEdit, QProgressBar, QStackedWidget, QVBoxLayout, QHBoxLayout, QWidget, QFrame)
from latex_question_studio.ui.icons import icon


class StatsStrip(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent);layout=QHBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(6);self.values=[]
        for title,color in [('Tổng câu','blue'),('Hợp lệ','green'),('Thiếu tài nguyên','amber'),('Lỗi biên dịch','red')]:
            card=QFrame();card.setObjectName('importStat');card.setProperty('accent',color);box=QVBoxLayout(card);box.setContentsMargins(10,6,10,6);value=QLabel('0');value.setObjectName('importStatValue');box.addWidget(value);label=QLabel(title);label.setObjectName('importStatLabel');box.addWidget(label);layout.addWidget(card);self.values.append(value)
    def set_values(self,total,valid,missing,invalid):
        for value,number in zip(self.values,(total,valid,missing,invalid)):value.setText(f'{number:,}'.replace(',','.'))


class ImportWorkflow(QWidget):
    step_changed = Signal(int)

    def __init__(self, callbacks, parent=None):
        super().__init__(parent);self.setObjectName('importWorkflow');self.callbacks=callbacks
        layout=QHBoxLayout(self);layout.setContentsMargins(0,0,0,0);layout.setSpacing(10)
        self.steps=QListWidget();self.steps.setObjectName('importSteps');self.steps.setFixedWidth(190);self.steps.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        labels=[('Chọn nguồn','Chọn file hoặc thư mục LaTeX'),('Phân tích','Đọc câu hỏi và cấu trúc'),('Đối chiếu tài nguyên','Kiểm tra ảnh và file phụ'),('Xem trước','Duyệt, phân loại, sửa lỗi'),('Xác nhận','Nhập câu hợp lệ vào CSDL')]
        for index,(title,detail) in enumerate(labels):
            item=QListWidgetItem(f'{index+1}  {title}\n     {detail}');item.setData(Qt.ItemDataRole.UserRole,index);self.steps.addItem(item)
        layout.addWidget(self.steps);self.pages=QStackedWidget();layout.addWidget(self.pages,1)
        source=QWidget();box=QVBoxLayout(source);box.addWidget(QLabel('Chọn nguồn nhập'));hint=QLabel('Chọn file .tex hoặc thư mục chứa file và tài nguyên. File gốc không bị sửa.');hint.setWordWrap(True);box.addWidget(hint)
        actions=QHBoxLayout()
        self.file_button=QPushButton('Chọn file TeX');self.file_button.setObjectName('importPickFile');self.file_button.setIcon(icon('import','#4ba3eb'));self.file_button.clicked.connect(callbacks['file']);actions.addWidget(self.file_button)
        self.folder_button=QPushButton('Chọn thư mục');self.folder_button.setObjectName('importPickFolder');self.folder_button.setIcon(icon('chapter','#4ba3eb'));self.folder_button.clicked.connect(callbacks['folder']);actions.addWidget(self.folder_button)
        actions.addStretch()
        self.pending_button=QPushButton('Hàng chờ / Sửa lỗi');self.pending_button.setObjectName('importOpenPending');self.pending_button.setIcon(icon('bank','#4ba3eb'));self.pending_button.clicked.connect(callbacks['pending']);actions.addWidget(self.pending_button)
        box.addLayout(actions)
        self.source_path=QLabel('Chưa chọn nguồn');self.source_path.setObjectName('importSourcePath');self.source_path.setWordWrap(True);box.addWidget(self.source_path)
        for text in ('Tìm kiếm tài nguyên trong các thư mục con (graphicspath)','Bao gồm các file phụ input/include','Chỉ phân tích môi trường ex, vidu'):
            option=QCheckBox(text);option.setChecked(True);box.addWidget(option)
        
        box.addWidget(QLabel('Hoặc dán trực tiếp mã nguồn TeX:'))
        self.direct_text=QPlainTextEdit();self.direct_text.setObjectName('importDirectText')
        self.direct_text.setPlaceholderText(r'Dán mã câu hỏi LaTeX tại đây (ví dụ: \begin{ex}%[NB] ... \end{ex})...')
        self.direct_text.setMaximumHeight(130)
        box.addWidget(self.direct_text)
        paste_bar=QHBoxLayout()
        self.paste_button=QToolButton();self.paste_button.setObjectName('importDirectButton')
        self.paste_button.setText('Phân tích mã đã dán');self.paste_button.setIcon(icon('import','#4ba3eb'))
        self.paste_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.paste_button.clicked.connect(lambda: callbacks.get('direct_text',lambda t:None)(self.direct_text.toPlainText()))
        paste_bar.addWidget(self.paste_button);paste_bar.addStretch()
        box.addLayout(paste_bar)
        
        box.addStretch();self.pages.addWidget(source)
        parse=QWidget();box=QVBoxLayout(parse);box.addWidget(QLabel('Đang phân tích nguồn'));self.stats_strip=StatsStrip();box.addWidget(self.stats_strip);self.status=QLabel('Chọn nguồn để bắt đầu.');self.status.setWordWrap(True);box.addWidget(self.status);self.progress=QProgressBar();self.progress.setValue(0);box.addWidget(self.progress);box.addWidget(QLabel('Các câu hợp lệ, lỗi cú pháp và tài nguyên sẽ được giữ lại để đối chiếu.'));box.addStretch();self.pages.addWidget(parse)
        resources=QWidget();box=QVBoxLayout(resources);box.addWidget(QLabel('Đối chiếu tài nguyên'));self.resource_status=QLabel('Chưa có kết quả phân tích.');self.resource_status.setWordWrap(True);box.addWidget(self.resource_status)
        res_bar=QHBoxLayout()
        self.res_next_btn=QToolButton();self.res_next_btn.setText('Tiếp tục sang bước Xem trước ›');self.res_next_btn.setIcon(icon('bank','#4ba3eb'))
        self.res_next_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.res_next_btn.clicked.connect(lambda:self.set_step(3));res_bar.addWidget(self.res_next_btn);res_bar.addStretch();box.addLayout(res_bar)
        box.addStretch();self.pages.addWidget(resources)
        review=QWidget();self.content_host=QWidget();self.content=QVBoxLayout(self.content_host);self.content.setContentsMargins(0,0,0,0);box=QVBoxLayout(review);box.setContentsMargins(0,0,0,0);box.addWidget(self.content_host);self.pages.addWidget(review)
        confirm=QWidget();box=QVBoxLayout(confirm);box.addWidget(QLabel('Xác nhận nhập'));self.confirm_status=QLabel('Chưa ghi câu hỏi.');self.confirm_status.setWordWrap(True);box.addWidget(self.confirm_status)
        confirm_bar=QHBoxLayout()
        self.confirm_view_btn=QToolButton();self.confirm_view_btn.setText('Xem câu hỏi trong CSDL');self.confirm_view_btn.setIcon(icon('bank','#4ba3eb'))
        self.confirm_view_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.confirm_view_btn.clicked.connect(lambda:callbacks.get('view_library',lambda:None)())
        confirm_bar.addWidget(self.confirm_view_btn)
        self.confirm_pending_btn=QToolButton();self.confirm_pending_btn.setText('Mở Hàng chờ / Sửa lỗi');self.confirm_pending_btn.setIcon(icon('edit','#4ba3eb'))
        self.confirm_pending_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.confirm_pending_btn.clicked.connect(lambda:callbacks.get('pending',lambda:None)())
        confirm_bar.addWidget(self.confirm_pending_btn)
        self.confirm_restart_btn=QToolButton();self.confirm_restart_btn.setText('Nhập tiếp nguồn khác');self.confirm_restart_btn.setIcon(icon('import','#4ba3eb'))
        self.confirm_restart_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.confirm_restart_btn.clicked.connect(lambda:self.set_step(0))
        confirm_bar.addWidget(self.confirm_restart_btn);confirm_bar.addStretch();box.addLayout(confirm_bar)
        box.addStretch();self.pages.addWidget(confirm)
        self.steps.currentRowChanged.connect(self.pages.setCurrentIndex);self.pages.currentChanged.connect(self.step_changed.emit);self.set_step(0)

    def set_step(self,index):
        index=max(0,min(index,self.pages.count()-1));self.steps.setCurrentRow(index);self.pages.setCurrentIndex(index)
