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
import threading
from latex_question_studio.parsing.latex import commands, group, skip_space

BUILTIN_PREAMBLE = r"""\documentclass[12pt,a4paper]{article}
\usepackage[utf8]{vietnam}
\usepackage[margin=18mm]{geometry}
\usepackage{amsmath,amssymb,amsfonts,mathrsfs}
\usepackage{graphicx,xcolor,multicol,enumitem,tabularx,array}
\usepackage{tikz}
\usetikzlibrary{arrows,arrows.meta,calc,positioning,shapes,patterns,intersections}
\pagestyle{empty}
\newenvironment{ex}{\par\noindent\ignorespaces}{\par\medskip}
\newenvironment{vidu}{\par\noindent\ignorespaces}{\par\medskip}
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
\providecommand{\heva}[1]{\left\{\begin{aligned}#1\end{aligned}\right.}
\providecommand{\hoac}[1]{\left[\begin{aligned}#1\end{aligned}\right.}
\providecommand{\motcot}[4]{\begin{enumerate}[label=\Alph*.]\item #1\item #2\item #3\item #4\end{enumerate}}
\providecommand{\haicot}[4]{\begin{multicols}{2}\begin{enumerate}[label=\Alph*.]\item #1\item #2\item #3\item #4\end{enumerate}\end{multicols}}
\providecommand{\bacot}[4]{\begin{multicols}{3}\begin{enumerate}[label=\Alph*.]\item #1\item #2\item #3\item #4\end{enumerate}\end{multicols}}
\providecommand{\boncot}[4]{\begin{multicols}{4}\begin{enumerate}[label=\Alph*.]\item #1\item #2\item #3\item #4\end{enumerate}\end{multicols}}
\providecommand{\tab}{\hspace*{1.5em}}
\providecommand{\haidong}[2][]{}
\providecommand{\bondong}[2][]{}
\providecommand{\loai}[1]{}
\providecommand{\dapan}[1]{}
\providecommand{\nguon}[1]{}
\providecommand{\subject}{TOÁN}
\providecommand{\TieudeT}[1]{%
  \begin{center}%
  \begin{tabular}{p{0.36\textwidth}|p{0.58\textwidth}}%
    \centering \textbf{TRƯỜNG THPT} & \centering \textbf{\large #1} \tabularnewline%
    \centering \textbf{ĐỀ KIỂM TRA} & \centering Môn: \textbf{\subject} \tabularnewline%
    & \centering \textit{Thời gian làm bài: 90 phút}%
  \end{tabular}%
  \end{center}%
  \vspace{1em}%
}
\providecommand{\PhanI}{\bigskip\noindent\textbf{\large PHẦN I. Câu trắc nghiệm nhiều phương án lựa chọn}\par\medskip}
\providecommand{\PhanII}{\bigskip\noindent\textbf{\large PHẦN II. Câu trắc nghiệm đúng sai}\par\medskip}
\providecommand{\PhanIII}{\bigskip\noindent\textbf{\large PHẦN III. Câu trắc nghiệm trả lời ngắn}\par\medskip}
\providecommand{\PhanTL}{\bigskip\noindent\textbf{\large PHẦN IV. Tự luận}\par\medskip}
\providecommand{\dapsoTL}[2][]{\par\textbf{Đáp án: }#2}
\providecommand{\dapso}[2][]{\par\textbf{Đáp án: }#2}
\providecommand{\newenvironmentTF}{}
\providecommand{\Opensolutionfile}[2][]{}
\providecommand{\Closesolutionfile}[1]{}
\newenvironment{cauhoiTN}[1]{}{}
\newenvironment{cauhoiDS}[1]{}{}
\newenvironment{cauhoiTLN}[1]{}{}
\newenvironment{cauhoiTL}[1]{}{}
"""

