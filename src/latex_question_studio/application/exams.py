from pathlib import Path
from datetime import datetime,timezone
import json
import random
import shutil
import uuid
from latex_question_studio.parsing.latex import parse_questions,commands,group,skip_space
from latex_question_studio.application.search import SearchService
from latex_question_studio.preview.compiler import Compiler,BUILTIN_PREAMBLE

HIDE_ANSWERS = r"""\renewcommand{\True}{}
\renewcommand{\loigiai}[1]{}
\let\hdan\loigiai
\renewcommand{\shortans}[2][]{}
"""

class ExamService:
    def __init__(self,services):self.services=services

    def candidates(self,filters,taxonomy_id=None):
        results=[];offset=0;search=SearchService(self.services)
        while True:
            page=search.find(filters=filters,limit=500,offset=offset,taxonomy_id=taxonomy_id)
            results.extend(q.id for q in page)
            if len(page)<500:return results
            offset+=500

    def is_valid_candidate(self,qid):
        q=self.services.questions.get(qid)
        items=parse_questions(q.latex_source) if q else []
        return len(items)==1 and not items[0].diagnostics

    def statistics(self,taxonomy_id=None,question_type='',exclude_ids=None):
        excluded=set(exclude_ids or []);counts={level:0 for level in ('NB','TH','VD','VDC','unclassified')};invalid=0
        for qid in self.candidates({'question_type':question_type},taxonomy_id):
            if qid in excluded:continue
            q=self.services.questions.get(qid);items=parse_questions(q.latex_source)
            if len(items)!=1 or items[0].diagnostics:
                invalid+=1;continue
            level=q.cognitive_level if q.cognitive_level in counts else 'unclassified';counts[level]+=1
        return {'counts':counts,'invalid':invalid,'total':sum(counts.values())}

    def generate(self,title,manual_ids=None,matrix=None,seed=0,shuffle_questions=True,shuffle_options=True):
        if not title.strip():raise ValueError('Tên đề không được rỗng')
        rng=random.Random(seed);manual=list(dict.fromkeys(manual_ids or []));matrix=matrix or []
        if len(manual)!=len(manual_ids or []):raise ValueError('Câu chọn thủ công bị lặp')
        slots=[]
        for row in matrix:
            count=int(row['count'])
            if not 0<=count<=500:raise ValueError('Số câu mỗi hàng phải từ 0 đến 500')
            candidates=[q for q in self.candidates(row.get('filters',{}),row.get('taxonomy_id')) if q not in manual]
            candidates=[qid for qid in candidates if self.is_valid_candidate(qid)]
            rng.shuffle(candidates)
            if len(candidates)<count:raise ValueError(f"Thiếu nguồn: cần {count}, có {len(candidates)}")
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
            q=self.services.questions.get(qid)
            if not q:raise ValueError('Câu hỏi đã bị xóa')
            items=parse_questions(q.latex_source)
            if len(items)!=1 or items[0].diagnostics:raise ValueError('Câu chưa phân tích hợp lệ: '+qid[:8])
            item=items[0];source=q.latex_source;permutation=[];answer={}
            if item.question_type in ('mcq','true_false'):
                options=item.answer['options'];permutation=list(range(len(options)))
                if shuffle_options and item.question_type=='mcq':rng.shuffle(permutation)
                if item.question_type=='mcq':answer={'correct_letter':next(chr(65+i) for i,old in enumerate(permutation) if options[old]['correct'])}
                else:answer={'truth':[o['correct'] for o in options]}
                if permutation:
                    start=item.start+options[0]['start'];end=item.start+options[-1]['end']
                    source=source[:start]+'\n'.join('{'+options[i]['source']+'}' for i in permutation)+source[end:]
            elif item.question_type=='short_answer':answer={'value':item.answer['value']}
            else:answer={'essay':True}
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
        snapshot={'title':title,'questions':snapshots,'assets':global_assets}
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
        title=''.join(escape.get(ch,ch) for ch in snapshot['title'])
        lines=[r'\section*{'+title+'}']
        for i,q in enumerate(snapshot['questions'],1):
            if answer_only:
                answer=q['answer'];value=answer.get('correct_letter',answer.get('value',str(answer.get('truth','Tự luận'))))
                # Values are genuine LaTeX answers; preserve math rather than escaping.
                lines.append(f"\\noindent {i}. "+str(value)+r'\par')
            else:
                lines.append(f"\\noindent\\textbf{{Câu {i}.}}\n"+q['source'])
                if solutions and q['solution'] and not any(c.name in ('loigiai','hdan') for c in commands(q['source'])):lines.append(r'\loigiai{'+q['solution']+'}')
        return '\n\n'.join(lines)

    def export_tex(self,snapshot,path,solutions=False,answer_only=False,preamble=None):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        for reference,source in snapshot['assets'].items():
            target=path.parent/reference;target.parent.mkdir(parents=True,exist_ok=True)
            if Path(source).resolve()!=target.resolve():shutil.copyfile(source,target)
        header=preamble or BUILTIN_PREAMBLE
        if not solutions and not answer_only:header+='\n'+HIDE_ANSWERS
        document=header+'\n\\begin{document}\n'+self.content(snapshot,solutions,answer_only)+'\n\\end{document}\n'
        path.write_text(document,encoding='utf-8')
        return path

    def export_pdf(self,snapshot,path,solutions=False,answer_only=False,engine='pdflatex',preamble_file=None,cancelled=lambda:False):
        compiler=Compiler(self.services.config.data_dir,engine=engine,preamble_file=preamble_file,preamble_extra='' if solutions or answer_only else HIDE_ANSWERS)
        result=compiler.compile(self.content(snapshot,solutions,answer_only),snapshot['assets'],cancelled)
        if result.ok:shutil.copyfile(result.pdf,path)
        return result
