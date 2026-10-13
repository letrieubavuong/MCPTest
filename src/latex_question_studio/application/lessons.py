"""Versioned lesson documents; bank references are pinned, never live content."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import random
import shutil
import tempfile
import unicodedata
import uuid
from latex_question_studio.application.search import SearchService
from latex_question_studio.parsing.latex import commands, group, skip_space, parse_questions
from latex_question_studio.preview.compiler import Compiler

KINDS = {'theory':'Lý thuyết', 'method':'Dạng toán / Phương pháp', 'example':'Ví dụ',
         'exercise':'Bài tập vận dụng', 'section':'Nhóm nội dung'}
POLICIES = {'full':'Hiện đầy đủ', 'question':'Chỉ đề bài', 'private':'Chỉ giáo viên'}

FOLDER_THEORY = 'LyThuyet'
FOLDER_METHODS = 'DangToan'
FOLDER_EXERCISES = 'BTVD'

FILE_ROLE_FOLDERS = {
    'theory': FOLDER_THEORY,
    'method': FOLDER_METHODS,
    'exercise': FOLDER_EXERCISES,
}
FILE_ROLES = ('theory', 'method', 'exercise')
FILE_ROLE_LABELS = {
    'theory': 'Thư mục Lý thuyết (LyThuyet)',
    'method': 'Thư mục Dạng toán & Ví dụ (DangToan)',
    'exercise': 'Thư mục BTVD (BTVD)',
}


def stamp():
    return datetime.now(timezone.utc).isoformat()


def block(kind, title, parent=None, source=''):
    return {'id':str(uuid.uuid4()), 'parent':parent, 'kind':kind, 'title':title,
            'source':source, 'policy':'question' if kind=='exercise' else 'full',
            'assets':{}, 'question':None, 'teacher_notes':''}


LESSON_TEMPLATES = {
    'standard': {
        'name': 'Chuẩn GDPT 2018 (Toàn diện)',
        'description': 'Mục tiêu → Khởi động → A. Lý thuyết trọng tâm → B. Các dạng toán (Phương pháp + Ví dụ + Luyện tập) → C. Vận dụng → D. Bài tập về nhà.',
    },
    'methods': {
        'name': 'Chuyên đề phân dạng (Rèn kỹ năng & Luyện thi)',
        'description': 'Tóm tắt công thức → Dạng 1 → Dạng 2 (kèm ví dụ và bài tập) → Hệ thống bài tập tự luyện tổng hợp.',
    },
    'theory': {
        'name': 'Tiết học lý thuyết (Hình thành kiến thức mới)',
        'description': 'Đặt vấn đề → Khái niệm & định lý → Ví dụ áp dụng trực tiếp → Củng cố nhanh tại lớp.',
    },
    'worksheet': {
        'name': 'Phiếu bài tập (Worksheet rèn luyện)',
        'description': 'Tóm tắt lý thuyết dạng bảng → Trắc nghiệm nhiều lựa chọn → Đúng / Sai → Trả lời ngắn & Tự luận.',
    },
    'legacy': {
        'name': 'Cơ bản (Lý thuyết + 1 Dạng toán + Ví dụ + Vận dụng)',
        'description': 'Cấu trúc tiêu chuẩn gọn nhẹ với 1 phần lý thuyết, 1 dạng toán và bài tập vận dụng.',
    },
    'blank': {
        'name': 'Bài giảng trống (Tự tạo từ đầu)',
        'description': 'Khung tài liệu trắng với 1 mục để giáo viên tự thiết kế toàn bộ theo phong cách riêng.',
    },
}


def build_template_blocks(template_key='legacy', num_methods=2, include_warmup=True, include_homework=True):
    if template_key == 'standard':
        blocks = [block('section', 'Mục tiêu & Yêu cầu cần đạt')]
        if include_warmup:
            blocks.append(block('theory', 'I. Khởi động & Đặt vấn đề'))
        theory = block('theory', 'A. Lý thuyết trọng tâm')
        blocks.append(theory)
        blocks.append(block('theory', '1. Khái niệm và định lý cơ bản', parent=theory['id']))
        blocks.append(block('theory', '2. Các công thức & Chú ý cần nhớ', parent=theory['id']))
        for i in range(1, max(1, num_methods) + 1):
            m_title = f'Dạng {i}: Phương pháp giải cơ bản' if i == 1 else f'Dạng {i}: Dạng toán nâng cao & vận dụng'
            m = block('method', m_title)
            blocks.append(m)
            blocks.append(block('example', f'Ví dụ 1 (Minh họa phương pháp)', parent=m['id']))
            blocks.append(block('exercise', f'Bài tập luyện tập Dạng {i}', parent=m['id']))
        blocks.append(block('section', 'B. Bài tập vận dụng tổng hợp'))
        if include_homework:
            blocks.append(block('section', 'C. Hướng dẫn tự học & Bài tập về nhà'))
        return blocks
    elif template_key == 'methods':
        blocks = [block('theory', 'A. Tóm tắt kiến thức cốt lõi')]
        for i in range(1, max(1, num_methods) + 1):
            m_title = f'Dạng {i}: Nhận diện và phương pháp giải' if i == 1 else f'Dạng {i}: Dạng toán rèn luyện kỹ năng'
            m = block('method', m_title)
            blocks.append(m)
            blocks.append(block('example', f'Ví dụ minh họa 1', parent=m['id']))
            blocks.append(block('example', f'Ví dụ minh họa 2', parent=m['id']))
            blocks.append(block('exercise', f'Bài tập tự luyện Dạng {i}', parent=m['id']))
        blocks.append(block('section', 'B. Bài tập trắc nghiệm & tự luyện tổng hợp'))
        if include_homework:
            blocks.append(block('section', 'C. Bài tập rèn luyện nâng cao'))
        return blocks
    elif template_key == 'theory':
        blocks = [block('section', 'I. Mục tiêu bài học')]
        theory = block('theory', 'II. Khám phá kiến thức mới')
        blocks.append(theory)
        blocks.append(block('theory', '1. Hoạt động hình thành khái niệm', parent=theory['id']))
        blocks.append(block('theory', '2. Định lý, tính chất và hệ quả', parent=theory['id']))
        blocks.append(block('example', 'III. Ví dụ minh họa và phân tích'))
        blocks.append(block('section', 'IV. Luyện tập & Củng cố nhanh tại lớp'))
        return blocks
    elif template_key == 'worksheet':
        return [
            block('theory', 'A. Tóm tắt lý thuyết & Công thức trọng tâm'),
            block('section', 'Phần 1: Trắc nghiệm nhiều phương án lựa chọn'),
            block('section', 'Phần 2: Trắc nghiệm Đúng / Sai'),
            block('section', 'Phần 3: Câu hỏi Trả lời ngắn & Tự luận'),
        ]
    elif template_key == 'blank':
        return [block('theory', 'Nội dung bài giảng')]
    else:
        theory = block('theory', 'A. Lý thuyết')
        method = block('method', 'Dạng 1: Phương pháp giải')
        example = block('example', 'Ví dụ 1', method['id'])
        exercises = block('section', 'B. Bài tập vận dụng')
        return [theory, method, example, exercises]



def _slug(value):
    value = str(value or '').replace('đ', 'd').replace('Đ', 'D')
    normalized = unicodedata.normalize('NFKD', value)
    ascii_chars = [c for c in normalized if not unicodedata.combining(c) and ord(c) < 128]
    clean = ''.join(c.lower() if c.isalnum() else '-' for c in ascii_chars)
    return '-'.join(part for part in clean.split('-') if part)[:48] or 'noi-dung'


def _descendants(blocks, roots):
    selected=set(roots);changed=True
    while changed:
        changed=False
        for item in blocks:
            if item.get('parent') in selected and item['id'] not in selected:
                selected.add(item['id']);changed=True
    return selected


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
    'frac dfrac tfrac sqrt left right text textrm textbf textit emph underline textbackslash textasciicircum textasciitilde '
    'sin cos tan cot log ln exp lim max min sum prod int iint infty partial prime '
    'alpha beta gamma delta theta lambda mu pi sigma omega Delta Omega '
    'cdot times div pm mp le leq ge geq ne neq approx equiv in notin subset '
    'subseteq cup cap emptyset forall exists mathbb mathcal mathrm mathbf '
    'vec overrightarrow overline hat bar underbrace overbrace displaystyle '
    'quad qquad hspace vspace smallskip medskip bigskip par noindent section subsection subsubsection '
    'includegraphics linewidth textwidth textheight item label ref pageref dots ldots cdots vdots ddots '
    'draw node path fill filldraw coordinate foreach newpage clearpage '
    'centering caption multicolumn hline cline to mapsto longrightarrow '
    'Rightarrow Leftrightarrow perp parallel angle degree '
    'implies iff Leftarrow leftarrow rightarrow leftrightarrow heva hoac motcot haicot bacot boncot '
    'motdong haidong badong bondong dapan bangdapan loai loaidapan nguon nganh tieude dethi tieuDe '
    'tab rq lq circ setminus epsilon varepsilon varphi arcsin arccos arctan cotan gcd lcm pmod mod '
    'clip shade shadedraw widehat widetilde TieudeT subject color textcolor definecolor '
    'bfseries itshape rmfamily sffamily tiny small large Large LARGE huge Huge phantom vphantom hphantom').split())


def student_source(source, hide_answers=False):
    source = without_comments(source)
    if hide_answers:
        edits = []
        for cmd in commands(source):
            if cmd.name == 'True':
                edits.append((cmd.start, cmd.end, ''))
            elif cmd.name in ('loigiai', 'hdan', 'shortans'):
                cursor = skip_space(source, cmd.end)
                if cursor < len(source) and source[cursor] == '[':
                    _, cursor, _ = group(source, cursor, '[', ']')
                cursor = skip_space(source, cursor)
                _, end, _ = group(source, cursor)
                edits.append((cmd.start, end, ''))
        boundary = -1
        selected = []
        for start, end, replacement in sorted(edits):
            if start >= boundary:
                selected.append((start, end, replacement))
                boundary = end
        for start, end, replacement in reversed(selected):
            source = source[:start] + replacement + source[end:]

    # Kiểm tra xác thực các lệnh còn lại trong source học sinh (fail-closed)
    for cmd in commands(source):
        if cmd.name not in STUDENT_COMMANDS and not (len(cmd.name) == 1 and not cmd.name.isalpha()):
            raise ValueError('Macro chưa được chứng nhận cho source học sinh: \\' + cmd.name)
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
        return self.ensure_files(json.loads(row[0])) if row else None

    def ensure_files(self, doc):
        """Add the canonical 3-folder TeX-file manifest without rewriting legacy blocks.
        Thư mục 1: LyThuyet/ (Lý thuyết)
        Thư mục 2: DangToan/ (Các dạng toán + ví dụ)
        Thư mục 3: BTVD/ (Bài tập vận dụng)
        """
        result=deepcopy(doc)
        blocks=result.get('blocks',[])
        existing={entry.get('role'):entry for entry in result.get('files',[]) if entry.get('role') in FILE_ROLES}
        files=[]
        theory_roots=[item['id'] for item in blocks if item.get('kind')=='theory' and item.get('parent') is None]
        if theory_roots:
            ids=_descendants(blocks,theory_roots)
            old=existing.get('theory',{})
            files.append({
                'id':old.get('id',str(uuid.uuid4())),
                'role':'theory',
                'folder':FOLDER_THEORY,
                'title':old.get('title') or 'Lý thuyết',
                'filename':f'{FOLDER_THEORY}/ly-thuyet.tex',
                'block_ids':[item['id'] for item in blocks if item['id'] in ids],
                'locked':old.get('locked',True)
            })
        methods=[item for item in blocks if item.get('kind')=='method' and item.get('parent') is None]
        for index,item in enumerate(methods,1):
            ids=_descendants(blocks,[item['id']])
            old=next((entry for entry in result.get('files',[]) if entry.get('role')=='method' and item['id'] in entry.get('block_ids',[])),{})
            files.append({
                'id':old.get('id',str(uuid.uuid4())),
                'role':'method',
                'folder':FOLDER_METHODS,
                'title':item.get('title') or f'Dạng toán {index}',
                'filename':f'{FOLDER_METHODS}/dang-{index:02d}-{_slug(item.get("title", "dang-toan"))}.tex',
                'block_ids':[block['id'] for block in blocks if block['id'] in ids],
                'locked':old.get('locked',True)
            })
        exercise_roots=[item['id'] for item in blocks if item.get('kind') in ('section','exercise') and item.get('parent') is None]
        if exercise_roots:
            ids=_descendants(blocks,exercise_roots)
            old=next((entry for entry in result.get('files',[]) if entry.get('role')=='exercise'),{})
            files.append({
                'id':old.get('id',str(uuid.uuid4())),
                'role':'exercise',
                'folder':FOLDER_EXERCISES,
                'title':old.get('title') or 'Bài tập vận dụng',
                'filename':f'{FOLDER_EXERCISES}/bai-tap-van-dung.tex',
                'block_ids':[item['id'] for item in blocks if item['id'] in ids],
                'locked':old.get('locked',True)
            })
        result['files']=files
        result['file_model_version']=2
        return result

    def file_manifest(self, doc):
        return deepcopy(self.ensure_files(doc).get('files',[]))

    def _raw_file_source(self, doc, entry):
        selected=set(entry.get('block_ids',[]));blocks=[item for item in doc.get('blocks',[]) if item['id'] in selected]
        lines=[r'\section*{'+tex_text(entry.get('title',FILE_ROLE_LABELS[entry['role']]))+'}']
        for item in blocks:
            if item.get('title'):
                lines.append(r'\subsection*{'+tex_text(item['title'])+'}')
            if item.get('source'):
                lines.append(item['source'])
        return '\n\n'.join(lines)

    def sync_file_tables(self, connection, doc):
        """Persist canonical source files and pinned exercise indexes in SQLite."""
        normalized=self.ensure_files(doc);now=stamp()
        connection.execute('DELETE FROM lesson_files WHERE lesson_id=?',(doc['id'],))
        for position,entry in enumerate(normalized.get('files',[])):
            connection.execute('INSERT INTO lesson_files VALUES (?,?,?,?,?,?,?,?,?)',(
                entry['id'],doc['id'],entry['role'],entry.get('title',FILE_ROLE_LABELS[entry['role']]),entry['filename'],position,
                self._raw_file_source(normalized,entry),int(entry.get('locked',True)),now))
            if entry['role']!='exercise':continue
            exercise_position=0
            for block_id in entry.get('block_ids',[]):
                item=next((block for block in normalized['blocks'] if block['id']==block_id),None)
                question=item.get('question') if item else None
                if not question:continue
                connection.execute('INSERT INTO lesson_file_exercises VALUES (?,?,?,?,?,?,?)',(
                    entry['id'],exercise_position,exercise_position+1,question['id'],question['revision'],item.get('source',''),int(entry.get('locked',True))))
                exercise_position+=1

    def file_records(self, lesson_id):
        with self.services.database.connect() as connection:
            files=[dict(row) for row in connection.execute('SELECT * FROM lesson_files WHERE lesson_id=? ORDER BY position',(lesson_id,))]
            for entry in files:
                entry['locked']=bool(entry['locked'])
                entry['exercises']=[dict(row) for row in connection.execute('SELECT * FROM lesson_file_exercises WHERE file_id=? ORDER BY export_index',(entry['id'],))]
            return files

    def lock_file(self, doc, role, locked=True):
        candidate=self.ensure_files(doc)
        for entry in candidate.get('files',[]):
            if entry['role']==role:
                entry['locked']=bool(locked)
                if role=='exercise':
                    for index,block_id in enumerate(entry.get('block_ids',[]),1):
                        block_item=next((item for item in candidate['blocks'] if item['id']==block_id),None)
                        if block_item and block_item.get('question'):
                            block_item['question']['export_index']=index
                break
        return candidate

    def mark_file_dirty(self, doc, block_id):
        candidate=self.ensure_files(doc)
        for entry in candidate.get('files',[]):
            if block_id in entry.get('block_ids',[]):
                entry['locked']=False
                break
        return candidate

    def _file_document(self, doc, entry):
        selected=set(entry.get('block_ids',[]))
        blocks=[deepcopy(item) for item in doc.get('blocks',[]) if item['id'] in selected]
        for item in blocks:
            if item.get('parent') not in selected:
                item['parent']=None
        return {'id':doc['id'],'title':entry.get('title',FILE_ROLE_LABELS[entry['role']]),'revision':doc.get('revision',0),'blocks':blocks,'recipes':[],'files':[]}

    def file_sources(self, doc, audience='teacher', worksheet=False):
        normalized=self.ensure_files(doc);result=[]
        for entry in normalized.get('files',[]):
            subdoc=self._file_document(normalized,entry)
            source,assets=self.body(subdoc,audience,worksheet,include_titles=False,include_block_titles=True)
            result.append((entry,source,assets))
        return result

    def create(self, title='Bài giảng mới', subject='Toán', grade='12', chapter=None,
               blocks=None, taxonomy_id=None, template_key='legacy',
               num_methods=1, include_warmup=False, include_homework=False):
        if blocks is None:
            blocks = build_template_blocks(template_key, num_methods=num_methods,
                                           include_warmup=include_warmup,
                                           include_homework=include_homework)
        doc = {'id':str(uuid.uuid4()), 'title':title, 'revision':0,
               'subject':subject or 'Toán', 'grade':str(grade or '12'),
               'chapter':chapter, 'taxonomy_id':taxonomy_id,
               'template_key':template_key, 'blocks':blocks, 'recipes':[]}
        doc = self.ensure_files(doc)
        return self.save(doc)

    def add_method_bundle(self, doc, title=None, parent=None):
        doc = deepcopy(doc)
        existing_methods = [b for b in doc.get('blocks', []) if b.get('kind') == 'method']
        next_idx = len(existing_methods) + 1
        method_title = title or f"Dạng {next_idx}: Phương pháp giải & ví dụ"
        method_b = block('method', method_title, parent=parent)
        ex_b = block('example', f"Ví dụ 1", parent=method_b['id'])
        train_b = block('exercise', f"Bài tập rèn luyện", parent=method_b['id'])
        doc['blocks'].extend([method_b, ex_b, train_b])
        doc = self.ensure_files(doc)
        return self.save(doc), method_b['id']

    def duplicate_block(self, doc, block_id):
        doc = deepcopy(doc)
        blocks = doc.get('blocks', [])
        target = next((b for b in blocks if b['id'] == block_id), None)
        if not target:
            return doc, None
        descendants = _descendants(blocks, [block_id])
        id_map = {old_id: str(uuid.uuid4()) for old_id in descendants}
        new_blocks = []
        for b in blocks:
            if b['id'] in descendants:
                copied = deepcopy(b)
                copied['id'] = id_map[b['id']]
                if b['id'] == block_id:
                    copied['title'] = (copied.get('title') or '') + ' (bản sao)'
                    copied['parent'] = b.get('parent')
                else:
                    copied['parent'] = id_map.get(b.get('parent'), b.get('parent'))
                new_blocks.append(copied)
        doc['blocks'].extend(new_blocks)
        doc = self.ensure_files(doc)
        return self.save(doc), id_map[block_id]


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
        doc=self.ensure_files(doc)
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
            self.sync_file_tables(c,saved)
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

    def body(self, doc, audience='teacher', worksheet=False, include_titles=True, include_block_titles=None):
        self.validate(doc)
        if audience not in ('teacher','student'):raise ValueError('Đối tượng không hợp lệ')
        if include_block_titles is None:include_block_titles=include_titles
        assets={};lines=[r'\section*{'+tex_text(doc['title'])+'}'] if include_titles else [];nodes=doc['blocks']
        def render(parent=None,depth=0):
            for b in nodes:
                if b['parent']!=parent:continue
                if audience=='student' and b['policy']=='private':continue
                include=not worksheet or b['kind'] in ('exercise','section','method')
                if include:
                    command='subsection*' if depth==0 else 'subsubsection*'
                    if include_block_titles:lines.append('\\'+command+'{'+tex_text(b['title'])+'}')
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

    def generate_master_source(self, doc, files=None, audience='teacher', worksheet=False):
        """Tạo mã nguồn master (main.tex) liên kết toàn bộ các file từ 3 thư mục:
        - Thư mục lý thuyết: LyThuyet/
        - Thư mục dạng toán & ví dụ: DangToan/
        - Thư mục bài tập vận dụng: BTVD/
        """
        if files is None:
            files = self.file_manifest(doc)
        lines = [
            f"% ====================================================================",
            f"% BÀI GIẢNG: {tex_text(doc.get('title', 'Bài giảng'))}",
            f"% Cấu trúc 3 thư mục: LyThuyet/ · DangToan/ · BTVD/",
            f"% Tự động liên kết các file thành bài giảng hoàn chỉnh",
            f"% ====================================================================\n",
            r'\section*{' + tex_text(doc.get('title', 'BÀI GIẢNG')) + '}\n',
        ]
        theory_files = [f for f in files if f.get('role') == 'theory']
        if theory_files:
            lines.append('% --- THƯ MỤC LÝ THUYẾT (LyThuyet/) ---')
            for entry in theory_files:
                input_ref = entry['filename'].removesuffix('.tex').replace('\\', '/')
                lines.append(r'\input{' + input_ref + '}')
            lines.append('')
        method_files = [f for f in files if f.get('role') == 'method']
        if method_files:
            lines.append('% --- THƯ MỤC DẠNG TOÁN VÀ VÍ DỤ (DangToan/) ---')
            for entry in method_files:
                input_ref = entry['filename'].removesuffix('.tex').replace('\\', '/')
                lines.append(r'\input{' + input_ref + '}')
            lines.append('')
        exercise_files = [f for f in files if f.get('role') == 'exercise']
        if exercise_files:
            lines.append('% --- THƯ MỤC BÀI TẬP VẬN DỤNG (BTVD/) ---')
            for entry in exercise_files:
                input_ref = entry['filename'].removesuffix('.tex').replace('\\', '/')
                lines.append(r'\input{' + input_ref + '}')
            lines.append('')
        return '\n'.join(lines)

    def master_bundle(self, doc, audience='teacher', worksheet=False):
        """Tập hợp master source, từ điển extra_files (tương ứng 3 thư mục), và assets."""
        normalized = self.ensure_files(doc)
        files = self.file_sources(normalized, audience, worksheet)
        extra_files = {}
        assets = {}
        for entry, source, file_assets in files:
            extra_files[entry['filename']] = source
            for ref, path in file_assets.items():
                assets[ref] = path
        _, doc_assets = self.body(normalized, audience, worksheet)
        for ref, path in doc_assets.items():
            if ref not in assets:
                assets[ref] = path
        master_source = self.generate_master_source(normalized, [e for e, _, _ in files], audience, worksheet)
        return master_source, extra_files, assets

    def export(self, doc, folder, audience='teacher', worksheet=False, engine='pdflatex', preamble_file=None, cancelled=lambda:False):
        """Commit a complete immutable local bundle; never overwrite an older bundle.
        Xuất toàn bộ cấu trúc 3 thư mục:
          - LyThuyet/ (Lý thuyết)
          - DangToan/ (Dạng toán + Ví dụ)
          - BTVD/     (Bài tập vận dụng)
          - main.tex  (Liên kết 3 thư mục)
          - bai-giang.pdf
        """
        doc=self.ensure_files(doc)
        records=self.file_records(doc['id'])
        exercise_refs=[row for entry in records if entry['role']=='exercise' for row in entry.get('exercises',[])]
        if exercise_refs and any(not entry['locked'] for entry in records if entry['role']=='exercise' and entry.get('exercises')):
            raise ValueError('File bài tập chưa được chốt; hãy chốt file và chỉ mục trước khi xuất')
        files=self.file_sources(doc,audience,worksheet)
        master_source,extra_files,assets=self.master_bundle(doc,audience,worksheet)
        compiler=Compiler(self.root,engine=engine,preamble_file=preamble_file)
        result=compiler.compile(master_source,assets,cancelled=cancelled,extra_files=extra_files)
        if not result.ok:raise ValueError(result.log[-2500:])
        if cancelled():raise ValueError('Đã hủy xuất bài')
        folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
        export_id=str(uuid.uuid4());destination=folder/('bai-giang-'+audience+'-'+export_id[:8])
        snapshot={'document':deepcopy(doc),'audience':audience,'worksheet':worksheet,'engine':engine,'profile':compiler.profile()[0]}
        with tempfile.TemporaryDirectory(dir=folder,prefix='.lesson-') as temporary:
            work=Path(temporary);(work/'assets').mkdir()
            for reference,path in assets.items():
                target_asset=work/reference
                target_asset.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(path,target_asset)
            preamble,dependencies=compiler.profile()
            if preamble_file:raise ValueError('Xuất gói bài giảng hiện dùng profile tích hợp; profile riêng chưa được chứng nhận đóng gói')
            for relative in dependencies:
                target=work/(Path(relative).name if Path(relative).suffix==".cls" else relative);target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copyfile(compiler.profile_root/relative,target)
            file_sources={}
            for entry,source,file_assets in files:
                for reference,path in file_assets.items():
                    if reference not in assets:
                        assets[reference]=path
                        target_asset=work/reference
                        target_asset.parent.mkdir(parents=True,exist_ok=True)
                        shutil.copyfile(path,target_asset)
                file_path=work/entry['filename']
                file_path.parent.mkdir(parents=True,exist_ok=True)
                file_path.write_text(source,encoding='utf-8')
            body, _ = self.body(doc, audience, worksheet)
            source_index = '\n'.join('% ' + line for line in body.splitlines())
            (work/'main.tex').write_text(preamble+'\n'+r'\begin{document}'+'\n'+master_source+'\n'+source_index+'\n'+r'\end{document}',encoding='utf-8')
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
            raise ValueError('Đã tạo bộ xuất tại '+str(destination)+' nhưng chưa ghi được lịch sử')
        return destination
