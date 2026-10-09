"""Synthetic-only benchmark. Does not open user data directories."""
from pathlib import Path
import sys,json,time,platform,sqlite3,statistics,uuid
from dataclasses import replace
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.library import LibraryService
from latex_question_studio.application.search import SearchService
from latex_question_studio.application.exams import ExamService
from latex_question_studio.application.importing import ImportService
from latex_question_studio.preview.compiler import Compiler
root=Path(__file__).resolve().parents[1];label=sys.argv[1];sizes=[int(v) for v in sys.argv[2:]] or [1000,10000,50000]
def timed(fn,repeats=1):
 vals=[]
 for _ in range(repeats):
  start=time.perf_counter();value=fn();vals.append(time.perf_counter()-start)
 return {'seconds':vals,'median':statistics.median(vals)},value
results={'label':label,'environment':{'platform':platform.platform(),'python':sys.version,'sqlite':sqlite3.sqlite_version},'sizes':{}}
for size in sizes:
 folder=root/'.runtime'/('benchmark-'+label+'-'+str(size)+'-'+uuid.uuid4().hex[:6]);s=create_services(AppConfig.load(folder));lib=LibraryService(s);search=SearchService(s);exam=ExamService(s)
 source=lambda i:r'\begin{ex}Câu tổng hợp '+str(i)+r' tính $x^2+'+str(i)+r'$.\loigiai{Minh họa}\end{ex}'
 start=time.perf_counter()
 with s.database.transaction() as c:
  c.executemany('INSERT INTO questions VALUES (?,?,?,?,?,?,?,?,?)',[(str(i),source(i),'essay','Minh họa',None,['NB','TH','VD','VDC'][i%4],1,'now','now') for i in range(size)])
  c.executemany('INSERT INTO question_metadata VALUES (?,?)',[(str(i),json.dumps({'subject':'Toán','grade':'10','taxonomy_id':'curriculum:math10:lesson:01','archived':i%100==99})) for i in range(size)])
  c.executemany('INSERT INTO question_taxonomy VALUES (?,?)',[(str(i),'curriculum:math10:lesson:01') for i in range(size)])
 metrics={'seed_seconds':time.perf_counter()-start}
 for name,fn in [('open_bank',lambda:search.find(limit=100)),('switch_lesson',lambda:search.find(taxonomy_id='curriculum:math10:lesson:01')),('search',lambda:search.find('tổng hợp 42')),('metadata',lambda:search.find(filters={'subject':'Toán','grade':'10','cognitive_level':'NB'})),('taxonomy',lib.taxonomy),('statistics_cold',lambda:exam.statistics('curriculum:math10')),('statistics_warm',lambda:exam.statistics('curriculum:math10')),('duplicates',lambda:search.duplicates('42',limit=10))]:
  metrics[name],_=timed(fn);print(label,size,name,round(metrics[name]['median'],4),flush=True)
 from PySide6.QtWidgets import QApplication
 from latex_question_studio.ui.main_window import MainWindow
 app=QApplication.instance() or QApplication([])
 metrics['startup'],window=timed(lambda:MainWindow(s));window.close();app.processEvents()
 file=folder/'batch.tex';file.write_text('\n'.join(source(i) for i in range(size)),encoding='utf-8');importer=ImportService(s)
 metrics['import_stage'],staged=timed(lambda:importer.stage([file]));metrics['import_commit'],_=timed(lambda:importer.commit(staged[0]))
 if label=='after' or size==sizes[0]:
  compiler=Compiler(folder);metrics['preview_cold'],compiled=timed(lambda:compiler.compile(source(42)))
  metrics['preview_cache'],cached=timed(lambda:compiler.compile(source(42)));metrics['preview_ok']=compiled.ok;metrics['cache_hit']=cached.cache_hit
  if compiled.ok:metrics['preview_render'],_=timed(lambda:compiler.render(compiled.pdf))
  if label=='after':
   metrics['preview_switch'],_=timed(lambda:compiler.compile(source(43)))
   metrics['preview_return'],_=timed(lambda:compiler.compile(source(42)))
   with s.database.connect() as c:
    join,where,params=search.query_parts(taxonomy_id='curriculum:math10')
    metrics['scope_query_plan']=[tuple(r) for r in c.execute('EXPLAIN QUERY PLAN SELECT q.id FROM questions q LEFT JOIN question_metadata m ON m.question_id=q.id'+join+' WHERE '+' AND '.join(where),params)]
    metrics['analysis_index_plan']=[tuple(r) for r in c.execute('EXPLAIN QUERY PLAN SELECT question_id FROM question_analysis WHERE normalized_hash=?',('synthetic',))]
 results['sizes'][str(size)]=metrics
 out=root/'artifacts'/('stabilization-'+label+'.json');out.parent.mkdir(exist_ok=True);out.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
 print('Completed',label,size,flush=True)
