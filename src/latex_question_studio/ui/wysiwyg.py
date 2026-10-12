"""Editable visual LaTeX projection with atomic formulas and lossless TeX anchors."""
from collections import OrderedDict
import hashlib
import json
import time

from PySide6.QtCore import Qt, Signal, QSizeF
from PySide6.QtGui import (QColor, QFont, QImage, QPainter, QTextCharFormat, QTextCursor,
    QTextFormat, QPyTextObject, QUndoCommand, QUndoStack)
from PySide6.QtWidgets import QTextEdit, QDialog, QDialogButtonBox, QVBoxLayout

from latex_question_studio.parsing.visual import escape_text, visual_runs, encode_visual_input, tex_input_spans, recover_literal_tex, formula_source
from latex_question_studio.preview.compiler import Compiler
from latex_question_studio.ui.editor import LatexEditor
from latex_question_studio.ui.jobs import Job


RUN_ID = int(QTextFormat.Property.UserProperty) + 40
TEX_OBJECT = int(QTextFormat.ObjectTypes.UserObject) + 40
OBJECT = '\ufffc'


class TeXRenderer(QPyTextObject):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def intrinsicSize(self, document, position, format):
        key = int(format.property(RUN_ID))
        run = self.editor.runs[key]
        if run.kind == 'anchor':
            return QSizeF(.1, 1)
        image = self.editor.images.get(key)
        if image is not None:
            return self.editor.image_size(run, image)
        if run.kind == 'break':
            return QSizeF(.1, 1)
        metrics = self.editor.fontMetrics()
        return QSizeF(min(340, metrics.horizontalAdvance(run.text) + 12), 28)

    def drawObject(self, painter, rect, document, position, format):
        key = int(format.property(RUN_ID))
        run = self.editor.runs[key]
        if run.kind in ('anchor', 'break'):
            return
        image = self.editor.images.get(key)
        if image is not None:
            if run.kind in ('math','display_math'):
                image=image.copy();tint=QPainter(image);tint.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                tint.fillRect(image.rect(),self.editor.palette().text().color());tint.end()
            painter.drawImage(rect, image)
            return
        if run.kind in ('heading', 'option', 'correct'):
            painter.setPen(QColor('#187c77') if run.kind == 'correct' else self.editor.palette().text().color())
            font = QFont(self.editor.font());font.setBold(True);painter.setFont(font)
        else:
            painter.fillRect(rect, QColor('#e8f1f8'))
            painter.setPen(QColor('#285c80'))
        painter.drawText(rect, Qt.AlignmentFlag.AlignVCenter, run.text)


class SourceEdit(QUndoCommand):
    def __init__(self, editor, before, after, typing=False):
        super().__init__('Soạn nội dung')
        self.editor, self.before, self.after = editor, before, after
        self.first = True
        self.typing=typing;self.epoch=editor.generation;self.timestamp=time.monotonic()

    def id(self):
        return 1 if self.typing else -1

    def mergeWith(self, other):
        if not isinstance(other,SourceEdit) or not other.typing or other.editor is not self.editor or other.epoch!=self.epoch or other.before!=self.after or other.timestamp-self.timestamp>1:
            return False
        self.after=other.after;self.timestamp=other.timestamp;return True

    def undo(self):
        self.editor.restore_source(self.before)

    def redo(self):
        if self.first:
            self.first = False
        else:
            self.editor.restore_source(self.after)


