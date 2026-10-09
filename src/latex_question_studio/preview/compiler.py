from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import time
import sys
from latex_question_studio.parsing.latex import commands, group, skip_space

BUILTIN_PREAMBLE = r"""\documentclass[12pt,a4paper]{article}
\usepackage[utf8]{vietnam}
\usepackage[margin=18mm]{geometry}
\usepackage{amsmath,amssymb,graphicx,tikz,enumitem}
\usetikzlibrary{arrows,arrows.meta,calc,positioning,shapes,patterns}
\pagestyle{empty}
\newenvironment{ex}{\par\noindent}{\par\medskip}
\newenvironment{vidu}{\par\noindent}{\par\medskip}
\newenvironment{ex*}{\begin{ex}}{\end{ex}}
\newenvironment{vidu*}{\begin{vidu}}{\end{vidu}}
\newenvironment{listEX}[1][1]{\begin{enumerate}}{\end{enumerate}}
\newcommand{\True}{\textbf{*}}
\newcommand{\choice}[4]{\begin{enumerate}[label=\Alph*.]\item #1\item #2\item #3\item #4\end{enumerate}}
\newcommand{\choiceTF}[4]{\begin{enumerate}[label=\alph*)]\item #1\item #2\item #3\item #4\end{enumerate}}
\let\choiceTFt\choiceTF
\newcommand{\shortans}[2][]{\par\textbf{Đáp án: }#2}
\newcommand{\loigiai}[1]{\par\textbf{Lời giải. }#1}
\let\hdan\loigiai
"""

MAPCLASS_PREAMBLE = r"""\documentclass[company=BookA4,pagesize=DethiA4,mausac=01,tuychon=GV1]{MAPClass}
\pagestyle{empty}
\AtBeginDocument{\showansEX{ex}}
"""

def default_profile_root():
    """Use the author-provided files live in a checkout, bundled copies in an EXE."""
    docs = Path(__file__).resolve().parents[3] / 'docs'
    if not getattr(sys, 'frozen', False) and (docs / 'Class/MAPClass.cls').is_file():
        return docs
    return Path(__file__).resolve().parent / 'data'

@dataclass(frozen=True)
class CompileResult:
    ok: bool
    pdf: Path | None
    log: str
    cache_hit: bool = False
    cancelled: bool = False

