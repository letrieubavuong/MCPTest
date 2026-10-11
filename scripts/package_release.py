from pathlib import Path
import hashlib
import importlib.metadata as metadata
import json
import shutil
import struct
import sys
import zipfile
import argparse
import tomllib

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--dist-dir',type=Path,default=root/'dist/LaTeXQuestionStudio');parser.add_argument('--output-dir',type=Path,default=root/'release');parser.add_argument('--test-count',type=int,required=True);args=parser.parse_args()
version=tomllib.loads((root/'pyproject.toml').read_text(encoding='utf-8'))['project']['version']
dist=args.dist_dir.resolve()
exe=dist/'LaTeXQuestionStudio.exe'
raw=exe.read_bytes()
if raw[:2] != b'MZ': raise RuntimeError('Invalid executable header')
offset=struct.unpack_from('<I',raw,60)[0]
if struct.unpack_from('<H',raw,offset+4)[0]!=0x8664:raise RuntimeError('Refusing to package a non-x64 executable')
subsystem=struct.unpack_from('<H',raw,offset+24+68)[0]
if subsystem!=2:raise RuntimeError('Refusing to release an executable that opens a console')
for name in ('USER_GUIDE.md','TROUBLESHOOTING.md','RELEASE_NOTES.md','18_LESSON_AUTHORING_SPEC.md','19_LESSON_IMPLEMENTATION_REPORT.md','20_KHTN6_CURRICULUM_REPORT.md','CODEX_TECHNICAL_AUDIT.md','PERFORMANCE_BENCHMARK.md','CODEX_STABILIZATION_REPORT.md','CURRICULUM_CATALOG.md','UI_UX_AUDIT.md','UI_REDESIGN_SPEC.md','UI_REDESIGN_REPORT.md','UI_LIBRARY_CORRECTION.md','PREVIEW_MAPCLASS_REPORT.md','HANDOVER.md'):
    shutil.copyfile(root/'docs'/name,dist/name)
    if name in ('UI_REDESIGN_REPORT.md','UI_LIBRARY_CORRECTION.md','PREVIEW_MAPCLASS_REPORT.md','HANDOVER.md'):
        report=(dist/name).read_text(encoding='utf-8').replace('../artifacts/','verification/')
        (dist/name).write_text(report,encoding='utf-8')
shutil.copytree(root/'examples',dist/'examples',dirs_exist_ok=True)
wysiwyg_report=root/'docs/WYSIWYG_IMPLEMENTATION_REPORT.md'
if wysiwyg_report.exists():shutil.copyfile(wysiwyg_report,dist/wysiwyg_report.name)
windowed_report=root/'docs/WINDOWED_BUILD_REPORT.md'
if windowed_report.exists():shutil.copyfile(windowed_report,dist/windowed_report.name)
icon_report=root/'docs/APP_ICON_BUILD_RETENTION_REPORT.md'
if icon_report.exists():shutil.copyfile(icon_report,dist/icon_report.name)
for name in ('LESSON_FILE_MODEL_REPORT.md','STABILIZATION_20261011_REPORT.md','IMPORT_WORKFLOW_IMPLEMENTATION_REPORT.md'):
    report=root/'docs'/name
    if report.exists():shutil.copyfile(report,dist/name)
verification=dist/'verification';verification.mkdir(exist_ok=True)
for name in ('stabilization-before.json','stabilization-after.json','latex-integration.json','windows-smoke.json','stabilization-import.png','stabilization-exam.png'):
    source=root/'artifacts'/name
    if source.exists():shutil.copyfile(source,verification/name)
