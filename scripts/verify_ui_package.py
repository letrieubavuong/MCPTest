"""Verify current UI bytecode and smoke the actual Windows bundle or extracted ZIP."""
from pathlib import Path
import argparse,subprocess,sqlite3,json,uuid,types,hashlib,zipfile,tomllib
from PyInstaller.archive.readers import ZlibArchiveReader
root=Path(__file__).resolve().parents[1];version=tomllib.loads((root/'pyproject.toml').read_text(encoding='utf-8'))['project']['version'];parser=argparse.ArgumentParser();parser.add_argument('--zip',type=Path);parser.add_argument('--output-dir',type=Path,default=root/'artifacts/ui-redesign');args=parser.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
folder=root/'.runtime'/('ui-smoke-'+uuid.uuid4().hex[:8]);bundle=root/'dist'/version/'LaTeXQuestionStudio'
if args.zip:
 extracted=root/'.runtime'/('ui-zip-'+uuid.uuid4().hex[:8]);extracted.mkdir()
 with zipfile.ZipFile(args.zip) as archive:
  for name in archive.namelist():
   if not (extracted/name).resolve().is_relative_to(extracted.resolve()):raise ValueError('Invalid ZIP path')
  archive.extractall(extracted)
 bundle=next(extracted.rglob('LaTeXQuestionStudio.exe')).parent
exe=bundle/'LaTeXQuestionStudio.exe';p=subprocess.run([str(exe),'--smoke-test','--smoke-delay-ms','2000','--data-dir',str(folder)],capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
report={'version':version,'exit_code':p.returncode,'stderr':p.stderr.decode('utf-8','replace')[-1500:],'exe_sha256':hashlib.sha256(exe.read_bytes()).hexdigest()}
db=list(folder.rglob('*.sqlite*'))+list(folder.rglob('*.db'))
if db:
 with sqlite3.connect(db[0]) as c:report.update(integrity=c.execute('PRAGMA integrity_check').fetchone()[0],schema=c.execute('PRAGMA user_version').fetchone()[0],taxonomy_nodes=c.execute('SELECT count(*) FROM taxonomy_nodes').fetchone()[0])
def sig(code):return code.co_code,code.co_names,code.co_varnames,code.co_argcount,code.co_kwonlyargcount,tuple(sig(v) if isinstance(v,types.CodeType) else v for v in code.co_consts)
archive=ZlibArchiveReader(str(root/'.runtime/pyinstaller/LaTeXQuestionStudio/PYZ-00.pyz'));matches={}
for path in (root/'src/latex_question_studio/ui').rglob('*.py'):
 if path.name=='__init__.py':continue
 name='.'.join(path.relative_to(root/'src').with_suffix('').parts)
 if name in archive.toc:matches[name]=sig(archive.extract(name))==sig(compile(path.read_text(encoding='utf-8'),str(path),'exec'))
report['ui_modules_current']=all(matches.values());report['ui_modules_checked']=len(matches)
if args.zip:
 report['zip_sha256']=hashlib.sha256(args.zip.read_bytes()).hexdigest();report['zip_size']=args.zip.stat().st_size
 report['bundled_user_database']=bool(list(bundle.rglob('*.sqlite*'))+list(bundle.rglob('*.db')))
 report['bundled_secret_config']=bool(list(bundle.rglob('config.json')))
name='zip-smoke.json' if args.zip else 'windows-smoke.json';(args.output_dir/name).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(report,ensure_ascii=False))
assert p.returncode==0 and report.get('integrity')=='ok' and report['ui_modules_current']
if args.zip:assert not report['bundled_user_database'] and not report['bundled_secret_config']