MAPCLASS_PREAMBLE = r"""\documentclass[company=BookA4,pagesize=DethiA4,mausac=01,tuychon=GV1]{MAPClass}
\pagestyle{empty}
\providecommand{\nobox}{0}
\providecommand{\nameans}{}
\providecommand{\SttANS}{}
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
        self._active_processes = set()
        self._process_lock = threading.Lock()

    @property
    def profile_root(self):
        return self.preamble_file.parent if self.preamble_file else default_profile_root()

    def engine_path(self):
        return shutil.which(self.engine)

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
        if any(command.name == 'begin' and command.depth == 0 and group(preamble, command.end)[0] == 'document' for command in commands(preamble)):
            raise ValueError('Preamble phải kết thúc trước begin{document}')
        for root in roots:
            for suffix in ('*.cls','*.sty','*.tex'):
                for file in root.rglob(suffix):
                    dependencies[str(file.relative_to(self.profile_root))]=hashlib.sha256(file.read_bytes()).hexdigest()
        return preamble+"\n"+self.preamble_extra,dependencies

    def compile(self, source, assets=None, cancelled=lambda:False, progress=lambda a,b:None, extra_files=None):
        engine=shutil.which(self.engine)
        if not engine:return CompileResult(False,None,'Không tìm thấy pdfLaTeX. Cấu hình đường dẫn trong Cài đặt.')
        if cancelled():return CompileResult(False,None,'Đã hủy.',cancelled=True)
        assets=assets or {}
        extra_files=extra_files or {}
        try:
            preamble,dependencies=self.profile()
            stat=Path(engine).stat();engine_key=(str(Path(engine).resolve()),stat.st_mtime_ns,stat.st_size)
            version=self._engine_versions.get(engine_key)
            if version is None:
                version=subprocess.run([engine,'--version'],capture_output=True,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).stdout.decode('utf-8','replace').splitlines()[0]
                self._engine_versions[engine_key]=version
            asset_bytes={name:Path(path).read_bytes() for name,path in assets.items()}
            extra_file_hashes={name:hashlib.sha256(content.encode('utf-8') if isinstance(content,str) else content).hexdigest() for name,content in extra_files.items()}
            payload={'source':source,'preamble':preamble,'dependencies':dependencies,'assets':{n:hashlib.sha256(b).hexdigest() for n,b in asset_bytes.items()},'extra_files':extra_file_hashes,'engine':str(Path(engine).resolve()),'version':version,'flags':'no-shell-escape/haltonerror/full-document/v2'}
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
        with tempfile.TemporaryDirectory(prefix='compile-',dir=cache,ignore_cleanup_errors=True) as temporary:
            work=Path(temporary);(work/'assets').mkdir();(work/'Loigiai').mkdir(parents=True,exist_ok=True)
            for name,raw in asset_bytes.items():
                (work/'assets'/(hashlib.sha256(raw).hexdigest()+Path(assets[name]).suffix.lower())).write_bytes(raw)
            for rel_path,content in extra_files.items():
                target_file=work/rel_path
                target_file.parent.mkdir(parents=True,exist_ok=True)
                if isinstance(content,bytes):target_file.write_bytes(content)
                else:target_file.write_text(content,encoding='utf-8')
            if r'\documentclass' in rewritten:
                document = rewritten
            else:
                document = preamble + '\n\\begin{document}\n' + rewritten + '\n\\end{document}\n'
            (work/'preview.tex').write_text(document,encoding='utf-8')
            environment = os.environ.copy()
            environment['TEXINPUTS'] = (
                str(work).replace('\\', '/') + '//' + os.pathsep +
                str(self.root).replace('\\', '/') + '//' + os.pathsep +
                str(self.profile_root).replace('\\', '/') + '//' + os.pathsep +
                environment.get('TEXINPUTS', '')
            )
            log_path=work/'process.log'
            with log_path.open('wb') as stream:
                process=subprocess.Popen([engine,'-no-shell-escape','-interaction=nonstopmode','-halt-on-error','-file-line-error','preview.tex'],cwd=work,stdout=stream,stderr=subprocess.STDOUT,env=environment,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                with self._process_lock:
                    self._active_processes.add(process)
                deadline=time.monotonic()+self.timeout
                aborted=False
                try:
                    while process.poll() is None:
                        if cancelled() or time.monotonic()>deadline:
                            aborted=True
                            try:
                                process.kill()
                                if os.name == 'nt':
                                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True, timeout=1)
                                process.wait(timeout=2)
                            except Exception:
                                pass
                            break
                        time.sleep(.04)
                finally:
                    with self._process_lock:
                        self._active_processes.discard(process)
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

    def kill_all_active(self):
        """Immediately forces termination of all currently running compiler subprocesses."""
        with self._process_lock:
            procs = list(self._active_processes)
        for proc in procs:
            try:
                proc.kill()
                if os.name == 'nt':
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, timeout=1)
            except Exception:
                pass

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
    def render(pdf, page=0, scale=1.5, crop=True):
        import pymupdf
        from latex_question_studio.preview.crop import render_page
        with pymupdf.open(pdf) as document:
            target = document[page]
            raw_png = render_page(target, scale=scale, crop=crop)
            return raw_png, len(document)