if (root/'artifacts/ui-redesign').exists():shutil.copytree(root/'artifacts/ui-redesign',verification/'ui-redesign',dirs_exist_ok=True,ignore=shutil.ignore_patterns('zip-smoke.json'))
if (root/'artifacts/library-fix').exists():shutil.copytree(root/'artifacts/library-fix',verification/'library-fix',dirs_exist_ok=True)
if (root/'artifacts/mapclass-preview').exists():shutil.copytree(root/'artifacts/mapclass-preview',verification/'mapclass-preview',dirs_exist_ok=True,ignore=shutil.ignore_patterns('zip-smoke.json'))
if (root/'artifacts/formula-input-fix').exists():shutil.copytree(root/'artifacts/formula-input-fix',verification/'formula-input-fix',dirs_exist_ok=True,ignore=shutil.ignore_patterns('zip-smoke.json'))
if (root/'artifacts/windowed-build').exists():shutil.copytree(root/'artifacts/windowed-build',verification/'windowed-build',dirs_exist_ok=True,ignore=shutil.ignore_patterns('zip-smoke.json'))
if (root/'artifacts/app-icon').exists():shutil.copytree(root/'artifacts/app-icon',verification/'app-icon',dirs_exist_ok=True)
if (root/'artifacts/dashboard').exists():shutil.copytree(root/'artifacts/dashboard',verification/'dashboard',dirs_exist_ok=True)
if (root/'artifacts/import-workflow').exists():shutil.copytree(root/'artifacts/import-workflow',verification/'import-workflow',dirs_exist_ok=True)
if (root/'artifacts/stabilization-20261011').exists():shutil.copytree(root/'artifacts/stabilization-20261011',verification/'stabilization-20261011',dirs_exist_ok=True,ignore=shutil.ignore_patterns('zip-smoke.json','cleanup.json'))
licenses=dist/'licenses';licenses.mkdir(exist_ok=True)
versions={}
for package in ('PySide6','PySide6_Essentials','PySide6_Addons','shiboken6','PyMuPDF','PyInstaller'):
    info=metadata.distribution(package);versions[package]=info.version
    target=licenses/package;target.mkdir(exist_ok=True)
    (target/'METADATA.txt').write_text(info.read_text('METADATA') or '',encoding='utf-8')
    for file in info.files or []:
        if any(word in str(file).lower() for word in ('license','licence','copying')) and info.locate_file(file).is_file():
            relative=Path(str(file))
            if '..' in relative.parts:continue
            destination=target/relative;destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(info.locate_file(file),destination)
python_license=Path(sys.base_prefix)/'LICENSE.txt'
if python_license.exists():shutil.copyfile(python_license,licenses/'PYTHON_LICENSE.txt')
(dist/'THIRD_PARTY_NOTICES.md').write_text("""# Third-party components

Python runtime, Qt/PySide6, shiboken6, PyMuPDF and PyInstaller are included. License and copyright texts from installed distributions are in licenses/. PySide6 metadata lists LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only; PyMuPDF is AGPL-3.0 or Artifex Commercial License; PyInstaller has a bootloader exception. These files preserve dependency notices; they do not grant an additional commercial license. TeX Live is external and is not bundled.
""",encoding='utf-8')
manifest={'product':'LaTeX Question Studio','version':version,'architecture':'Windows x64','python':sys.version.split()[0],'dependencies':versions,'exe_sha256':hashlib.sha256(raw).hexdigest(),'pe_subsystem':subsystem,'windowed':True,'tests':args.test_count,'clean_windows_vm_tested':False,'config_and_tokens_bundled':False}
(dist/'release_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
release=args.output_dir;release.mkdir(parents=True,exist_ok=True)
archive=release/f'LaTeXQuestionStudio-{version}-win64.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for file in sorted(dist.rglob('*')):
        if file.is_file():z.write(file,Path('LaTeXQuestionStudio')/file.relative_to(dist))
checksum=hashlib.sha256(archive.read_bytes()).hexdigest()
(archive.with_suffix('.zip.sha256')).write_text(checksum+'  '+archive.name+'\n',encoding='ascii')
print('Release:',archive.name,'bytes:',archive.stat().st_size,'sha256:',checksum)
