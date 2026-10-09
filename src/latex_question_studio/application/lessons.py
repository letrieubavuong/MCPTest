"""Versioned lesson documents; bank references are pinned, never live content."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import random
import shutil
import tempfile
import uuid
from latex_question_studio.application.search import SearchService
from latex_question_studio.parsing.latex import commands, group, skip_space, parse_questions
from latex_question_studio.preview.compiler import Compiler

KINDS = {'theory':'Lý thuyết', 'method':'Dạng toán / Phương pháp', 'example':'Ví dụ',
         'exercise':'Bài tập vận dụng', 'section':'Nhóm nội dung'}
POLICIES = {'full':'Hiện đầy đủ', 'question':'Chỉ đề bài', 'private':'Chỉ giáo viên'}


def stamp():
    return datetime.now(timezone.utc).isoformat()


def block(kind, title, parent=None, source=''):
    return {'id':str(uuid.uuid4()), 'parent':parent, 'kind':kind, 'title':title,
            'source':source, 'policy':'question' if kind=='exercise' else 'full',
            'assets':{}, 'question':None, 'teacher_notes':''}


def tex_text(text):
    escapes={'\\':r'\textbackslash{}', '&':r'\&', '%':r'\%', '$':r'\$', '#':r'\#',
             '_':r'\_', '{':r'\{', '}':r'\}', '~':r'\textasciitilde{}', '^':r'\textasciicircum{}'}
    return ''.join(escapes.get(c,c) for c in text)


def without_comments(source):
    lines=[]
    for line in source.splitlines():
        for i,c in enumerate(line):
            if c=='%':
                j=i-1
                while j>=0 and line[j]=='\\':j-=1
                if (i-j-1)%2==0:
                    line=line[:i];break
        lines.append(line)
    return '\n'.join(lines)


# Student source uses the explicitly supported built-in vocabulary. Unknown
# macros/definitions must be reviewed instead of claiming their answers are hidden.
STUDENT_COMMANDS=set(('begin end choice choiceTF choiceTFt True shortans loigiai hdan '
    'frac dfrac tfrac sqrt left right text textrm textbf textit emph underline '
    'sin cos tan cot log ln exp lim max min sum prod int iint infty partial prime '
    'alpha beta gamma delta theta lambda mu pi sigma omega Delta Omega '
    'cdot times div pm mp le leq ge geq ne neq approx equiv in notin subset '
    'subseteq cup cap emptyset forall exists mathbb mathcal mathrm mathbf '
    'vec overrightarrow overline hat bar underbrace overbrace displaystyle '
    'quad qquad hspace vspace smallskip medskip bigskip par noindent '
    'includegraphics linewidth textwidth textheight item label ref pageref dots ldots cdots vdots ddots '
    'draw node path fill filldraw coordinate foreach newpage clearpage '
    'centering caption multicolumn hline cline to mapsto longrightarrow '
    'Rightarrow Leftrightarrow perp parallel angle degree').split())


def student_source(source, hide_answers=False):
    source=without_comments(source)
    edits=[]
    for cmd in commands(source):
        if cmd.name not in STUDENT_COMMANDS and not (len(cmd.name)==1 and not cmd.name.isalpha()):
            raise ValueError('Macro chưa được chứng nhận cho source học sinh: \\' + cmd.name)
        if not hide_answers:continue
        if cmd.name=='True':edits.append((cmd.start,cmd.end,''))
        elif cmd.name in ('loigiai','hdan','shortans'):
            cursor=skip_space(source,cmd.end)
            if cmd.name=='shortans' and cursor<len(source) and source[cursor]=='[':
                _,cursor,_=group(source,cursor,'[',']')
            _,end,_=group(source,cursor)
            edits.append((cmd.start,end,''))
    # Nested answer macros are swallowed by their enclosing removed group.
    boundary=-1;selected=[]
    for start,end,replacement in sorted(edits):
        if start>=boundary:selected.append((start,end,replacement));boundary=end
    for start,end,replacement in reversed(selected):source=source[:start]+replacement+source[end:]
    return source


class LessonService:
    def __init__(self, services):
        self.services=services
        self.root=services.config.data_dir

    def list(self):
        with self.services.database.connect() as c:
            return [dict(r) for r in c.execute('SELECT id,title,revision,updated_at FROM lessons ORDER BY updated_at DESC')]

    def get(self, lesson_id):
        with self.services.database.connect() as c:
            row=c.execute('SELECT document_json FROM lessons WHERE id=?',(lesson_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def create(self, title='Bài giảng mới'):
        theory=block('theory','A. Lý thuyết')
        method=block('method','Dạng 1: Phương pháp giải')
        example=block('example','Ví dụ 1',method['id'])
        exercises=block('section','B. Bài tập vận dụng')
        doc={'id':str(uuid.uuid4()),'title':title,'revision':0,'subject':'Toán','grade':'12',
             'blocks':[theory,method,example,exercises],'recipes':[]}
        return self.save(doc)

    def validate(self, doc):
        if not doc['title'].strip():raise ValueError('Tên bài không được rỗng')
        blocks=doc['blocks'];ids=[b['id'] for b in blocks]
        if len(ids)!=len(set(ids)):raise ValueError('ID khối bị lặp')
        nodes={b['id']:b for b in blocks}
        for b in blocks:
            if b['kind'] not in KINDS or b['policy'] not in POLICIES:raise ValueError('Loại khối hoặc chính sách không hợp lệ')
            seen={b['id']};parent=b['parent']
            while parent is not None:
                if parent not in nodes or parent in seen:raise ValueError('Cây bài giảng không hợp lệ')
                seen.add(parent);parent=nodes[parent]['parent']

    def save(self, doc):
        self.validate(doc);saved=deepcopy(doc);saved['revision']+=1
        payload=json.dumps(saved,ensure_ascii=False);now=stamp()
        with self.services.database.transaction() as c:
            row=c.execute('SELECT revision FROM lessons WHERE id=?',(doc['id'],)).fetchone()
            if row is None:
                if doc['revision']!=0:raise ValueError('Bài không còn tồn tại')
                c.execute('INSERT INTO lessons VALUES (?,?,?,?,?)',(doc['id'],saved['title'],1,payload,now))
            else:
                if row[0]!=doc['revision']:raise ValueError('Bài đã thay đổi ở nơi khác; mở lại trước khi lưu')
                c.execute('UPDATE lessons SET title=?,revision=?,document_json=?,updated_at=? WHERE id=?',(saved['title'],saved['revision'],payload,now,doc['id']))
            c.execute('INSERT INTO lesson_revisions VALUES (?,?,?,?)',(doc['id'],saved['revision'],payload,now))
        return saved

    def history(self, lesson_id):
        with self.services.database.connect() as c:
            return [dict(r) for r in c.execute('SELECT revision,created_at FROM lesson_revisions WHERE lesson_id=? ORDER BY revision DESC',(lesson_id,))]

    def restore(self, lesson_id, revision):
        current=self.get(lesson_id)
        with self.services.database.connect() as c:
            row=c.execute('SELECT document_json FROM lesson_revisions WHERE lesson_id=? AND revision=?',(lesson_id,revision)).fetchone()
        if not row:raise ValueError('Không có phiên bản này')
        old=json.loads(row[0]);old['revision']=current['revision']
        return self.save(old)

    def question_block(self, question_id, kind='exercise', parent=None):
        q=self.services.questions.get(question_id)
        if not q:raise ValueError('Câu hỏi không còn tồn tại')
        parsed=parse_questions(q.latex_source)
        if len(parsed)!=1 or parsed[0].diagnostics:raise ValueError('Câu chưa phân tích hợp lệ; sửa trước khi chèn')
        b=block(kind, KINDS[kind]+' • '+question_id[:8], parent, q.latex_source)
        b['question']={'id':q.id,'revision':q.revision,'original_source':q.latex_source}
        with self.services.database.connect() as c:
            for row in c.execute('SELECT qa.original_reference,a.relative_path,a.content_hash FROM question_assets qa JOIN assets a ON a.id=qa.asset_id WHERE qa.question_id=?',(q.id,)):
                b['assets'][row['original_reference']]={'path':row['relative_path'],'hash':row['content_hash']}
        return b

    def insert_questions(self, doc, ids, kind='exercise', parent=None, allow_repeat=False):
        present={b['question']['id'] for b in doc['blocks'] if b.get('question')}
        if len(ids)!=len(set(ids)) or (not allow_repeat and present.intersection(ids)):
            raise ValueError('Câu đã có trong bài; chỉ cho phép lặp khi bạn chọn rõ tùy chọn đó')
        additions=[self.question_block(qid,kind,parent) for qid in ids]
        candidate=deepcopy(doc);candidate['blocks'].extend(additions);self.validate(candidate)
        return candidate

    def select(self, doc, text='', filters=None, count=1, seed=2027, allow_repeat=False):
        if not 1<=count<=100:raise ValueError('Số câu cần lấy từ 1 đến 100')
        present={b['question']['id'] for b in doc['blocks'] if b.get('question')}
        search=SearchService(self.services);rows=[];offset=0
        while True:
            page=search.find(text,filters or {},limit=500,offset=offset)
            rows.extend(q.id for q in page if allow_repeat or q.id not in present)
            if len(page)<500:break
            offset+=500
        if len(rows)<count:raise ValueError(f'Thiếu nguồn: cần {count}, còn {len(rows)} câu phù hợp chưa có trong bài')
        return random.Random(seed).sample(sorted(rows),count),len(rows)

    def attach_image(self, b, path):
        path=Path(path);raw=path.read_bytes()
        if not raw:raise ValueError('Ảnh rỗng')
        if path.suffix.lower() not in ('.png','.jpg','.jpeg','.pdf'):raise ValueError('Chọn ảnh PNG/JPG hoặc PDF')
        digest=hashlib.sha256(raw).hexdigest();relative=Path('assets')/(digest+path.suffix.lower())
        target=self.root/relative;target.parent.mkdir(parents=True,exist_ok=True)
        if not target.exists():target.write_bytes(raw)
        reference='lesson-'+digest+path.suffix.lower()
        b['assets'][reference]={'path':relative.as_posix(),'hash':digest}
        return r'\includegraphics[width=.75\linewidth]{'+reference+'}'

    def body(self, doc, audience='teacher', worksheet=False):
        self.validate(doc)
        if audience not in ('teacher','student'):raise ValueError('Đối tượng không hợp lệ')
        assets={};lines=[r'\section*{'+tex_text(doc['title'])+'}'];nodes=doc['blocks']
        def render(parent=None,depth=0):
            for b in nodes:
                if b['parent']!=parent:continue
                if audience=='student' and b['policy']=='private':continue
                include=not worksheet or b['kind'] in ('exercise','section','method')
                if include:
                    command='subsection*' if depth==0 else 'subsubsection*'
                    lines.append('\\'+command+'{'+tex_text(b['title'])+'}')
                    source=b['source']
                    if audience=='student':source=student_source(source,b['policy']=='question')
                    replacements=[]
                    for cmd in commands(source):
                        if cmd.name!='includegraphics':continue
                        cursor=skip_space(source,cmd.end)
                        if cursor<len(source) and source[cursor]=='*':cursor=skip_space(source,cursor+1)
                        if cursor<len(source) and source[cursor]=='[':_,cursor,_=group(source,cursor,'[',']')
                        reference,end,start=group(source,cursor)
                        info=b['assets'].get(reference)
                        if not info:raise ValueError('Thiếu ảnh trong '+b['title']+': '+reference)
                        file=(self.root/info['path']).resolve()
                        if not file.is_relative_to(self.root.resolve()):raise ValueError('Tài nguyên ngoài kho quản lý')
                        if not file.is_file() or hashlib.sha256(file.read_bytes()).hexdigest()!=info['hash']:
                            raise ValueError('Ảnh thiếu hoặc đã đổi bytes: '+reference)
                        export_ref='assets/'+info['hash']+file.suffix.lower()
                        assets[export_ref]=file;replacements.append((start+1,end-1,export_ref))
                    for start,end,value in reversed(replacements):source=source[:start]+value+source[end:]
                    lines.append(source)
                    if audience=='teacher' and b['teacher_notes'].strip():
                        lines.extend([r'\par\textbf{Ghi chú giáo viên:}',b['teacher_notes']])
                render(b['id'],depth+1)
        render()
        return '\n\n'.join(lines),assets

    def export(self, doc, folder, audience='teacher', worksheet=False, engine='pdflatex', preamble_file=None, cancelled=lambda:False):
        """Commit a complete immutable local bundle; never overwrite an older bundle."""
        body,assets=self.body(doc,audience,worksheet)
        compiler=Compiler(self.root,engine=engine,preamble_file=preamble_file)
        result=compiler.compile(body,assets,cancelled)
        if not result.ok:raise ValueError(result.log[-2500:])
        if cancelled():raise ValueError('Đã hủy xuất bài')
        folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
        export_id=str(uuid.uuid4());destination=folder/('bai-giang-'+audience+'-'+export_id[:8])
        snapshot={'document':deepcopy(doc),'audience':audience,'worksheet':worksheet,'engine':engine,'profile':compiler.profile()[0]}
        with tempfile.TemporaryDirectory(dir=folder,prefix='.lesson-') as temporary:
            work=Path(temporary);(work/'assets').mkdir()
            for reference,path in assets.items():shutil.copyfile(path,work/reference)
            preamble,dependencies=compiler.profile()
            # Custom profile dependencies may contain private content: supported
            # source bundles currently use the audited built-in profile only.
            if preamble_file:raise ValueError('Xuất gói bài giảng hiện dùng profile tích hợp; profile riêng chưa được chứng nhận đóng gói')
            (work/'main.tex').write_text(preamble+'\n'+r'\begin{document}'+'\n'+body+'\n'+r'\end{document}',encoding='utf-8')
            shutil.copyfile(result.pdf,work/'bai-giang.pdf')
            hashes={f.relative_to(work).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in work.rglob('*') if f.is_file()}
            (work/'manifest.json').write_text(json.dumps({'lesson_id':doc['id'],'revision':doc['revision'],'audience':audience,'worksheet':worksheet,'sha256':hashes},ensure_ascii=False,indent=2),encoding='utf-8')
            shutil.move(str(work),str(destination))
        managed=self.root/'lesson_exports'/export_id
        managed.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(destination,managed)
        snapshot['bundle_sha256']={f.relative_to(managed).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in managed.rglob('*') if f.is_file()}
        try:
            with self.services.database.transaction() as c:
                c.execute('INSERT INTO lesson_exports VALUES (?,?,?,?,?,?,?)',(export_id,doc['id'],doc['revision'],audience,json.dumps(snapshot,ensure_ascii=False),managed.relative_to(self.root).as_posix(),stamp()))
        except Exception:
            # Keep the complete folder available even if recording fails.
            raise ValueError('Đã tạo bộ xuất tại '+str(destination)+' nhưng chưa ghi được lịch sử')
        return destination