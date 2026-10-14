"""Check bundled code and open the reported formula with synthetic lesson data."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import types
import uuid

from PyInstaller.archive.readers import ZlibArchiveReader


root=Path(__file__).resolve().parents[1]
output=root/'artifacts/formula-input-fix'
evidence=json.loads((output/'verification.json').read_text(encoding='utf-8'))
fixture=Path(evidence['synthetic_data']).resolve()
if not fixture.is_relative_to((root/'.runtime').resolve()):raise ValueError('Expected synthetic workspace data')
target=root/'.runtime'/('formula-bundle-'+uuid.uuid4().hex[:8])
shutil.copytree(fixture,target,ignore=shutil.ignore_patterns('cache'))
import tomllib
version = tomllib.loads((root / 'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
exe = root / f'dist/{version}/LaTeXQuestionStudio/LaTeXQuestionStudio.exe'
if not exe.is_file():
    candidates = sorted((root / 'dist').glob('*/LaTeXQuestionStudio/LaTeXQuestionStudio.exe'))
    if candidates:
        exe = candidates[-1]
process=subprocess.run([str(exe),'--smoke-test','--smoke-delay-ms','12000','--data-dir',str(target),'--screenshot',str(output/'bundle-window.png')],capture_output=True,timeout=45)


def signature(code):
    return code.co_code,code.co_names,code.co_varnames,code.co_argcount,code.co_kwonlyargcount,tuple(signature(value) if isinstance(value,types.CodeType) else value for value in code.co_consts)


archive=ZlibArchiveReader(str(root/'.runtime/pyinstaller/LaTeXQuestionStudio/PYZ-00.pyz'))
matches={};unbundled=[]
for path in (root/'src/latex_question_studio').rglob('*.py'):
    if path.name in ('__init__.py','__main__.py'):continue
    name='.'.join(path.relative_to(root/'src').with_suffix('').parts)
    if name not in archive.toc:unbundled.append(name);continue
    matches[name]=signature(archive.extract(name))==signature(compile(path.read_text(encoding='utf-8'),str(path),'exec'))
report={'exit_code':process.returncode,'stderr':process.stderr.decode('utf-8','replace')[-1500:],'exe_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'synthetic_data':str(target),'all_modules_current':all(matches.values()),'modules_checked':len(matches),'source_modules_not_bundled':unbundled,'formula_modules_current':{name:matches[name] for name in ('latex_question_studio.parsing.visual','latex_question_studio.ui.wysiwyg','latex_question_studio.ui.lesson_page','latex_question_studio.application.lessons')}}
(output/'bundle-smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
assert process.returncode==0 and report['all_modules_current'] and (output/'bundle-window.png').is_file()
