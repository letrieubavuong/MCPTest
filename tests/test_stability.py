from PySide6.QtCore import QTimer
from threading import Event, get_ident
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
    importer=ImportService(services);main_thread=get_ident()
    entered={phase:Event() for phase in ('stage','commit')}
    responsive={phase:Event() for phase in entered};ticks={phase:0 for phase in entered}
    def heartbeat():
        for phase in entered:
            if entered[phase].is_set() and not responsive[phase].is_set():
                ticks[phase]+=1
                if ticks[phase]>=3:responsive[phase].set()
    def checkpoint(phase):
        assert get_ident()!=main_thread,'Import must run outside the UI thread'
        if not entered[phase].is_set():
            entered[phase].set()
            assert responsive[phase].wait(5),'UI did not respond during '+phase
        return False
    def work(cancelled,progress):
        batch,_=importer.stage([file],lambda:cancelled() or checkpoint('stage'),progress)
        return importer.commit(batch,cancelled=lambda:cancelled() or checkpoint('commit'))
    timer=QTimer();timer.timeout.connect(heartbeat);timer.start(5)
    done=[];errors=[];job=Job(work)
    job.signals.completed.connect(done.append);job.signals.failed.connect(errors.append);window.start_job(job)
    try:qtbot.waitUntil(lambda:bool(done or errors),timeout=30000)
    finally:
        timer.stop()
        for gate in responsive.values():gate.set()
    assert not errors and done==[500]
    assert all(ticks[phase]>=3 for phase in ticks)
    window.close()
