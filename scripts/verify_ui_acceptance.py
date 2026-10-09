"""Additional owned-window acceptance: actual shortcuts and 2,000-question staging."""
from pathlib import Path
import json,time,uuid
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt,QThreadPool
from PySide6.QtTest import QTest
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.importing import ImportService
from latex_question_studio.ui.main_window import MainWindow
root=Path(__file__).resolve().parents[1];folder=root/'.runtime'/('ui-acceptance-'+uuid.uuid4().hex[:8]);folder.mkdir(parents=True)
app=QApplication([]);services=create_services(AppConfig.load(folder));q=services.questions.create(r'\begin{ex}Tính $1+1$.\end{ex}')
w=MainWindow(services);w.show();w.activateWindow();w.raise_();editor=w.open_question(q.id);editor.setFocus();QTest.qWait(100)
editor.clear();QTest.keyClicks(editor,r'\begin{ex}Compute $2+2$.\end{ex}');QTest.keyClick(editor,Qt.Key.Key_S,Qt.KeyboardModifier.ControlModifier);QTest.qWait(100)
report={'ctrl_s':not editor.document().isModified() and '$2+2$' in services.questions.get(q.id).latex_source}
QTest.keyClick(editor,Qt.Key.Key_F,Qt.KeyboardModifier.ControlModifier);QTest.qWait(50);report['ctrl_f']=editor.findbar.isVisible()
QTest.keyClick(editor,Qt.Key.Key_H,Qt.KeyboardModifier.ControlModifier);QTest.qWait(50);report['ctrl_h']=editor.replace_input.isVisible();editor.hide_find()
file=folder/'2000 cau minh hoa.tex';file.write_text('\n'.join(r'\begin{ex}Tính $'+str(i)+r'+1$.\end{ex}' for i in range(2000)),encoding='utf-8')
start=time.perf_counter();batch,rows=ImportService(services).stage([file]);report['staged_count']=len(rows);report['stage_seconds']=round(time.perf_counter()-start,3)
start=time.perf_counter();w.import_ready((batch,rows));review=w.import_review;review.cancel_preview();report['review_seconds']=round(time.perf_counter()-start,3);report['visible_rows']=review.table.rowCount()
review.table.item(0,0).setCheckState(Qt.CheckState.Unchecked);review.change_page(1);review.cancel_preview();review.change_page(-1);review.cancel_preview();report['excluded_survives_page']=rows[0]['id'] not in review.selected_ids()
w.library_split.setSizes([210,650,400]);w.show_page(4);w.show_page(0);report['editor_preserved']='$2+2$' in editor.toPlainText()
w.close();QThreadPool.globalInstance().waitForDone(5000)
(root/'artifacts/ui-redesign/acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False));assert all(report[k] for k in ('ctrl_s','ctrl_f','ctrl_h','excluded_survives_page','editor_preserved')) and report['staged_count']==2000 and report['visible_rows']==200
