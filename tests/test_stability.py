from PySide6.QtCore import QTimer
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.importing import ImportService
from latex_question_studio.ui.main_window import MainWindow
from latex_question_studio.ui.jobs import Job


def test_pending_repair_keeps_original_and_commits(tmp_path):
    services=create_services(AppConfig.load(tmp_path/'app'));importer=ImportService(services)
    file=tmp_path/'bad.tex';original=r'\begin{ex}\choice{a}{b}\end{ex}';file.write_text(original)
    batch,results=importer.stage([file]);item=results[0]['id']
    assert importer.commit(batch)==0
    repaired=r'\begin{ex}\choice{a}{b}{\True c}{d}\end{ex}'
    assert importer.repair(item,repaired)==[]
    assert importer.commit(batch,{item})==1
    assert services.questions.list_page()[0].latex_source==repaired
    with services.database.connect() as c:
        row=c.execute('SELECT raw_source,working_source FROM import_items').fetchone()
        assert tuple(row)==(original,repaired)
    assert file.read_text()==original


def test_ui_timer_runs_during_import_and_commit(qtbot,tmp_path):
    services=create_services(AppConfig.load(tmp_path/'app'));window=MainWindow(services);qtbot.addWidget(window)
    file=tmp_path/'batch.tex';file.write_text('\n'.join(r'\begin{ex}Question '+str(i)+r'\end{ex}' for i in range(500)))
    importer=ImportService(services);ticks=[];timer=QTimer();timer.timeout.connect(lambda:ticks.append(1));timer.start(5)
    done=[]
    job=Job(lambda cancelled,progress:importer.commit(importer.stage([file],cancelled,progress)[0]))
    job.signals.completed.connect(done.append);window.start_job(job)
    qtbot.waitUntil(lambda:bool(done),timeout=30000)
    timer.stop();assert done==[500];assert len(ticks)>2
    window.close()
