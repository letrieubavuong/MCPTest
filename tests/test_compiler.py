from pathlib import Path
import shutil
import pytest
from latex_question_studio.preview.compiler import Compiler

@pytest.mark.skipif(not shutil.which('pdflatex'),reason='pdfLaTeX not installed')
def test_real_tex_tikz_asset_cache_and_error(tmp_path):
    from PySide6.QtGui import QImage,QColor
    image=QImage(20,20,QImage.Format.Format_RGB32);image.fill(QColor('blue'));image.save(str(tmp_path/'asset.png'))
    compiler=Compiler(tmp_path/'app')
    source=r"""\begin{ex}Tính $\frac{1}{2}+1$.\choice{1}{\True $1,5$}{2}{3}
\begin{tikzpicture}\draw (0,0) circle (0.3);\end{tikzpicture}
\includegraphics[width=1cm]{asset.png}\loigiai{Đáp án đúng là $1,5$.}\end{ex}"""
    first=compiler.compile(source,{'asset.png':tmp_path/'asset.png'})
    assert first.ok,first.log
    assert first.pdf.read_bytes().startswith(b'%PDF')
    assert not first.cache_hit
    png,pages=compiler.render(first.pdf)
    assert png.startswith(b'\x89PNG') and pages>=1
    assert compiler.compile(source,{'asset.png':tmp_path/'asset.png'}).cache_hit
    image.fill(QColor('red'));image.save(str(tmp_path/'asset.png'))
    changed=compiler.compile(source,{'asset.png':tmp_path/'asset.png'})
    assert changed.ok and not changed.cache_hit and changed.pdf!=first.pdf
    error=compiler.compile(r'\begin{ex}\UnknownMacro\end{ex}')
    assert not error.ok and 'source:' in error.log
    missing=compiler.compile(source)
    assert not missing.ok and 'asset.png' in missing.log


def test_missing_engine_and_cancellation(tmp_path):
    assert not Compiler(tmp_path,engine='no-such-tex-engine').compile('x').ok
    result=Compiler(tmp_path).compile('x',cancelled=lambda:True)
    assert result.cancelled

@pytest.mark.skipif(not shutil.which('pdflatex'),reason='pdfLaTeX not installed')
def test_timeout_kills_tex(tmp_path):
    compiler=Compiler(tmp_path,timeout=.1)
    result=compiler.compile(r'\def\forever{\forever}\forever')
    assert not result.ok and 'thời gian' in result.log


def test_provided_profile_and_custom_override(tmp_path, monkeypatch):
    import latex_question_studio.preview.compiler as module
    import hashlib
    preamble, dependencies=Compiler(tmp_path).profile()
    assert '{MAPClass}' in preamble and '\\newcommand{\\choice}' not in preamble
    root=module.default_profile_root()
    for relative in ('Class/MAPClass.cls','Packages/ex_test.sty'):
        assert dependencies[str(Path(relative))] == hashlib.sha256((root/relative).read_bytes()).hexdigest()
    custom=tmp_path/'custom.tex';custom.write_text(r'\documentclass{article}',encoding='utf-8')
    assert Compiler(tmp_path,preamble_file=custom).profile()[0].startswith(r'\documentclass{article}')
    copied=tmp_path/'profile with spaces'
    for relative in ('Class/MAPClass.cls','Packages/ex_test.sty'):
        target=copied/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(root/relative,target)
    monkeypatch.setattr(module,'default_profile_root',lambda:copied)
    first=Compiler(tmp_path).profile()[1]
    with (copied/'Packages/ex_test.sty').open('ab') as stream:stream.write(b'\n% cache invalidation test\n')
    assert Compiler(tmp_path).profile()[1]!=first

@pytest.mark.skipif(not shutil.which('pdflatex'),reason='pdfLaTeX not installed')
def test_mapclass_teacher_student_all_question_types(tmp_path):
    from latex_question_studio.application.lessons import student_source
    import pymupdf
    source=r"""\begin{ex}Tính $1+1$.\choice{1}{\True 2}{3}{4}\loigiai{TEACHERSECRET}\end{ex}
\begin{ex}Đúng sai.\choiceTF{\True Một}{Hai}{\True Ba}{Bốn}\end{ex}
\begin{ex}Đúng sai bảng.\choiceTFt{Một}{\True Hai}{Ba}{\True Bốn}\end{ex}
\begin{ex}Trả lời ngắn.\shortans{42}\end{ex}
\begin{ex}Tự luận $x^2=4$.\loigiai{TEACHERSECRET}\end{ex}"""
    for teacher in (True,False):
        result=Compiler(tmp_path).compile(source if teacher else student_source(source,hide_answers=True))
        assert result.ok,result.log
        with pymupdf.open(result.pdf) as doc:text=''.join(page.get_text() for page in doc)
        assert ('TEACHERSECRET' in text)==teacher