class Compiler:
    _engine_versions = {}
    def __init__(self, data_dir, engine='pdflatex', preamble_file=None, timeout=45, cache_limit=300*1024*1024, preamble_extra=""):
        self.preamble_extra=preamble_extra
        self.root=Path(data_dir)
        self.engine=engine
        self.preamble_file=Path(preamble_file) if preamble_file else None
        self.timeout=timeout
        self.cache_limit=cache_limit

    @property
    def profile_root(self):
        return self.preamble_file.parent if self.preamble_file else default_profile_root()

    def profile(self):
        dependencies={}
        if self.preamble_file:
            preamble=self.preamble_file.read_text(encoding='utf-8-sig')
            roots=[self.profile_root]
        else:
            preamble=MAPCLASS_PREAMBLE
            roots=[self.profile_root/'Class', self.profile_root/'Packages']
            for relative in ('Class/MAPClass.cls','Packages/ex_test.sty'):
                if not (self.profile_root/relative).is_file():
                    raise FileNotFoundError('Thiếu tài nguyên preview: '+relative)
        if r'\begin{document}' in preamble:
            raise ValueError('Preamble phải kết thúc trước begin{document}')
        for root in roots:
            for suffix in ('*.cls','*.sty','*.tex'):
                for file in root.rglob(suffix):
                    dependencies[str(file.relative_to(self.profile_root))]=hashlib.sha256(file.read_bytes()).hexdigest()
        return preamble+"\n"+self.preamble_extra,dependencies

    def compile(self, source, assets=None, cancelled=lambda:False, progress=lambda a,b:None):
        engine=shutil.which(self.engine)
        if not engine:return CompileResult(False,None,'Không tìm thấy pdfLaTeX. Cấu hình đường dẫn trong Cài đặt.')
        if cancelled():return CompileResult(False,None,'Đã hủy.',cancelled=True)
        assets=assets or {}
        try:
            preamble,dependencies=self.profile()
            stat=Path(engine).stat();engine_key=(str(Path(engine).resolve()),stat.st_mtime_ns,stat.st_size)
            version=self._engine_versions.get(engine_key)
            if version is None:
                version=subprocess.run([engine,'--version'],capture_output=True,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).stdout.decode('utf-8','replace').splitlines()[0]
                self._engine_versions[engine_key]=version
            asset_bytes={name:Path(path).read_bytes() for name,path in assets.items()}
            payload={'source':source,'preamble':preamble,'dependencies':dependencies,'assets':{n:hashlib.sha256(b).hexdigest() for n,b in asset_bytes.items()},'engine':str(Path(engine).resolve()),'version':version,'flags':'no-shell-escape/haltonerror/full-document/v1'}
            key=hashlib.sha256(json.dumps(payload,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
        except Exception as error:return CompileResult(False,None,'Cấu hình hoặc tài nguyên không hợp lệ: '+str(error))
        cache=self.root/'cache';cache.mkdir(parents=True,exist_ok=True)
        output=cache/(key+'.pdf')
        if output.exists():
            output.touch()
            return CompileResult(True,output,'Preview từ cache.',True)
        replacements=[]
        try:
            for command in commands(source):
                if command.name!='includegraphics':continue
                cursor=skip_space(source,command.end)
                if cursor<len(source) and source[cursor]=='*':cursor=skip_space(source,cursor+1)
                if cursor<len(source) and source[cursor]=='[':_,cursor,_=group(source,cursor,'[',']')
                reference,end,start=group(source,cursor)
                if reference not in assets:return CompileResult(False,None,'Thiếu tài nguyên: '+reference)
                filename='assets/'+hashlib.sha256(asset_bytes[reference]).hexdigest()+Path(assets[reference]).suffix.lower()
                replacements.append((start+1,end-1,filename))
        except ValueError as error:return CompileResult(False,None,str(error))
        rewritten=source
        for start,end,value in reversed(replacements):rewritten=rewritten[:start]+value+rewritten[end:]
        with tempfile.TemporaryDirectory(prefix='compile-',dir=cache) as temporary:
            work=Path(temporary);(work/'assets').mkdir()
            for name,raw in asset_bytes.items():
                (work/'assets'/(hashlib.sha256(raw).hexdigest()+Path(assets[name]).suffix.lower())).write_bytes(raw)
            document=preamble+'\n\\begin{document}\n'+rewritten+'\n\\end{document}\n'
            (work/'preview.tex').write_text(document,encoding='utf-8')
            environment=os.environ.copy()
            environment['TEXINPUTS']=str(self.profile_root).replace('\\','/')+'//'+os.pathsep+environment.get('TEXINPUTS','')
            log_path=work/'process.log'
            with log_path.open('wb') as stream:
                process=subprocess.Popen([engine,'-no-shell-escape','-interaction=nonstopmode','-halt-on-error','-file-line-error','preview.tex'],cwd=work,stdout=stream,stderr=subprocess.STDOUT,env=environment,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                deadline=time.monotonic()+self.timeout
                aborted=False
                while process.poll() is None:
                    if cancelled() or time.monotonic()>deadline:
                        aborted=True;process.kill();process.wait(timeout=5);break
                    time.sleep(.04)
            log=log_path.read_text(encoding='utf-8',errors='replace')[-24000:]
            line_offset=preamble.count('\n')+2
            import re
            log=re.sub(r'preview\.tex:(\d+)',lambda m:f"source:{max(1,int(m[1])-line_offset)}",log)
            if aborted:return CompileResult(False,None,('Đã hủy.' if cancelled() else 'Hết thời gian biên dịch.')+'\n'+log,cancelled=cancelled())
            pdf=work/'preview.pdf'
            if process.returncode!=0 or not pdf.exists():return CompileResult(False,None,log)
            temp_output=output.with_name(output.name+'.'+__import__('uuid').uuid4().hex+'.tmp');shutil.copyfile(pdf,temp_output);temp_output.replace(output)
        self.trim_cache(output)
        return CompileResult(True,output,log)

    def trim_cache(self, keep=None):
        files=sorted((self.root/'cache').glob('*.pdf'),key=lambda p:p.stat().st_mtime)
        size=sum(p.stat().st_size for p in files)
        for file in files:
            if size<=self.cache_limit:break
            if file!=keep:
                try:
                    length=file.stat().st_size;file.unlink(missing_ok=True);size-=length
                except OSError:continue

    @staticmethod
    def render(pdf, page=0, scale=1.5):
        import pymupdf
        with pymupdf.open(pdf) as document:
            target=document[page]
            rectangles=[pymupdf.Rect(block[:4]) for block in target.get_text('blocks')]
            rectangles += [drawing['rect'] for drawing in target.get_drawings()]
            clip=None
            for rectangle in rectangles:
                clip=rectangle if clip is None else clip|rectangle
            if clip is not None:clip=(clip+(-12,-12,12,12))&target.rect
            return target.get_pixmap(matrix=pymupdf.Matrix(scale,scale),clip=clip).tobytes('png'),len(document)
