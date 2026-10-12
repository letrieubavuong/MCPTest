from pathlib import Path
from datetime import datetime,timezone
import json
import random
import shutil
import tempfile
import uuid
import zipfile
from latex_question_studio.parsing.latex import parse_questions,commands,group,skip_space
from latex_question_studio.application.search import SearchService
from latex_question_studio.preview.compiler import Compiler,BUILTIN_PREAMBLE

HIDE_ANSWERS = r"""\renewcommand{\True}{}
\renewcommand{\loigiai}[1]{}
\let\hdan\loigiai
\renewcommand{\shortans}[2][]{}
\ifcsname hideansEX\endcsname\AtBeginDocument{\hideansEX{ex}}\fi
"""

def shuffled_question(item, rng, shuffle_options=True):
    source = item.source
    permutation = []
    if item.question_type in ('mcq', 'true_false'):
        options = item.answer['options']
        permutation = list(range(len(options)))
        if shuffle_options and item.question_type == 'mcq':
            rng.shuffle(permutation)
        if item.question_type == 'mcq':
            answer = {'correct_letter': next(chr(65+i) for i, old in enumerate(permutation) if options[old]['correct'])}
        else:
            answer = {'truth': [option['correct'] for option in options]}
        if permutation != list(range(len(options))):
            for index in reversed(range(len(options))):
                option = options[index]
                source = source[:option['start']+1] + options[permutation[index]]['source'] + source[option['end']-1:]
    elif item.question_type == 'short_answer':
        answer = {'value': item.answer['value']}
    else:
        answer = {'essay': True}
    return {'source': source, 'permutation': permutation, 'answer': answer}

