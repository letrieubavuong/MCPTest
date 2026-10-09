"""Read-only legacy corpus benchmark; writes only a separate temporary app data directory."""
from contextlib import closing
from pathlib import Path
from statistics import median
import json
import platform
import sqlite3
import sys
import tempfile
import time
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.importing import ImportService
from latex_question_studio.application.search import SearchService
from latex_question_studio.preview.compiler import Compiler

reference=Path(sys.argv[1]).resolve()
with closing(sqlite3.connect(reference.as_uri()+'?mode=ro',uri=True)) as c:
    rows=c.execute('SELECT STT,ND FROM DanhsachCH ORDER BY STT').fetchall()
Path('.runtime').mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='benchmark-',dir='.runtime') as temporary:
    root=Path(temporary).resolve();file=root/'legacy-ND-reconstructed.tex'
    file.write_text('\n\n'.join('\\begin{ex}\n'+row[1]+'\n\\end{ex}' for row in rows),encoding='utf-8')
    services=create_services(AppConfig.load(root/'app'));importer=ImportService(services)
    start=time.perf_counter();batch,results=importer.stage([file]);staging=time.perf_counter()-start
    start=time.perf_counter();count=importer.commit(batch);commit=time.perf_counter()-start
    search=SearchService(services);search_times=[];page_times=[]
    for i in range(30):
        start=time.perf_counter();search.find(['oxit','nguyên tử','phản ứng'][i%3]);search_times.append(time.perf_counter()-start)
        start=time.perf_counter();search.find(offset=(i*100)%max(count,1));page_times.append(time.perf_counter()-start)
    compiler=Compiler(root/'app');source=r'\begin{ex}Tính $2+2$.\choice{1}{2}{3}{\True 4}\loigiai{$2+2=4$.}\end{ex}'
    start=time.perf_counter();first=compiler.compile(source);compile_time=time.perf_counter()-start
    start=time.perf_counter();second=compiler.compile(source);cache_time=time.perf_counter()-start
    result={'platform':platform.platform(),'python':platform.python_version(),'corpus':'Actual legacy DanhsachCH.ND, wrapped in ex; not original source files','corpus_questions':len(rows),'parsed_items':len(results),'imported':count,'quarantined':len(results)-count,'stage_seconds':staging,'commit_seconds':commit,'search_median_ms':median(search_times)*1000,'search_max_ms':max(search_times)*1000,'page_median_ms':median(page_times)*1000,'page_max_ms':max(page_times)*1000,'preview_sample':'Synthetic valid MCQ; not full legacy compile corpus','preview_ok':first.ok,'preview_seconds':compile_time,'cache_hit':second.cache_hit,'cache_seconds':cache_time,'database_integrity':None}
    with services.database.connect() as c:result['database_integrity']=c.execute('PRAGMA integrity_check').fetchone()[0]
    Path('artifacts/phase08_benchmark.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))
