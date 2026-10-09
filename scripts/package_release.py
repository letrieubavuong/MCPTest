from pathlib import Path
import hashlib
import importlib.metadata as metadata
import json
import shutil
import struct
import sys
import zipfile

root=Path(__file__).resolve().parents[1]
dist=root/'dist/LaTeXQuestionStudio'
exe=dist/'LaTeXQuestionStudio.exe'
raw=exe.read_bytes()
if raw[:2] != b'MZ': raise RuntimeError('Invalid executable header')
offset=struct.unpack_from('<I',raw,60)[0]
if struct.unpack_from('<H',raw,offset+4)[0]!=0x8664:raise RuntimeError('Refusing to package a non-x64 executable')
for name in ('USER_GUIDE.md','TROUBLESHOOTING.md','RELEASE_NOTES.md','18_LESSON_AUTHORING_SPEC.md','19_LESSON_IMPLEMENTATION_REPORT.md','20_KHTN6_CURRICULUM_REPORT.md'):
    shutil.copyfile(root/'docs'/name,dist/name)
shutil.copytree(root/'examples',dist/'examples',dirs_exist_ok=True)
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
manifest={'product':'LaTeX Question Studio','version':'0.2.5','architecture':'Windows x64','python':sys.version.split()[0],'dependencies':versions,'exe_sha256':hashlib.sha256(raw).hexdigest(),'tests':49,'clean_windows_vm_tested':False,'config_and_tokens_bundled':False}
(dist/'release_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
release=root/'release';release.mkdir(exist_ok=True)
archive=release/'LaTeXQuestionStudio-0.2.5-win64.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
    for file in sorted(dist.rglob('*')):
        if file.is_file():z.write(file,Path('LaTeXQuestionStudio')/file.relative_to(dist))
checksum=hashlib.sha256(archive.read_bytes()).hexdigest()
(archive.with_suffix('.zip.sha256')).write_text(checksum+'  '+archive.name+'\n',encoding='ascii')
print('Release:',archive.name,'bytes:',archive.stat().st_size,'sha256:',checksum)
