import csv
import json
from pathlib import Path
import shutil

import pytest

from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.tex_exams import TexExamService
from latex_question_studio.parsing.latex import parse_questions


HEADER = r"""\documentclass{article}
\usepackage{graphicx}
\newenvironment{ex}{\par\noindent}{\par\medskip}
\newcommand{\True}{*}
\newcommand{\choice}[4]{\par A. #1 B. #2 C. #3 D. #4\par}
\newcommand{\choiceTF}[4]{\par a. #1 b. #2 c. #3 d. #4\par}
\newcommand{\loigiai}[1]{\par #1\par}
\newcommand{\shortans}[1]{#1}
\newcommand{\made}{000}
% \begin{document} in this comment is not a document boundary.
\begin{document}
\section*{ORIGINAL TEMPLATE - \made}
"""
MCQ = r'\begin{ex}QUESTION%d\choice{a}{\True CORRECT%d}{c}{d}\loigiai{TEACHERSECRET}\end{ex}'


def fixture(tmp_path, body=None):
    services = create_services(AppConfig.load(tmp_path / 'data'))
    source = HEADER + (body or (
        '\\section*{FIRST SECTION}\n' + '\n'.join(MCQ % (i, i) for i in range(1, 4)) +
        '\n\\section*{SECOND SECTION}\n' + '\n'.join(MCQ % (i, i) for i in range(4, 7)) +
        '\n\\section*{TRUE FALSE}\n' + r'\begin{ex}Statements\choiceTF{\True one}{two}{\True three}{four}\end{ex}')) + '\nFOOTER\n\\end{document}\n'
    path = tmp_path / 'exam with spaces.tex'
    path.write_bytes(source.encode('utf-8'))
    return services, TexExamService(services), path, source


@pytest.mark.parametrize('seed', [0, 17, 2027])
def test_sections_reproducibility_answers_and_bank_untouched(tmp_path, seed):
    services, service, path, source = fixture(tmp_path)
    document = service.load(path)
    assert [len(section['indices']) for section in document['sections']] == [3, 3, 1]
    batch = service.generate(document, ['101', '102'], seed=seed)
    again = service.generate(document, ['102', '101'], seed=seed)
    assert batch['variants'][0] == again['variants'][1]
    for variant in batch['variants']:
        assert variant['source'].startswith(HEADER.replace('{000}', '{' + variant['exam_code'] + '}'))
        assert variant['source'].endswith('\nFOOTER\n\\end{document}\n')
        assert {q['original_number'] for q in variant['questions'][:3]} == {1, 2, 3}
        assert {q['original_number'] for q in variant['questions'][3:6]} == {4, 5, 6}
        parsed = parse_questions(variant['source'])
        for question, item in zip(variant['questions'], parsed):
            if question['type'] == 'mcq':
                option = item.answer['options'][ord(question['answer']['correct_letter'])-65]
                assert option['correct'] and 'CORRECT' + str(question['original_number']) in option['source']
            else:
                assert question['permutation'] == [0, 1, 2, 3]
                assert question['answer']['truth'] == [True, False, True, False]
    assert path.read_bytes() == source.encode('utf-8')
    with services.database.connect() as connection:
        assert connection.execute('SELECT count(*) FROM questions').fetchone()[0] == 0
        assert connection.execute('SELECT count(*) FROM import_batches').fetchone()[0] == 0


def test_disabled_shuffle_keeps_template_and_option_gaps(tmp_path):
    body = '\\section*{ONE}\n' + (MCQ % (1, 1)).replace('}{', '}  % preserve option spacing\n{')
    _, service, path, source = fixture(tmp_path, body)
    document = service.load(path)
    variant = service.generate(document, ['101'], shuffle_questions=False, shuffle_options=False)['variants'][0]
    assert variant['source'] == source.replace('{000}', '{101}')
    shuffled = service.generate(document, ['101'], seed=4)['variants'][0]
    assert shuffled['source'].count('% preserve option spacing') == source.count('% preserve option spacing')
    assert not parse_questions(shuffled['source'])[0].diagnostics


def test_pinned_assets_student_export_mapping_and_private_image(tmp_path):
    body = '\\section*{ONE}\n' + (MCQ % (1, 1)).replace('QUESTION1', r'QUESTION1\includegraphics[width=1cm]{visible.png}').replace('TEACHERSECRET', r'TEACHERSECRET\includegraphics{secret.png}')
    _, service, path, source = fixture(tmp_path, body)
    image = Path(__file__).resolve().parents[1] / 'examples/diagram.png'
    for name in ('visible.png', 'secret.png'):
        shutil.copyfile(image, tmp_path / name)
    document = service.load(path)
    batch = service.generate(document, ['101', '102'])
    path.write_text('changed source', encoding='utf-8')
    (tmp_path / 'visible.png').write_bytes(b'changed image')
    target = service.export(batch, tmp_path / 'output', pdf=False)
    student = target / 'student'
    assert (student / 'visible.png').read_bytes() == image.read_bytes()
    assert not (student / 'secret.png').exists()
    for paper in student.glob('*.tex'):
        body = paper.read_text(encoding='utf-8').split(r'\begin{document}', 1)[1]
        assert 'TEACHERSECRET' not in body and r'\True' not in body and r'\loigiai' not in body
        assert 'ORIGINAL TEMPLATE' in body and 'FOOTER' in body
    with (target / 'dap-an.csv').open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.reader(stream))
    assert len(rows) == 3
    assert rows[1][-1] == batch['variants'][0]['questions'][0]['answer']['correct_letter']
    manifest = json.loads((target / 'doi-chieu-ma-de.json').read_text(encoding='utf-8'))
    assert manifest['source_sha256'] == document['source_sha256'] and len(manifest['mapping']) == 2
    teacher = service.export(batch, tmp_path / 'output', pdf=False, solutions=True)
    assert (teacher / 'teacher/secret.png').exists()
    assert 'TEACHERSECRET' in (teacher / 'teacher/de-101.tex').read_text(encoding='utf-8')


