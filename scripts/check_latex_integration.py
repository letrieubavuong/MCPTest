"""Use repository profiles verbatim; report dependency failures, never patch packages."""
from pathlib import Path
import shutil,json,re,subprocess,time
from latex_question_studio.preview.compiler import Compiler
from latex_question_studio.application.lessons import student_source
root=Path(__file__).resolve().parents[1];folder=root/'.runtime/integration-ex-test';folder.mkdir(parents=True,exist_ok=True)
for rel in ('Class/MAPClass.cls','Packages/ex_test.sty'):
 target=folder/rel;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy(root/'docs'/rel,target)
source=r'\begin{ex}Synthetic $\frac{1}{2}$\choice{a}{\True b}{c}{d}\loigiai{TEACHERSECRET}\end{ex}'+ '\n'+r'\begin{ex}TF\choiceTF{\True a}{b}{\True c}{d}\loigiai{TEACHERSECRET}\end{ex}'+ '\n'+r'\begin{ex}TFt\choiceTFt{a}{\True b}{c}{\True d}\end{ex}'+ '\n'+r'\begin{ex}Short\shortans{42}\loigiai{TEACHERSECRET}\end{ex}'
profiles={'article_ex_test':r'\documentclass{article}\usepackage{amsmath,amssymb,fontawesome,colortbl}\usepackage[loigiai]{ex_test}\definecolor{Mapcolor}{RGB}{0,0,0}', 'MAPClass_ex_test':r'\documentclass[company=BookA4,pagesize=DethiA4,mausac=01,tuychon=GV1]{MAPClass}'}
results={}
for name,preamble in profiles.items():
 path=folder/(name+'.tex');path.write_text(preamble+r'\AtBeginDocument{\showansEX{ex}}',encoding='utf-8');compiler=Compiler(folder/name,preamble_file=path,timeout=45)
 results[name]={}
 for audience,body in [('teacher',source),('student',student_source(source,hide_answers=True))]:
  path.write_text(preamble+(r'\AtBeginDocument{\showansEX{ex}}' if audience=='teacher' else r'\AtBeginDocument{\hideansEX{ex}}'),encoding='utf-8')
  start=time.perf_counter();r=compiler.compile(body);(root/'artifacts'/f'{name}-{audience}.log').write_text(r.log,encoding='utf-8')
  entry={'status':'PASS' if r.ok else 'BLOCKED','seconds':time.perf_counter()-start,'missing_files':re.findall(r"File `([^']+)' not found",r.log),'pdf':str(r.pdf) if r.ok else None}
  if r.ok:
   import pymupdf
   with pymupdf.open(r.pdf) as doc:text=''.join(p.get_text() for p in doc)
   entry['teacher_secret_present']='TEACHERSECRET' in text
   if audience=='student' and entry['teacher_secret_present']:entry['status']='FAIL'
   if audience=='teacher' and not entry['teacher_secret_present']:entry['status']='BLOCKED';entry['reason']='Teacher solution not visible in actual PDF'
  if not r.ok:entry['error_tail']=r.log[-1800:]
  results[name][audience]=entry
out=root/'artifacts/latex-integration.json';out.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(results,ensure_ascii=True,indent=2))
