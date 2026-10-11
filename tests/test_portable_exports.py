import json
import zipfile

from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.exams import ExamService
from latex_question_studio.application.importing import ImportService
from latex_question_studio.application.services import create_services


def test_exam_portable_zip_has_manifest_and_no_solution_for_student(tmp_path):
    services=create_services(AppConfig.load(tmp_path/'data'))
    image=tmp_path/'q.png';image.write_bytes(b'question image')
    source=tmp_path/'q.tex';source.write_text(r'\begin{ex}Q\includegraphics{q.png}\choice{a}{\True b}{c}{d}\loigiai{SECRET}\end{ex}',encoding='utf-8')
    batch,_=ImportService(services).stage([source]);assert ImportService(services).commit(batch)==1
    exam=ExamService(services);_,snapshot=exam.generate('Portable',manual_ids=[services.questions.list_page()[0].id])
    archive=exam.export_zip(snapshot,tmp_path/'student.zip')
    with zipfile.ZipFile(archive) as bundle:
        names=set(bundle.namelist());assert 'main.tex' in names and 'manifest.json' in names and any(name.startswith('assets/') for name in names)
        text=bundle.read('main.tex').decode('utf-8');manifest=json.loads(bundle.read('manifest.json'))
        body=text.split(r'\begin{document}',1)[1]
        assert 'SECRET' not in body and r'\True' not in body and manifest['audience']=='student'
        for name,digest in manifest['sha256'].items():
            import hashlib
            assert hashlib.sha256(bundle.read(name)).hexdigest()==digest