class VisualLatexEditor(QTextEdit):
    sourceChanged = Signal(str)
    notice = Signal(str)

    def __init__(self, services, run_job, compiler_config, parent=None):
        super().__init__(parent)
        self.services, self.run_job, self.compiler_config = services, run_job, compiler_config
        self.setObjectName('wysiwygEditor')
        self.setAcceptRichText(False)
        self.setUndoRedoEnabled(False)
        self.document().setDocumentMargin(20)
        self.setFont(QFont('Segoe UI', 12))
        self.runs, self.images, self.assets = [], {}, {}
        self._source = ''
        self.loading = False
        self.generation = 0
        self.render_job = None
        self.image_cache = OrderedDict()
        self.history = QUndoStack(self);self.history.setUndoLimit(150)
        self.renderer = TeXRenderer(self)
        self.document().documentLayout().registerHandler(TEX_OBJECT, self.renderer)
        self.textChanged.connect(self._visual_changed)

    def source(self):
        return self._source

    def set_source(self, source, assets=None, reset_history=True):
        if reset_history:
            self.history.clear()
        self.cancel_render()
        self.assets = dict(assets or {})
        self._source = source
        self.runs = visual_runs(source)
        self.images = {}
        self.loading = True
        self.clear()
        cursor = self.textCursor()
        for key, run in enumerate(self.runs):
            format = QTextCharFormat()
            format.setProperty(RUN_ID, key)
            if run.kind == 'text':
                format.setFontWeight(QFont.Weight.Bold if run.style.get('bold') else QFont.Weight.Normal)
                format.setFontItalic(bool(run.style.get('italic')))
                format.setFontUnderline(bool(run.style.get('underline')))
                format.setFontPointSize(run.style.get('size', 12))
                cursor.insertText(run.text.replace('\n', '\u2028').replace('\r', ''), format)
            else:
                if run.kind=='option':
                    separator=QTextCharFormat();separator.setProperty(RUN_ID,-1);cursor.insertText('\u2028',separator)
                format.setObjectType(TEX_OBJECT)
                if run.kind=='math':format.setVerticalAlignment(QTextCharFormat.VerticalAlignment.AlignMiddle)
                cursor.insertText(OBJECT, format)
                if run.kind in ('heading', 'option', 'break'):
                    separator = QTextCharFormat();separator.setProperty(RUN_ID, -1)
                    if run.kind in ('heading', 'break'):
                        cursor.insertText('\u2028', separator)
                    else:
                        cursor.insertText(' ', separator)
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.setTextCursor(cursor)
        self.loading = False
        self.schedule_render()

    def _pieces(self):
        pieces = []
        block = self.document().begin()
        while block.isValid():
            iterator = block.begin()
            while not iterator.atEnd():
                fragment = iterator.fragment()
                if fragment.isValid():
                    format = fragment.charFormat()
                    key = format.property(RUN_ID) if format.hasProperty(RUN_ID) else None
                    text = fragment.text()
                    if pieces and pieces[-1][0] == key and pieces[-1][2] + len(pieces[-1][1].encode('utf-16-le'))//2 == fragment.position():
                        pieces[-1] = (key, pieces[-1][1]+text, pieces[-1][2])
                    else:
                        pieces.append((key, text, fragment.position()))
                iterator += 1
            if block.next().isValid():
                pieces.append((None, '\n', block.position()+block.length()-1))
            block = block.next()
        return pieces

    def serialized(self, with_mapping=False):
        source, mapping, protected = [], {}, []
        offset = 0
        for key, text, position in self._pieces():
            if key == -1:
                raw = ''
            elif key is not None and 0 <= int(key) < len(self.runs):
                key = int(key);run = self.runs[key]
                if run.kind != 'text':
                    if text != OBJECT:
                        raise ValueError('Chọn vùng văn bản để sửa; công thức mở bằng nhấp đúp.')
                    raw = run.raw
                    if run.protected:
                        protected.append(key)
                else:
                    display = text.replace('\u2028', '\n')
                    raw = run.raw if display == run.text.replace('\r', '') else encode_visual_input(display)
            else:
                raw = encode_visual_input(text.replace('\u2028', '\n'))
            mapping[position] = offset
            width = len(text.encode('utf-16-le'))//2
            if key is not None and key != -1 and 0 <= int(key) < len(self.runs) and self.runs[int(key)].kind == 'text' and raw == text.replace('\u2028', '\n'):
                inner = 0
                for char in text:
                    mapping[position+inner] = offset
                    inner += len(char.encode('utf-16-le'))//2
                    offset += 1
                source.append(raw)
            else:
                source.append(raw);offset += len(raw)
            mapping[position+width] = offset
        required = [key for key, run in enumerate(self.runs) if run.protected]
        if protected != required:
            raise ValueError('Cấu trúc câu/đáp án được giữ nguyên; sửa phần văn bản hoặc chuyển Mã LaTeX.')
        value = ''.join(source)
        return (value, mapping) if with_mapping else value

    def _visual_changed(self):
        if self.loading:
            return
        before = self._source
        try:
            after = self.serialized()
        except ValueError as error:
            self.set_source(before, self.assets, reset_history=False)
            self.notice.emit(str(error))
            return
        if after == before:
            return
        promote=False
        for key,text,position in self._pieces():
            display=text.replace('\u2028','\n')
            if key is None or (key>=0 and self.runs[int(key)].kind=='text' and display!=self.runs[int(key)].text.replace('\r','')):
                promote=promote or bool(tex_input_spans(display))
        cursor_offset=self.serialized(with_mapping=True)[1].get(self.textCursor().position(),len(after))
        self._source = after
        self.history.push(SourceEdit(self, before, after, typing=True))
        if promote:
            self.set_source(after,self.assets,reset_history=False);self.move_to_source(cursor_offset)
        self.sourceChanged.emit(after)

    def restore_source(self, source):
        self.set_source(source, self.assets, reset_history=False)
        self.sourceChanged.emit(source)

    def move_to_source(self, offset):
        raw_position = 0
        visual_position = 0
        for run in self.runs:
            if run.kind=='option':visual_position+=1
            width = len(run.text.replace('\n','\u2028').replace('\r','').encode('utf-16-le'))//2 if run.kind == 'text' else 1
            if raw_position <= offset <= raw_position + len(run.raw):
                inner = min(offset-raw_position, len(run.text)) if run.kind == 'text' else (1 if offset==raw_position+len(run.raw) else 0)
                prefix = run.text[:inner] if run.kind == 'text' else ''
                target = visual_position + (len(prefix.encode('utf-16-le'))//2 if run.kind == 'text' else inner)
                cursor = self.textCursor();cursor.setPosition(min(target,self.document().characterCount()-1));self.setTextCursor(cursor)
                return
            raw_position += len(run.raw)
            visual_position += width + (1 if run.kind in ('heading','option','break') else 0)

    def apply_source(self, source, cursor_offset=None):
        before = self._source
        self.set_source(source, self.assets, reset_history=False)
        if cursor_offset is not None:self.move_to_source(cursor_offset)
        if before != source:
            self.history.push(SourceEdit(self, before, source))
            self.sourceChanged.emit(source)

    def wrap_selection(self, prefix, suffix, replace=False):
        value, mapping = self.serialized(with_mapping=True)
        cursor = self.textCursor()
        start, end = cursor.selectionStart(), cursor.selectionEnd()
        # Expand a plain-text position within a run without exposing TeX wrappers.
        for key, text, position in self._pieces():
            if key is not None and key != -1 and self.runs[int(key)].kind == 'text':
                width = len(text.encode('utf-16-le'))//2
                for point in (start, end):
                    if position <= point <= position+width and point not in mapping:
                        prefix_text = text.encode('utf-16-le')[:2*(point-position)].decode('utf-16-le')
                        mapping[point] = mapping[position] + len(encode_visual_input(prefix_text.replace('\u2028', '\n')))
        if start not in mapping or end not in mapping:
            self.notice.emit('Chọn phần văn bản hoặc đặt con trỏ giữa các nội dung.')
            return
        a, b = mapping[start], mapping[end]
        selected = value[a:b] if start != end and not replace else ''
        if start != end:
            structural = ('heading','option','correct')
            for key, text, position in self._pieces():
                if key is not None and key >= 0 and start <= position < end and self.runs[int(key)].kind in structural:
                    self.notice.emit('Chọn văn bản trong cùng một mục hoặc phương án để định dạng.');return
        after = value[:a]+prefix+selected+suffix+value[b:]
        self.apply_source(after, a+len(prefix)+len(selected))
        self.setFocus()

    def insert_tex(self,source):
        self.wrap_selection(source,'',replace=True)

    def recover_tex_input(self):
        recovered=recover_literal_tex(self._source)
        if recovered==self._source:
            self.notice.emit('Không có công thức LaTeX bị chuyển thành chữ trong mục này.');return
        self.apply_source(recovered)
        self.notice.emit('Đã nhận dạng lại công thức và lệnh LaTeX. Có thể hoàn tác.')

    def edit_object(self, position=None):
        position=self.textCursor().position() if position is None else position
        for point in (position,position-1):
            if not 0<=point<self.document().characterCount()-1:continue
            cursor=QTextCursor(self.document());cursor.setPosition(point);cursor.movePosition(QTextCursor.MoveOperation.NextCharacter,QTextCursor.MoveMode.KeepAnchor)
            format=cursor.charFormat()
            if cursor.selectedText()!=OBJECT or not format.hasProperty(RUN_ID):continue
            key=int(format.property(RUN_ID))
            if key<0 or key>=len(self.runs) or self.runs[key].protected or self.runs[key].kind=='text':continue
            self.open_tex_dialog(key);return True
        return False

    def open_tex_dialog(self, key=None):
        dialog = QDialog(self);dialog.setWindowTitle('Sửa công thức / LaTeX' if key is not None else 'Chèn công thức')
        dialog.resize(580, 270);layout = QVBoxLayout(dialog)
        editor = LatexEditor(dialog)
        editor.setPlainText(self.runs[key].raw if key is not None else r'$x^2$')
        layout.addWidget(editor)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        raw = editor.toPlainText()
        if key is None or self.runs[key].kind in ('math','display_math'):
            raw=formula_source(raw)
        if key is None:
            self.insert_tex(raw)
        else:
            value, mapping = self.serialized(with_mapping=True)
            piece = next(((k, t, p) for k, t, p in self._pieces() if k == key), None)
            if piece:
                offset = mapping[piece[2]]
                self.apply_source(value[:offset]+raw+value[offset+len(self.runs[key].raw):],offset+len(raw))

    def keyPressEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_Z:
                self.history.redo() if event.modifiers() & Qt.KeyboardModifier.ShiftModifier else self.history.undo()
                return
            if event.key() == Qt.Key.Key_Y:
                self.history.redo();return
            if event.key() in (Qt.Key.Key_B, Qt.Key.Key_I, Qt.Key.Key_U):
                name = {Qt.Key.Key_B: 'textbf', Qt.Key.Key_I: 'textit', Qt.Key.Key_U: 'underline'}[event.key()]
                self.wrap_selection('\\'+name+'{', '}');return
        format = QTextCharFormat(self.currentCharFormat())
        if format.objectType() == TEX_OBJECT or format.property(RUN_ID) == -1:
            format.setObjectType(QTextFormat.ObjectTypes.NoObject);format.clearProperty(RUN_ID)
            self.setCurrentCharFormat(format)
        super().keyPressEvent(event)

    def inputMethodEvent(self,event):
        if event.commitString():
            format=QTextCharFormat(self.currentCharFormat())
            if format.objectType()==TEX_OBJECT or format.property(RUN_ID)==-1:
                format.setObjectType(QTextFormat.ObjectTypes.NoObject);format.clearProperty(RUN_ID)
                self.setCurrentCharFormat(format)
        super().inputMethodEvent(event)

    def mouseDoubleClickEvent(self, event):
        position = self.cursorForPosition(event.position().toPoint()).position()
        if self.edit_object(position):return
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        menu=self.createStandardContextMenu()
        for action in menu.actions():
            if 'undo' in action.text().lower() or 'redo' in action.text().lower():action.setVisible(False)
        menu.addSeparator();menu.addAction('Hoàn tác',self.history.undo).setEnabled(self.history.canUndo())
        menu.addAction('Làm lại',self.history.redo).setEnabled(self.history.canRedo())
        position=self.cursorForPosition(event.pos()).position()
        menu.addAction('Sửa công thức / LaTeX',lambda:self.edit_object(position))
        menu.exec(event.globalPos())

    def closeEvent(self,event):
        self.cancel_render();super().closeEvent(event)

    def insertFromMimeData(self, data):
        cursor = self.textCursor()
        format = QTextCharFormat();cursor.insertText(data.text(), format)

    def image_size(self, run, image):
        max_height = 80 if run.kind == 'math' else 220
        native_scale = 0.65 if run.kind in ('math','display_math') else 1.0
        scale = min(native_scale, max(60,min(420,self.viewport().width()-45))/max(1,image.width()), max_height/max(1,image.height()))
        return QSizeF(max(1, image.width()*scale), max(1, image.height()*scale))

    def resizeEvent(self,event):
        super().resizeEvent(event)
        self.document().markContentsDirty(0,self.document().characterCount())

    def cancel_render(self):
        self.generation += 1
        if self.render_job:
            self.render_job.cancelled.set()
        self.render_job = None

    def schedule_render(self):
        if not self.services or not self.run_job:
            return
        generation = self.generation
        config = self.compiler_config()
        candidates = [(key, run.raw) for key, run in enumerate(self.runs) if run.kind in ('math','display_math','image','diagram')]
        try:
            profile=Compiler(self.services.config.data_dir,preamble_file=config.get('preamble_file') or None).profile()
            signatures=[(name,hashlib.sha256(path.read_bytes()).hexdigest()) for name,path in self.assets.items()]
            context=json.dumps((config,profile,signatures),sort_keys=True,default=str)
        except (OSError,ValueError):
            context=json.dumps(config,sort_keys=True)
        pending=[]
        for key,raw in candidates:
            fingerprint=hashlib.sha256((raw+context).encode()).hexdigest()
            if fingerprint in self.image_cache:
                self.images[key]=self.image_cache[fingerprint]
                self.image_cache.move_to_end(fingerprint)
            else:pending.append((key,raw,fingerprint,self.runs[key].kind))
        if not pending:
            return
        assets = dict(self.assets)
        def work(cancelled, progress):
            compiler = Compiler(self.services.config.data_dir, engine=config.get('engine','pdflatex'), preamble_file=config.get('preamble_file') or None)
            result = []
            for index, (key, raw, fingerprint, kind) in enumerate(pending):
                if cancelled():
                    break
                output = compiler.compile(raw, assets, cancelled)
                if output.ok and not cancelled():
                    result.append((key, fingerprint, self.render_object(output.pdf,kind)))
                progress(index+1, len(pending))
            return generation, result
        job = Job(work);self.render_job = job
        def ready(payload):
            current, images = payload
            if current != self.generation:
                return
            self.render_job = None
            for key, fingerprint, raw in images:
                image = QImage.fromData(raw)
                if not image.isNull():
                    self.images[key] = image
                    self.image_cache[fingerprint]=image;self.image_cache.move_to_end(fingerprint)
            while len(self.image_cache)>80:self.image_cache.popitem(last=False)
            self.document().markContentsDirty(0, self.document().characterCount())
            self.viewport().update()
        job.signals.completed.connect(ready)
        job.signals.failed.connect(lambda error: self.notice.emit(error) if generation == self.generation else None)
        self.run_job(job)

    @staticmethod
    def render_object(pdf,kind):
        if kind not in ('math','display_math'):return Compiler.render(pdf)[0]
        import pymupdf
        with pymupdf.open(pdf) as document:
            page=document[0];rectangles=[pymupdf.Rect(block[:4]) for block in page.get_text('blocks')]
            rectangles.extend(drawing['rect'] for drawing in page.get_drawings())
            clip=page.rect
            if rectangles:
                clip=rectangles[0]
                for rectangle in rectangles[1:]:clip=clip|rectangle
                clip=(clip+(-1,-1,1,1))&page.rect
            return page.get_pixmap(matrix=pymupdf.Matrix(2,2),clip=clip,alpha=True).tobytes('png')
