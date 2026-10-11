"""Verify current UI bytecode and smoke the actual Windows bundle or extracted ZIP."""
from pathlib import Path
import argparse,subprocess,sqlite3,json,uuid,types,hashlib,zipfile,tomllib,struct
import pefile
from PyInstaller.archive.readers import CArchiveReader, ZlibArchiveReader
from latex_question_studio.persistence.database import SCHEMA_VERSION
root=Path(__file__).resolve().parents[1];version=tomllib.loads((root/'pyproject.toml').read_text(encoding='utf-8'))['project']['version'];parser=argparse.ArgumentParser();parser.add_argument('--zip',type=Path);parser.add_argument('--dist-dir',type=Path);parser.add_argument('--pyz',type=Path);parser.add_argument('--output-dir',type=Path,default=root/'artifacts/ui-redesign');args=parser.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
folder=root/'.runtime'/('ui-smoke-'+uuid.uuid4().hex[:8]);bundle=args.dist_dir or root/'dist'/version/'LaTeXQuestionStudio'
if args.zip:
 extracted=root/'.runtime'/('ui-zip-'+uuid.uuid4().hex[:8]);extracted.mkdir()
 with zipfile.ZipFile(args.zip) as archive:
  for name in archive.namelist():
   if not (extracted/name).resolve().is_relative_to(extracted.resolve()):raise ValueError('Invalid ZIP path')
  archive.extractall(extracted)
 bundle=next(extracted.rglob('LaTeXQuestionStudio.exe')).parent
exe=bundle/'LaTeXQuestionStudio.exe';raw=exe.read_bytes();pe_offset=struct.unpack_from('<I',raw,60)[0]
subsystem=struct.unpack_from('<H',raw,pe_offset+24+68)[0]
assert subsystem==2,'Expected a Windows GUI executable without a console'
p=subprocess.run([str(exe),'--smoke-test','--smoke-delay-ms','2000','--data-dir',str(folder)],capture_output=True,timeout=30)
report={'version':version,'exit_code':p.returncode,'stderr':p.stderr.decode('utf-8','replace')[-1500:],'exe_sha256':hashlib.sha256(raw).hexdigest(),'pe_subsystem':subsystem,'windowed':subsystem==2,'console_suppression_used':False}
icon=(root/'src/latex_question_studio/ui/assets/mcptest.ico').read_bytes()
count=struct.unpack_from('<H',icon,4)[0];expected=[]
for index in range(count):
 size,offset=struct.unpack_from('<II',icon,6+16*index+8);expected.append(icon[offset:offset+size])
with pefile.PE(str(exe)) as pe:
 embedded=[]
 for resource in pe.DIRECTORY_ENTRY_RESOURCE.entries:
  if resource.id==3:
   for image in resource.directory.entries:
    for language in image.directory.entries:
     data=language.data.struct;embedded.append(pe.get_data(data.OffsetToData,data.Size))
report['exe_icon_current']=len(embedded)==len(expected) and sorted(hashlib.sha256(value).hexdigest() for value in embedded)==sorted(hashlib.sha256(value).hexdigest() for value in expected)
bundled_icon=bundle/'_internal/latex_question_studio/ui/assets/mcptest.ico'
report['application_icon_current']=bundled_icon.is_file() and bundled_icon.read_bytes()==icon
report['icon_sizes']=count
db=list(folder.rglob('*.sqlite*'))+list(folder.rglob('*.db'))
if db:
 with sqlite3.connect(db[0]) as c:report.update(integrity=c.execute('PRAGMA integrity_check').fetchone()[0],schema=c.execute('PRAGMA user_version').fetchone()[0],taxonomy_nodes=c.execute('SELECT count(*) FROM taxonomy_nodes').fetchone()[0])
def sig(code):return code.co_code,code.co_names,code.co_varnames,code.co_argcount,code.co_kwonlyargcount,tuple(sig(v) if isinstance(v,types.CodeType) else v for v in code.co_consts)
package=CArchiveReader(str(exe));archive=package.open_embedded_archive(next(name for name,entry in package.toc.items() if entry[-1]=='z'));matches={};missing=[]
for path in (root/'src/latex_question_studio').rglob('*.py'):
 if path.name in ('__init__.py','__main__.py'):continue
 name='.'.join(path.relative_to(root/'src').with_suffix('').parts)
 if name in archive.toc:matches[name]=sig(archive.extract(name))==sig(compile(path.read_text(encoding='utf-8'),str(path),'exec'))
 else:missing.append(name)
ui_matches={name:ok for name,ok in matches.items() if name.startswith('latex_question_studio.ui.')}
report['ui_modules_current']=all(ui_matches.values());report['ui_modules_checked']=len(ui_matches)
report['all_modules_current']=all(matches.values());report['modules_checked']=len(matches);report['source_modules_not_bundled']=missing
report['bytecode_read_from']='executable'
if args.pyz:
 work_archive=ZlibArchiveReader(str(args.pyz))
 assert all(name in work_archive.toc and sig(work_archive.extract(name))==sig(archive.extract(name)) for name in matches),'Build PYZ differs from executable'
if args.zip:
 report['zip_sha256']=hashlib.sha256(args.zip.read_bytes()).hexdigest();report['zip_size']=args.zip.stat().st_size
 report['bundled_user_database']=bool(list(bundle.rglob('*.sqlite*'))+list(bundle.rglob('*.db')))
 report['bundled_secret_config']=bool(list(bundle.rglob('config.json')))
name='zip-smoke.json' if args.zip else 'windows-smoke.json';(args.output_dir/name).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False))
assert p.returncode==0 and report.get('integrity')=='ok' and report.get('schema')==SCHEMA_VERSION and report['all_modules_current'] and report['exe_icon_current'] and report['application_icon_current']
assert missing==['latex_question_studio.ui.metadata_dialog'],'Unexpected application module missing from bundle'
if args.zip:assert not report['bundled_user_database'] and not report['bundled_secret_config']
