"""Measure parser/resolver cost on synthetic LaTeX corpora without user data."""
from pathlib import Path
import argparse
import json
import shutil
import tempfile
import time
import tracemalloc

from latex_question_studio.application.assets import AssetResolver
from latex_question_studio.parsing.latex import parse_questions


parser=argparse.ArgumentParser();parser.add_argument('--counts',default='1000,10000,50000');parser.add_argument('--output',type=Path,default=Path('artifacts/asset-benchmark.json'));args=parser.parse_args()
results=[]
with tempfile.TemporaryDirectory(prefix='asset-benchmark-') as temporary:
    root=Path(temporary);(root/'images').mkdir();(root/'images/image.png').write_bytes(b'benchmark image')
    for count in (int(value) for value in args.counts.split(',')):
        source='\\graphicspath{{images/}}\n'+'\n'.join(f'\\begin{{ex}}Question {i}\\includegraphics{{image.png}}\\end{{ex}}' for i in range(count))
        tracemalloc.start();started=time.perf_counter();items=parse_questions(source);parse_seconds=time.perf_counter()-started
        started=time.perf_counter();graph=AssetResolver().resolve(source,root/'questions.tex');resolve_seconds=time.perf_counter()-started
        _,peak=tracemalloc.get_traced_memory();tracemalloc.stop()
        results.append({'questions':count,'parse_seconds':round(parse_seconds,4),'resolve_seconds':round(resolve_seconds,4),'peak_bytes':peak,'references':len(graph.references),'ready':graph.ready})
        print(json.dumps(results[-1],ensure_ascii=False),flush=True)
args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps({'method':'synthetic direct ex questions with one shared PNG','results':results},ensure_ascii=False,indent=2),encoding='utf-8')