def test_invalid_questions_codes_resources_and_atomic_cancel(tmp_path):
    _, service, path, _ = fixture(tmp_path)
    document = service.load(path)
    for codes in ([], ['101', '101'], ['A101', 'a101'], ['../101'], ['Mã01']):
        with pytest.raises(ValueError):
            service.generate(document, codes)
    with pytest.raises(InterruptedError):
        service.generate(document, ['101'], cancelled=lambda: True)
    batch = service.generate(document, ['101', '102'])
    done = []
    output = tmp_path / 'output'
    with pytest.raises(InterruptedError):
        service.export(batch, output, pdf=False, cancelled=lambda: bool(done), progress=lambda a, b: done.append(a))
    assert list(output.iterdir()) == []
    path.write_text(HEADER + r'\begin{ex}\choice{a}{b}{c}{d}\end{ex}\end{document}', encoding='utf-8')
    with pytest.raises(ValueError, match='True'):
        service.load(path)
    path.write_text(HEADER + r'\begin{ex}\includegraphics{missing.png}\end{ex}\end{document}', encoding='utf-8')
    with pytest.raises(ValueError, match='Thiếu tài nguyên'):
        service.load(path)


@pytest.mark.skipif(not shutil.which('pdflatex'), reason='pdfLaTeX not installed')
def test_original_template_real_pdf_and_standalone_tex(tmp_path):
    import pymupdf
    import subprocess
    _, service, path, _ = fixture(tmp_path, '\\section*{CUSTOM SECTION}\n' + MCQ % (1, 1))
    document = service.load(path)
    batch = service.generate(document, ['101'])
    for teacher in (False, True):
        target = service.export(batch, tmp_path / 'output', solutions=teacher)
        paper = target / ('teacher' if teacher else 'student') / 'de-101.pdf'
        with pymupdf.open(paper) as pdf:
            text = ''.join(page.get_text() for page in pdf)
        assert 'ORIGINAL TEMPLATE' in text and 'CUSTOM SECTION' in text and 'FOOTER' in text
        assert ('TEACHERSECRET' in text) == teacher
        result = subprocess.run(['pdflatex', '-no-shell-escape', '-interaction=nonstopmode', '-halt-on-error', 'de-101.tex'], cwd=paper.parent, capture_output=True, timeout=30)
        assert result.returncode == 0, result.stdout.decode('utf-8', 'replace')[-4000:]


def test_file_mode_fragment_mapclass_dependencies(tmp_path):
    _, service, path, _ = fixture(tmp_path)
    path.write_text(MCQ % (1, 1), encoding='utf-8')
    document = service.load(path)
    assert not document['full_document'] and 'MAPClass.cls' in document['resources']
    batch = service.generate(document, ['101'])
    source, body, profile, assets = service.preview(batch, batch['variants'][0])
    assert r'\begin{document}' in source and '{MAPClass}' in profile.read_text(encoding='utf-8')


def test_page_breaks_keep_section_and_local_preamble_dependencies(tmp_path):
    body = '\\section*{ONE}\n' + MCQ % (1, 1) + '\n\\newpage\n\\vspace{2cm}\n' + MCQ % (2, 2)
    _, service, path, source = fixture(tmp_path, body)
    path.write_text(source.replace(r'\usepackage{graphicx}', r'\usepackage{graphicx}\input{custom}'), encoding='utf-8')
    (tmp_path / 'custom.tex').write_text(r'\newcommand{\mytitle}{Original}', encoding='utf-8')
    document = service.load(path)
    assert len(document['sections']) == 1
    assert 'custom.tex' in document['resources']
    batch = service.generate(document, ['101'])
    target = service.export(batch, tmp_path / 'output', pdf=False)
    assert (target / 'student/custom.tex').read_text(encoding='utf-8') == r'\newcommand{\mytitle}{Original}'


@pytest.mark.skipif(not shutil.which('pdflatex'), reason='pdfLaTeX not installed')
def test_complete_mapclass_template_is_preserved_and_compiles(tmp_path):
    _, service, path, _ = fixture(tmp_path)
    source = r'\documentclass[company=BookA4,pagesize=DethiA4,mausac=01,tuychon=GV1]{MAPClass}\begin{document}' + MCQ % (1, 1) + r'\end{document}'
    path.write_text(source, encoding='utf-8')
    document = service.load(path)
    assert 'MAPClass.cls' in document['resources'] and 'Packages/ex_test.sty' in document['resources']
    batch = service.generate(document, ['101'])
    target = service.export(batch, tmp_path / 'output')
    assert (target / 'student/de-101.pdf').read_bytes().startswith(b'%PDF')
