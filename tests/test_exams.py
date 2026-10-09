import json
import shutil
import pytest
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.exams import ExamService
from latex_question_studio.application.library import LibraryService
from latex_question_studio.parsing.latex import parse_questions

MCQ=r'\begin{ex}What is 2+2?\choice{1}{2}{3}{\True 4}\loigiai{SECRET SOLUTION}\end{ex}'

def test_shuffle_true_matrix_reproducible_and_history(tmp_path):
    s=create_services(AppConfig.load(tmp_path));exam=ExamService(s);library=LibraryService(s)
    a=s.questions.create(MCQ);b=s.questions.create(MCQ.replace('2+2','1+3'))
    library.save_metadata(a.id,{'grade':'12','subject':'Toán'})
    library.save_metadata(b.id,{'grade':'12','subject':'Toán'})
    matrix=[{'filters':{'grade':'12'},'count':1},{'filters':{'subject':'Toán'},'count':1}]
    for seed in range(12):
        version,snapshot=exam.generate('Test',matrix=matrix,seed=seed)
        assert len({q['question_id'] for q in snapshot['questions']})==2
        for q in snapshot['questions']:
            options=parse_questions(q['source'])[0].answer['options']
            index=ord(q['answer']['correct_letter'])-65
            assert options[index]['correct'] and '4' in options[index]['source']
            assert sum(o['correct'] for o in options)==1
        _,again=exam.generate('Test',matrix=matrix,seed=seed)
        assert snapshot==again
    assert len(exam.history())==24
    assert s.questions.get(a.id).latex_source==MCQ
    with pytest.raises(ValueError):exam.generate('Bad',matrix=[{'count':3,'filters':{'grade':'12'}}])
    with pytest.raises(ValueError):exam.generate('Bad',manual_ids=[a.id,a.id])

@pytest.mark.skipif(not shutil.which('pdflatex'),reason='pdfLaTeX missing')
def test_tex_pdf_student_and_solution_answers(tmp_path):
    import pymupdf
    s=create_services(AppConfig.load(tmp_path/'app'));exam=ExamService(s)
    q=s.questions.create(MCQ)
    _,snapshot=exam.generate('Exam',manual_ids=[q.id],seed=2)
    tex=exam.export_tex(snapshot,tmp_path/'student.tex')
    assert '\\renewcommand{\\loigiai}' in tex.read_text(encoding='utf-8')
    student=tmp_path/'student.pdf'
    result=exam.export_pdf(snapshot,student)
    assert result.ok,result.log
    with pymupdf.open(student) as pdf:assert 'SECRET' not in ''.join(p.get_text() for p in pdf)
    solution=tmp_path/'solution.pdf'
    result=exam.export_pdf(snapshot,solution,solutions=True)
    assert result.ok,result.log
    with pymupdf.open(solution) as pdf:assert 'SECRET' in ''.join(p.get_text() for p in pdf)
    result=exam.export_pdf(snapshot,tmp_path/'answers.pdf',answer_only=True)
    assert result.ok,result.log
