import hashlib
import json
import os
from pathlib import Path
from datetime import datetime,timezone
import random
import shutil
import tempfile
import uuid
import zipfile
from latex_question_studio.parsing.latex import parse_questions,commands,group,skip_space
from latex_question_studio.application.search import SearchService
from latex_question_studio.preview.compiler import Compiler, BUILTIN_PREAMBLE, MAPCLASS_PREAMBLE, default_profile_root

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
                source = q['source']
                if not solutions:
                    from latex_question_studio.application.lessons import student_source
                    try:
                        source = student_source(source, hide_answers=True)
                    except ValueError as err:
                        qid = q.get('question_id', '')
                        msg = str(err)
                        if qid and not msg.startswith('Câu hỏi'):
                            msg = f"Câu hỏi {qid[:8]}: {msg}"
                        raise ValueError(msg) from err
                if any(env in source for env in (r'\begin{ex}', r'\begin{bt}')):
                    lines.append(source)
                else:
                    lines.append(f"\\noindent\\textbf{{Câu {i}.}}\n" + source)
                if solutions and q['solution'] and not any(c.name in ('loigiai','hdan') for c in commands(q['source'])):lines.append(r'\loigiai{'+q['solution']+'}')
        return '\n\n'.join(lines)

    @staticmethod
    def copy_class_dependencies(target_folder, raise_on_missing=False):
        """Sao chép MAPClass.cls và Packages/ex_test.sty vào thư mục xuất đề."""
        copied = []
        missing = []
        root = default_profile_root()
        target_folder = Path(target_folder)
        target_folder.mkdir(parents=True, exist_ok=True)

        probe = target_folder / '.write_probe'
        try:
            probe.write_text('probe', encoding='utf-8')
            probe.unlink(missing_ok=True)
        except Exception as e:
            raise PermissionError(f"Không có quyền ghi vào thư mục: {target_folder}") from e

        mapclass_src = root / 'Class' / 'MAPClass.cls'
        if not mapclass_src.is_file():
            alt = root / 'MAPClass.cls'
            if alt.is_file():
                mapclass_src = alt
        if mapclass_src.is_file():
            shutil.copyfile(mapclass_src, target_folder / 'MAPClass.cls')
            copied.append('MAPClass.cls')
        else:
            missing.append('MAPClass.cls')

        extest_src = root / 'Packages' / 'ex_test.sty'
        if not extest_src.is_file():
            alt = root / 'ex_test.sty'
            if alt.is_file():
                extest_src = alt
        if extest_src.is_file():
            pkg_dir = target_folder / 'Packages'
            pkg_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(extest_src, pkg_dir / 'ex_test.sty')
            shutil.copyfile(extest_src, target_folder / 'ex_test.sty')
            copied.append('Packages/ex_test.sty')
        else:
            missing.append('Packages/ex_test.sty')

        if raise_on_missing and missing:
            raise FileNotFoundError(f"Thiếu file phụ thuộc lớp LaTeX: {', '.join(missing)}")
        return {'copied': copied, 'missing': missing}

    def preflight_export(self, snapshot, target_folder, engine='pdflatex', preamble_file=None, style='mapclass'):
        """Kiểm tra trước khi export: quyền ghi, class, package, preamble, engine và assets."""
        errors = []
        warnings = []
        missing_assets = []
        missing_deps = []

        # 1. Kiểm tra quyền ghi thư mục đích
        target_folder = Path(target_folder)
        try:
            target_folder.mkdir(parents=True, exist_ok=True)
            probe = target_folder / f'.probe_{os.getpid()}'
            probe.write_text('probe', encoding='utf-8')
            probe.unlink(missing_ok=True)
        except Exception as e:
            errors.append(f"Không thể ghi vào thư mục '{target_folder}': {e}")

        # 2. Kiểm tra preamble file nếu có
        if preamble_file:
            pf = Path(preamble_file)
            if not pf.is_file():
                errors.append(f"Không tìm thấy file preamble: {preamble_file}")

        # 3. Kiểm tra class dependencies nếu dùng mapclass
        if style == 'mapclass' or preamble_file is None:
            root = default_profile_root()
            mapclass = root / 'Class' / 'MAPClass.cls'
            if not mapclass.is_file() and not (root / 'MAPClass.cls').is_file():
                missing_deps.append('MAPClass.cls')
            extest = root / 'Packages' / 'ex_test.sty'
            if not extest.is_file() and not (root / 'ex_test.sty').is_file():
                missing_deps.append('Packages/ex_test.sty')
            if missing_deps:
                warnings.append(f"Thiếu file phụ thuộc lớp LaTeX trong profile: {', '.join(missing_deps)}")

        # 4. Kiểm tra engine biên dịch
        compiler = Compiler(self.services.config.data_dir, engine=engine)
        if not compiler.engine_path():
            warnings.append(f"Không tìm thấy trình biên dịch LaTeX '{engine}' trên hệ thống (chỉ có thể xuất TeX)")

        # 5. Kiểm tra assets trong snapshot
        for ref, src in snapshot.get('assets', {}).items():
            if not Path(src).is_file():
                missing_assets.append(ref)
        if missing_assets:
            warnings.append(f"Không tìm thấy file ảnh tài nguyên: {', '.join(missing_assets)}")

        return {
            'ok': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'missing_assets': missing_assets,
            'missing_deps': missing_deps
        }

    def export_tex(self, snapshot, path, solutions=False, answer_only=False, preamble=None, bundle_dependencies=True):
        body = self.content(snapshot, solutions, answer_only)
        # A solution-only image is an answer too; do not copy it into student folders.
        references = set()
        for cmd in commands(body):
            if cmd.name != 'includegraphics':
                continue
            cursor = skip_space(body, cmd.end)
            if cursor < len(body) and body[cursor] == '*':
                cursor = skip_space(body, cursor + 1)
            if cursor < len(body) and body[cursor] == '[':
                _, cursor, _ = group(body, cursor, '[', ']')
            references.add(group(body, cursor)[0])
        path = Path(path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        for reference, source in snapshot.get('assets', {}).items():
            if reference not in references:
                continue
            target = (path.parent / reference).resolve()
            # Bảo vệ chống Path Traversal
            try:
                target.relative_to(path.parent.resolve())
            except ValueError:
                raise ValueError(f"Phát hiện đường dẫn tài nguyên không an toàn (path traversal): {reference}")
            target.parent.mkdir(parents=True, exist_ok=True)
            if Path(source).resolve() != target.resolve() and Path(source).is_file():
                shutil.copyfile(source, target)
        header = preamble or BUILTIN_PREAMBLE
        if not solutions and not answer_only:
            header += '\n' + HIDE_ANSWERS
        document = header + '\n\\begin{document}\n' + body + '\n\\end{document}\n'
        path.write_text(document, encoding='utf-8')
        dep_info = {'copied': [], 'missing': []}
        if bundle_dependencies and ('MAPClass' in header or preamble is None):
            dep_info = self.copy_class_dependencies(path.parent)
        return path

    def export_pdf(self, snapshot, path, solutions=False, answer_only=False, engine='pdflatex', preamble_file=None, cancelled=lambda: False):
        compiler = Compiler(self.services.config.data_dir, engine=engine, preamble_file=preamble_file, preamble_extra='' if solutions or answer_only else HIDE_ANSWERS)
        result = compiler.compile(self.content(snapshot, solutions, answer_only), snapshot.get('assets', {}), cancelled)
        if result.ok and result.pdf:
            shutil.copyfile(result.pdf, path)
        return result

    def export_bundle(
        self,
        snapshot,
        folder,
        export_student=True,
        export_teacher=True,
        export_answers=True,
        style='mapclass',
        compile_pdf=True,
        engine='pdflatex',
        preamble_file=None,
        cancelled=lambda: False,
        progress=lambda a, b: None
    ):
        """Xuất trọn gói thư mục tự trị (Self-contained Project) gồm:
        - Các file .tex đã chọn (học sinh / giáo viên / đáp án)
        - Biên dịch sẵn các file .pdf tương ứng chất lượng cao
        - Tự động đóng gói MAPClass.cls, Packages/ex_test.sty và toàn bộ ảnh assets
        - File tự biên dịch nhanh trên Windows: bien-dich.bat
        - File hướng dẫn sử dụng: HUONG_DAN_BIEN_DICH.txt
        - File manifest.json đầy đủ hash SHA256 và audience
        """
        folder = Path(folder).resolve()
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / f'.probe_{os.getpid()}'
        try:
            probe.write_text('probe', encoding='utf-8')
            probe.unlink(missing_ok=True)
        except Exception as e:
            raise PermissionError(f"Không có quyền ghi vào thư mục: {folder}") from e

        if cancelled():
            raise InterruptedError('Đã hủy xuất đề thi')

        if preamble_file:
            preamble = Path(preamble_file).read_text(encoding='utf-8-sig')
        elif style == 'mapclass':
            preamble = MAPCLASS_PREAMBLE
        else:
            preamble = BUILTIN_PREAMBLE

        created_tex = []
        created_pdf = []
        errors = []

        # Xác định đối tượng (audience)
        if export_student and not export_teacher and not export_answers:
            audience = 'student'
        elif export_teacher and not export_student and not export_answers:
            audience = 'teacher'
        elif export_answers and not export_student and not export_teacher:
            audience = 'answers'
        else:
            audience = 'all'

        total_steps = (int(export_student) + int(export_teacher) + int(export_answers)) * (2 if compile_pdf else 1)
        total_steps = max(total_steps, 1)
        step = 0

        # 1. Đề thi học sinh (Ẩn lời giải & đáp án)
        if export_student:
            if cancelled():
                raise InterruptedError('Đã hủy xuất đề thi')
            student_tex = folder / 'de-thi-hoc-sinh.tex'
            self.export_tex(snapshot, student_tex, solutions=False, answer_only=False, preamble=preamble, bundle_dependencies=False)
            created_tex.append(student_tex)
            step += 1
            progress(step, total_steps)

            if compile_pdf:
                student_pdf = folder / 'de-thi-hoc-sinh.pdf'
                res = self.export_pdf(snapshot, student_pdf, solutions=False, answer_only=False, engine=engine, preamble_file=preamble_file, cancelled=cancelled)
                if res.ok:
                    created_pdf.append(student_pdf)
                else:
                    errors.append(('Đề học sinh', res.log))
                step += 1
                progress(step, total_steps)

        # 2. Đề thi giáo viên (Hiện lời giải chi tiết & đáp án)
        if export_teacher:
            if cancelled():
                raise InterruptedError('Đã hủy xuất đề thi')
            teacher_tex = folder / 'de-thi-giao-vien.tex'
            self.export_tex(snapshot, teacher_tex, solutions=True, answer_only=False, preamble=preamble, bundle_dependencies=False)
            created_tex.append(teacher_tex)
            step += 1
            progress(step, total_steps)

            if compile_pdf:
                teacher_pdf = folder / 'de-thi-giao-vien.pdf'
                res = self.export_pdf(snapshot, teacher_pdf, solutions=True, answer_only=False, engine=engine, preamble_file=preamble_file, cancelled=cancelled)
                if res.ok:
                    created_pdf.append(teacher_pdf)
                else:
                    errors.append(('Đề giáo viên', res.log))
                step += 1
                progress(step, total_steps)

        # 3. Bảng đáp án
        if export_answers:
            if cancelled():
                raise InterruptedError('Đã hủy xuất đề thi')
            answers_tex = folder / 'dap-an.tex'
            self.export_tex(snapshot, answers_tex, solutions=False, answer_only=True, preamble=preamble, bundle_dependencies=False)
            created_tex.append(answers_tex)
            step += 1
            progress(step, total_steps)

            if compile_pdf:
                answers_pdf = folder / 'dap-an.pdf'
                res = self.export_pdf(snapshot, answers_pdf, solutions=False, answer_only=True, engine=engine, preamble_file=preamble_file, cancelled=cancelled)
                if res.ok:
                    created_pdf.append(answers_pdf)
                else:
                    errors.append(('Bảng đáp án', res.log))
                step += 1
                progress(step, total_steps)

        # 4. Sao chép các file phụ thuộc của MAPClass nếu dùng MAPClass
        dep_info = {'copied': [], 'missing': []}
        if style == 'mapclass' or preamble_file is None:
            dep_info = self.copy_class_dependencies(folder)

        # 5. Tạo file biên dịch nhanh Windows bien-dich.bat
        bat_content = (
            "@echo off\r\n"
            "chcp 65001 >nul\r\n"
            "echo ========================================================\r\n"
            "echo DANG BIEN DICH DE THI BANG PDFLATEX (MCPTEST)\r\n"
            "echo ========================================================\r\n"
            "if exist de-thi-hoc-sinh.tex (\r\n"
            "    echo [1/3] Dang bien dich de-thi-hoc-sinh.tex...\r\n"
            "    pdflatex -interaction=nonstopmode de-thi-hoc-sinh.tex\r\n"
            ")\r\n"
            "if exist de-thi-giao-vien.tex (\r\n"
            "    echo [2/3] Dang bien dich de-thi-giao-vien.tex...\r\n"
            "    pdflatex -interaction=nonstopmode de-thi-giao-vien.tex\r\n"
            ")\r\n"
            "if exist dap-an.tex (\r\n"
            "    echo [3/3] Dang bien dich dap-an.tex...\r\n"
            "    pdflatex -interaction=nonstopmode dap-an.tex\r\n"
            ")\r\n"
            "echo ========================================================\r\n"
            "echo HOAN TAT! Ban co the mo cac file PDF vua tao.\r\n"
            "echo ========================================================\r\n"
            "pause\r\n"
        )
        (folder / 'bien-dich.bat').write_text(bat_content, encoding='utf-8')

        # 6. Tạo file hướng dẫn biên dịch chi tiết HUONG_DAN_BIEN_DICH.txt
        guide_content = (
            "HƯỚNG DẪN SỬ DỤNG VÀ BIÊN DỊCH BỘ ĐỀ THI (MCPTEST)\n"
            "====================================================\n\n"
            "1. SỬ DỤNG VÀ IN ẤN NGAY:\n"
            "   - Thư mục này đã có sẵn các file PDF được biên dịch hoàn chỉnh:\n"
            "     * de-thi-hoc-sinh.pdf : Đề thi in phát cho học sinh (đã ẩn lời giải & đáp án).\n"
            "     * de-thi-giao-vien.pdf: Đề thi dành cho giáo viên (kèm lời giải chi tiết & đáp án).\n"
            "     * dap-an.pdf          : Bảng tra cứu đáp án trắc nghiệm.\n\n"
            "2. CHỈNH SỬA BẰNG TEXSTUDIO / OVERLEAF / MIKTEX:\n"
            "   - Thư mục đã bao gồm sẵn file MAPClass.cls, Packages/ex_test.sty và thư mục ảnh assets/.\n"
            "   - Mở de-thi-hoc-sinh.tex hoặc de-thi-giao-vien.tex bằng TeXStudio rồi bấm F5 (Biên dịch).\n"
            "   - Hoặc nén toàn bộ thư mục này thành file .ZIP rồi tải lên Overleaf (New Project -> Upload Project).\n\n"
            "3. BIÊN DỊCH TỰ ĐỘNG TRÊN WINDOWS:\n"
            "   - Nhấp đúp chuột vào file 'bien-dich.bat' để tự động chạy pdfLaTeX.\n"
        )
        (folder / 'HUONG_DAN_BIEN_DICH.txt').write_text(guide_content, encoding='utf-8')

        # 7. Ghi manifest JSON để kiểm tra tính toàn vẹn
        files_hash = {
            file.relative_to(folder).as_posix(): hashlib.sha256(file.read_bytes()).hexdigest()
            for file in sorted(folder.rglob('*')) if file.is_file() and file.name != 'manifest.json'
        }
        manifest = {
            'format': 1,
            'title': snapshot.get('title', 'Đề thi'),
            'exam_code': snapshot.get('exam_code', '101'),
            'question_count': len(snapshot.get('questions', [])),
            'audience': audience,
            'style': style,
            'engine': engine,
            'dependencies': dep_info,
            'sha256': files_hash
        }
        (folder / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

        return {
            'folder': str(folder),
            'created_tex': created_tex,
            'created_pdf': created_pdf,
            'dependencies': dep_info,
            'errors': errors,
            'ok': len(errors) == 0
        }

    def export_zip(
        self,
        snapshot,
        path,
        solutions=False,
        preamble=None,
        export_student=None,
        export_teacher=None,
        export_answers=None,
        style='mapclass',
        compile_pdf=True,
        engine='pdflatex',
        preamble_file=None,
        raise_on_compile_error=False,
        cancelled=lambda: False
    ):
        """Tạo gói đề Portable ZIP tự trị chứa toàn bộ TeX + PDF + MAPClass + Assets."""
        path = Path(path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        if export_student is None and export_teacher is None and export_answers is None:
            export_student = not solutions
            export_teacher = solutions
            export_answers = False
        else:
            export_student = bool(export_student)
            export_teacher = bool(export_teacher)
            export_answers = bool(export_answers)

        with tempfile.TemporaryDirectory(prefix='.exam-bundle-', dir=path.parent, ignore_cleanup_errors=True) as temporary:
            folder = Path(temporary)
            bundle_res = self.export_bundle(
                snapshot,
                folder,
                export_student=export_student,
                export_teacher=export_teacher,
                export_answers=export_answers,
                style=style,
                compile_pdf=compile_pdf,
                engine=engine,
                preamble_file=preamble_file,
                cancelled=cancelled
            )

            # Tạo alias main.tex để tương thích với các công cụ đọc gói cũ
            if (folder / 'de-thi-hoc-sinh.tex').is_file() and not (folder / 'main.tex').is_file():
                shutil.copyfile(folder / 'de-thi-hoc-sinh.tex', folder / 'main.tex')
            elif (folder / 'de-thi-giao-vien.tex').is_file() and not (folder / 'main.tex').is_file():
                shutil.copyfile(folder / 'de-thi-giao-vien.tex', folder / 'main.tex')

            # Cập nhật manifest để bao gồm main.tex, compilation status và toàn bộ file trong zip
            manifest_file = folder / 'manifest.json'
            if manifest_file.is_file():
                manifest_data = json.loads(manifest_file.read_text(encoding='utf-8'))
                files_hash = {
                    file.relative_to(folder).as_posix(): hashlib.sha256(file.read_bytes()).hexdigest()
                    for file in sorted(folder.rglob('*')) if file.is_file() and file.name != 'manifest.json'
                }
                manifest_data['sha256'] = files_hash
                manifest_data['compilation'] = {
                    'ok': bundle_res['ok'],
                    'errors': [name for name, _ in bundle_res.get('errors', [])]
                }
                manifest_file.write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding='utf-8')

            if cancelled():
                raise InterruptedError('Đã hủy xuất gói đề')

            if compile_pdf and not bundle_res['ok'] and raise_on_compile_error:
                err_details = "; ".join(f"{name}: {log[:200]}" for name, log in bundle_res['errors'])
                raise RuntimeError(f"Biên dịch PDF thất bại trong gói xuất đề: {err_details}")

            temporary_zip = path.with_suffix(path.suffix + f'.tmp_{os.getpid()}')
            with zipfile.ZipFile(temporary_zip, 'w', zipfile.ZIP_DEFLATED) as archive:
                for file in sorted(folder.rglob('*')):
                    if file.is_file():
                        archive.write(file, file.relative_to(folder).as_posix())
            temporary_zip.replace(path)
        return path