class ExamService:
    def __init__(self,services):self.services=services

    def candidates(self,filters,taxonomy_id=None,valid_only=False,cancelled=lambda:False):
        from latex_question_studio.persistence.analysis import ensure,PARSER_VERSION
        join,where,params=SearchService(self.services).query_parts(filters=filters,taxonomy_id=taxonomy_id)
        if valid_only:
            ensure(self.services.database,join,where,params,cancelled)
            join+=' JOIN question_analysis a ON a.question_id=q.id'
            where+=['a.valid=1','a.parser_version=?'];params+=[PARSER_VERSION]
        with self.services.database.connect() as c:
            return [row[0] for row in c.execute('SELECT q.id FROM questions q LEFT JOIN question_metadata m ON m.question_id=q.id'+join+' WHERE '+' AND '.join(where)+' ORDER BY q.created_at,q.id',params)]

    def is_valid_candidate(self,qid):
        from latex_question_studio.persistence.analysis import parsed
        items=parsed(self.services.database,qid)
        return len(items)==1 and not items[0].diagnostics

    def statistics(self,taxonomy_id=None,question_type='',exclude_ids=None,cancelled=lambda:False):
        from latex_question_studio.persistence.analysis import ensure,PARSER_VERSION
        join,where,params=SearchService(self.services).query_parts(filters={'question_type':question_type},taxonomy_id=taxonomy_id)
        excluded=list(set(exclude_ids or []))
        if excluded:where.append('q.id NOT IN ('+','.join('?' for _ in excluded)+')');params+=excluded
        ensure(self.services.database,join,where,params,cancelled)
        sql='SELECT q.cognitive_level,a.valid,count(*) FROM questions q LEFT JOIN question_metadata m ON m.question_id=q.id JOIN question_analysis a ON a.question_id=q.id'+join+' WHERE '+' AND '.join(where+['a.parser_version=?'])+' GROUP BY q.cognitive_level,a.valid'
        counts={level:0 for level in ('NB','TH','VD','VDC','unclassified')};invalid=0
        with self.services.database.connect() as c:
            for level,valid,count in c.execute(sql,params+[PARSER_VERSION]):
                if not valid:invalid+=count
                else:counts[level if level in counts else 'unclassified']+=count
        return {'counts':counts,'invalid':invalid,'total':sum(counts.values())}

    def matrix_statistics(self, taxonomy_id=None, exclude_ids=None, cancelled=lambda: False):
        """Return counts for all 4 question types (mcq, true_false, short_answer, essay) across 4 cognitive levels."""
        from latex_question_studio.persistence.analysis import ensure, PARSER_VERSION
        join, where, params = SearchService(self.services).query_parts(filters={}, taxonomy_id=taxonomy_id)
        excluded = list(set(exclude_ids or []))
        if excluded:
            where.append('q.id NOT IN (' + ','.join('?' for _ in excluded) + ')')
            params += excluded
        ensure(self.services.database, join, where, params, cancelled)
        sql = (
            'SELECT q.question_type, q.cognitive_level, a.valid, count(*) '
            'FROM questions q '
            'LEFT JOIN question_metadata m ON m.question_id=q.id '
            'JOIN question_analysis a ON a.question_id=q.id' + join + ' '
            'WHERE ' + ' AND '.join(where + ['a.parser_version=?']) + ' '
            'GROUP BY q.question_type, q.cognitive_level, a.valid'
        )
        types = ('mcq', 'true_false', 'short_answer', 'essay')
        matrix = {t: {lvl: 0 for lvl in ('NB', 'TH', 'VD', 'VDC', 'unclassified', 'total')} for t in types}
        invalid = 0
        with self.services.database.connect() as c:
            for q_type, level, valid, count in c.execute(sql, params + [PARSER_VERSION]):
                if not valid:
                    invalid += count
                else:
                    target_type = q_type if q_type in matrix else 'mcq'
                    target_lvl = level if level in ('NB', 'TH', 'VD', 'VDC') else 'unclassified'
                    matrix[target_type][target_lvl] += count
                    matrix[target_type]['total'] += count
        total = sum(matrix[t]['total'] for t in types)
        return {'matrix': matrix, 'invalid': invalid, 'total': total}

    def generate(self, title, manual_ids=None, matrix=None, seed=0, shuffle_questions=True, shuffle_options=True,
                 subject='TOÁN', grade='', duration='90 phút', school='', exam_code='101', cancelled=lambda: False, **extra):
        if not title.strip():raise ValueError('Tên đề không được rỗng')
        rng=random.Random(seed);manual=list(dict.fromkeys(manual_ids or []));matrix=matrix or []
        if len(manual)!=len(manual_ids or []):raise ValueError('Câu chọn thủ công bị lặp')
        slots=[]
        for row in matrix:
            count=int(row['count'])
            if not 0<=count<=500:raise ValueError('Số câu mỗi hàng phải từ 0 đến 500')
            candidates=[q for q in self.candidates(row.get('filters',{}),row.get('taxonomy_id'),valid_only=True,cancelled=cancelled) if q not in manual]
            rng.shuffle(candidates)
            if len(candidates)<count:
                scope_desc = row.get('scope_name') or row.get('taxonomy_id') or 'ma trận'
                qtype_desc = row.get('filters', {}).get('question_type', '')
                level_desc = row.get('filters', {}).get('cognitive_level', '')
                detail = f" ({qtype_desc} {level_desc})".strip() if (qtype_desc or level_desc) else ""
                raise ValueError(f"Thiếu nguồn cho '{scope_desc}{(' ' + detail) if detail else ''}': cần {count}, có {len(candidates)}")
            slots.extend([candidates[:] for _ in range(count)])
        # Bipartite matching handles overlapping matrix cells without duplicate IDs.
        if len(slots)+len(manual)>500:raise ValueError("Mỗi đề tối đa 500 câu")
        assignment={}
        def assign(slot,seen):
            for qid in slots[slot]:
                if qid in seen:continue
                seen.add(qid)
                if qid not in assignment or assign(assignment[qid],seen):assignment[qid]=slot;return True
            return False
        for slot in sorted(range(len(slots)),key=lambda i:len(slots[i])):
            if not assign(slot,set()):raise ValueError('Ma trận chồng lặp không có đủ câu độc lập')
        ids=manual+[qid for qid,slot in sorted(assignment.items(),key=lambda pair:pair[1])]
        if not ids:raise ValueError('Chưa chọn câu hỏi hoặc ma trận')
        if shuffle_questions:rng.shuffle(ids)
        snapshots=[];global_assets={}
        for qid in ids:
            if cancelled():raise InterruptedError("Đã hủy tạo đề")
            q=self.services.questions.get(qid)
            if not q:raise ValueError('Câu hỏi đã bị xóa')
            from latex_question_studio.persistence.analysis import parsed
            items=parsed(self.services.database,qid,q.latex_source)
            if len(items)!=1 or items[0].diagnostics:raise ValueError('Câu chưa phân tích hợp lệ: '+qid[:8])
            item=items[0];shuffled=shuffled_question(item,rng,shuffle_options)
            source=q.latex_source[:item.start]+shuffled['source']+q.latex_source[item.end:]
            permutation=shuffled['permutation'];answer=shuffled['answer']
            replacements=[]
            with self.services.database.connect() as c:
                assets={r['original_reference']:self.services.config.data_dir/r['relative_path'] for r in c.execute('SELECT qa.original_reference,a.relative_path FROM question_assets qa JOIN assets a ON qa.asset_id=a.id WHERE qa.question_id=?',(qid,))}
            for command in commands(source):
                if command.name!='includegraphics':continue
                cursor=skip_space(source,command.end)
                if cursor<len(source) and source[cursor]=='*':cursor=skip_space(source,cursor+1)
                if cursor<len(source) and source[cursor]=='[':_,cursor,_=group(source,cursor,'[',']')
                reference,end,start=group(source,cursor)
                if reference not in assets:raise ValueError('Thiếu ảnh: '+reference)
                unique='assets/'+assets[reference].name
                replacements.append((start+1,end-1,unique));global_assets[unique]=str(assets[reference])
            for start,end,value in reversed(replacements):source=source[:start]+value+source[end:]
            snapshots.append({'question_id':qid,'revision':q.revision,'source':source,'original_source':q.latex_source,'solution':item.solution,'permutation':permutation,'answer':answer})
        paper,version=str(uuid.uuid4()),str(uuid.uuid4());now=datetime.now(timezone.utc).isoformat()
        # Suggestions only: content equality must not silently remove teacher-selected IDs.
        from difflib import SequenceMatcher
        from latex_question_studio.parsing.latex import normalized_source
        normalized=[normalized_source(q['original_source']) for q in snapshots];warnings=[]
        for i,left in enumerate(normalized):
            if cancelled():raise InterruptedError('Đã hủy tạo đề')
            for j in range(i+1,len(normalized)):
                right=normalized[j];exact=left==right
                if not exact and (min(len(left),len(right))/max(len(left),len(right),1)<0.9):continue
                score=1.0 if exact else SequenceMatcher(None,left,right,autojunk=False).ratio()
                if exact or score>=0.95:
                    warnings.append({'kind':'exact' if exact else 'near','question_ids':[snapshots[i]['question_id'],snapshots[j]['question_id']],'score':round(score,4)})
        snapshot={
            'title': title,
            'subject': subject or 'TOÁN',
            'grade': grade or '',
            'duration': duration or '90 phút',
            'school': school or '',
            'exam_code': exam_code or '101',
            'questions': snapshots,
            'assets': global_assets,
            'duplicate_warnings': warnings
        }
        if cancelled():raise InterruptedError('Đã hủy tạo đề')
        with self.services.database.transaction() as c:
            c.execute('INSERT INTO exam_papers VALUES (?,?,?)',(paper,title,now))
            c.execute('INSERT INTO exam_versions VALUES (?,?,?,?,?,?)',(version,paper,seed,json.dumps(matrix),json.dumps(snapshot,ensure_ascii=False),now))
            for i,q in enumerate(snapshots):c.execute('INSERT INTO exam_questions VALUES (?,?,?,?,?,?)',(version,i+1,q['question_id'],q['revision'],json.dumps(q['permutation']),json.dumps(q['answer'],ensure_ascii=False)))
        return version,snapshot

    def history(self):
        with self.services.database.connect() as c:return [dict(r) for r in c.execute('SELECT v.*,p.title FROM exam_versions v JOIN exam_papers p ON p.id=v.paper_id ORDER BY v.created_at DESC LIMIT 100')]

    @staticmethod
    def content(snapshot,solutions=False,answer_only=False):
        escape={'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$','#':r'\#','_':r'\_','{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}'}
        title=''.join(escape.get(ch,ch) for ch in snapshot.get('title', 'Đề kiểm tra'))
        subject=''.join(escape.get(ch,ch) for ch in snapshot.get('subject', 'TOÁN'))
        school=''.join(escape.get(ch,ch) for ch in snapshot.get('school', 'TRƯỜNG THPT'))
        duration=''.join(escape.get(ch,ch) for ch in snapshot.get('duration', '90 phút'))
        exam_code=''.join(escape.get(ch,ch) for ch in snapshot.get('exam_code', '101'))

        # Header theo phong cách lệnh \TieudeT trong MAPClass (kèm fallback 2 cột tương thích)
        header_tex = (
            r"\ifcsname TieudeT\endcsname" "\n"
            rf"  \def\subject{{{subject}}}" "\n"
            rf"  \TieudeT{{{title}}}" "\n"
            r"\else" "\n"
            r"  \noindent" "\n"
            r"  \begin{center}" "\n"
            r"  \begin{tabular}{p{0.36\textwidth}|p{0.58\textwidth}}" "\n"
            rf"    \centering \textbf{{{school or 'TRƯỜNG THPT'}}} & \centering \textbf{{\large {title}}} \tabularnewline" "\n"
            rf"    \centering \textbf{{MÃ ĐỀ: {exam_code}}} & \centering Môn: \textbf{{{subject}}} \tabularnewline" "\n"
            rf"    & \centering \textit{{Thời gian làm bài: {duration} (không tính thời gian giao đề)}}" "\n"
            r"  \end{tabular}" "\n"
            r"  \end{center}" "\n"
            r"  \vspace{1em}" "\n"
            r"\fi"
        )
        lines = [header_tex]
        for i,q in enumerate(snapshot['questions'],1):
            if answer_only:
                answer=q['answer'];value=answer.get('correct_letter',answer.get('value',str(answer.get('truth','Tự luận'))))
                # Values are genuine LaTeX answers; preserve math rather than escaping.
                lines.append(f"\\noindent {i}. "+str(value)+r'\par')
            else:
                source=q['source']
                if not solutions:
                    from latex_question_studio.application.lessons import student_source
                    source=student_source(source,hide_answers=True)
                lines.append(f"\\noindent\\textbf{{Câu {i}.}}\n"+source)
                if solutions and q['solution'] and not any(c.name in ('loigiai','hdan') for c in commands(q['source'])):lines.append(r'\loigiai{'+q['solution']+'}')
        return '\n\n'.join(lines)

    def export_tex(self,snapshot,path,solutions=False,answer_only=False,preamble=None):
        body=self.content(snapshot,solutions,answer_only)
        # A solution-only image is an answer too; do not copy it into student folders.
        references=set()
        for cmd in commands(body):
            if cmd.name!='includegraphics':continue
            cursor=skip_space(body,cmd.end)
            if cursor<len(body) and body[cursor]=='*':cursor=skip_space(body,cursor+1)
            if cursor<len(body) and body[cursor]=='[':_,cursor,_=group(body,cursor,'[',']')
            references.add(group(body,cursor)[0])
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        for reference,source in snapshot['assets'].items():
            if reference not in references:continue
            target=path.parent/reference;target.parent.mkdir(parents=True,exist_ok=True)
            if Path(source).resolve()!=target.resolve():shutil.copyfile(source,target)
        header=preamble or BUILTIN_PREAMBLE
        if not solutions and not answer_only:header+='\n'+HIDE_ANSWERS
        document=header+'\n\\begin{document}\n'+body+'\n\\end{document}\n'
        path.write_text(document,encoding='utf-8')
        return path

    def export_pdf(self,snapshot,path,solutions=False,answer_only=False,engine='pdflatex',preamble_file=None,cancelled=lambda:False):
        compiler=Compiler(self.services.config.data_dir,engine=engine,preamble_file=preamble_file,preamble_extra='' if solutions or answer_only else HIDE_ANSWERS)
        result=compiler.compile(self.content(snapshot,solutions,answer_only),snapshot['assets'],cancelled)
        if result.ok:shutil.copyfile(result.pdf,path)
        return result

    def export_zip(self,snapshot,path,solutions=False,preamble=None,cancelled=lambda:False):
        """Create a self-contained TeX bundle with a checksum manifest."""
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.exam-bundle-',dir=path.parent) as temporary:
            folder=Path(temporary);tex=self.export_tex(snapshot,folder/'main.tex',solutions,False,preamble)
            if cancelled():raise InterruptedError('Đã hủy xuất gói đề')
            files={file.relative_to(folder).as_posix():__import__('hashlib').sha256(file.read_bytes()).hexdigest() for file in folder.rglob('*') if file.is_file()}
            manifest={'format':1,'title':snapshot['title'],'audience':'teacher' if solutions else 'student','source_questions':[{'id':q['question_id'],'revision':q['revision']} for q in snapshot['questions']],'sha256':files}
            (folder/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
            temporary_zip=path.with_suffix(path.suffix+'.tmp')
            with zipfile.ZipFile(temporary_zip,'w',zipfile.ZIP_DEFLATED) as archive:
                for file in folder.rglob('*'):
                    if file.is_file():archive.write(file,file.relative_to(folder).as_posix())
            temporary_zip.replace(path)
        return path
