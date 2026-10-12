from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import uuid
from latex_question_studio.parsing.latex import parse_questions, normalized_source
from latex_question_studio.domain.question import Question
from latex_question_studio.persistence.questions import QuestionRepository
from latex_question_studio.application.assets import AssetResolver, AssetStore, serialize_graph

def detect_cognitive_level(source: str, question_type: str = ''):
    # 1. Direct tag in \begin{ex}[TAG]
    m_level = re.search(r'\\begin\{(?:ex|vidu|bt)\*?\}\s*\[([^\]]*)\]', source)
    if m_level:
        tag = m_level.group(1).upper()
        for lvl in ('VDC', 'VD', 'TH', 'NB'):
            if lvl in tag:
                return lvl
        m_code = re.search(r'[0-9][A-Z][0-9]([YBKGT])', tag)
        if m_code:
            c = m_code.group(1)
            if c in ('Y', 'N'): return 'NB'
            if c in ('B', 'T'): return 'TH'
            if c in ('K', 'V'): return 'VD'
            if c in ('G', 'C'): return 'VDC'

    # 2. Direct comment tag %[TAG]
    m_comm = re.search(r'%\s*\[?(NB|TH|VD|VDC)\]?', source, re.IGNORECASE)
    if m_comm:
        return m_comm.group(1).upper()

    # 3. Vietnamese ID6/ID5 tag %[1PxY...]
    m_id6 = re.search(r'\[[0-9][A-Za-z][0-9]([YBKGT])[0-9]?(?:-[0-9]+)?\]', source)
    if m_id6:
        code = m_id6.group(1).upper()
        if code in ('Y', 'N'): return 'NB'
        if code in ('B', 'T'): return 'TH'
        if code in ('K', 'V'): return 'VD'
        if code in ('G', 'C'): return 'VDC'

    # 4. Pedagogical content classification heuristics
    has_math = bool(
        re.search(r'\$[^\$]+=[^\$]+\$', source)
        or re.search(r'\d+[\.,]?\d*\s*(?:kg|g|J|kJ|MJ|W|kW|MW|K|cal|kcal|phút|giây|s|h|%)\b', source, re.IGNORECASE)
        or 'circ' in source.lower()
    )

    vdc_patterns = [
        r'(?:công suất|ấm điện|bếp điện|dòng điện|điện trở|hiệu điện thế|hiệu suất.*?%).*?(?:nóng chảy|hoá hơi|hóa hơi|nhiệt dung)',
        r'(?:nước đá.*?ở\s*-\s*\d+.*?hơi nước|tan hết|nóng chảy hoàn toàn.*?hóa hơi)',
        r'(?:bình cách nhiệt.*?gồm|thả.*?cục nước đá.*?vào.*?nước.*?hỏi có tan hết)',
        r'(?:hao phí.*?ra môi trường|tốc độ tỏa nhiệt|công suất hao phí)',
        r'(?:đồ thị.*?(?:giai đoạn|hình vẽ|đoạn thẳng|trục tung|trục hoành).*?(?:công suất|nhiệt dung riêng|nhiệt hóa hơi))',
        r'(?:viên đạn.*?bắn vào|rơi tự do.*?chuyển thành nhiệt|va chạm.*?nhiệt lượng)',
    ]
    for pat in vdc_patterns:
        if re.search(pat, source, re.IGNORECASE):
            return 'VDC'

    vd_patterns = [
        r'(?:tính|tìm|xác định|bằng bao nhiêu|có giá trị là).*?(?:nhiệt lượng|nội năng|công|nhiệt dung riêng|nhiệt nóng chảy|nhiệt hoá hơi|hiệu suất)',
        r'(?:phương trình cân bằng nhiệt|trao đổi nhiệt|đun sôi|làm nóng chảy|nhiệt độ cân bằng)',
        r'(?:nhận nhiệt.*?nhận công|sinh công.*?truyền nhiệt|\bQ\s*=\s*mc|\bQ\s*=\s*m\\lambda|\bQ\s*=\s*mL|\b\Delta U\b)',
        r'(?:khối lượng.*?nhiệt độ.*?nhiệt lượng)',
    ]
    is_vd = False
    for pat in vd_patterns:
        if re.search(pat, source, re.IGNORECASE):
            is_vd = True
            break

    if is_vd and has_math:
        numbers = re.findall(r'\d+[\.,]?\d*', source)
        if len(numbers) >= 4:
            return 'VD'
        else:
            return 'TH'

    if is_vd:
        return 'VD'

    if question_type == 'short_answer' and has_math:
        return 'VD'

    if question_type == 'true_false' and has_math:
        return 'TH'

    nb_patterns = [
        r'(?:định nghĩa|khái niệm|đơn vị của|kí hiệu|công thức nào sau đây|đặc điểm nào sau đây|phát biểu nào sau đây đúng|phát biểu nào sau đây sai|phát biểu nào sau đây không đúng)',
        r'(?:chuyển động brown|mô hình động học|phân tử cấu tạo|thang nhiệt độ celsius|thang nhiệt độ kelvin|chất rắn kết tinh|chất rắn vô định hình)',
        r'(?:sự nóng chảy là|sự đông đặc là|sự bay hơi là|sự ngưng tụ là|sự sôi là|nội năng của một vật là)',
        r'(?:chuyển từ thể.*?sang thể|nhiệt độ nóng chảy là|nhiệt độ sôi là)',
    ]
    for pat in nb_patterns:
        if re.search(pat, source, re.IGNORECASE) and not has_math:
            return 'NB'

    if re.search(r'(?:tại sao|vì sao|giải thích|so sánh|nguyên nhân|ảnh hưởng|phụ thuộc vào)', source, re.IGNORECASE):
        return 'TH'

    return None


class ImportCancelled(Exception):
    pass

class ImportService:
    def __init__(self, services):
        self.services = services
        self.root = services.config.data_dir
        self.resolver = AssetResolver()
        self.asset_store = AssetStore(self.root)

    def stage(self, paths, cancelled=lambda: False, progress=lambda done, total: None):
        batch = str(uuid.uuid4())
        results, source_records = [], []
        from latex_question_studio.persistence.analysis import ensure,PARSER_VERSION
        try:ensure(self.services.database,cancelled=cancelled)
        except InterruptedError as error:raise ImportCancelled(str(error)) from error

        paths = sorted(set(Path(p).resolve() for p in paths))
        for number, path in enumerate(paths):
            if cancelled(): raise ImportCancelled()
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            archive = self.root / 'sources' / (digest + '.bin')
            archive.parent.mkdir(parents=True, exist_ok=True)
            if not archive.exists(): archive.write_bytes(raw)
            file_id = str(uuid.uuid4())
            encoding = 'utf-8-sig'
            try:
                if raw.startswith((b'\xff\xfe', b'\xfe\xff')): encoding = 'utf-16'
                source = raw.decode(encoding)
                parsed = parse_questions(source)
            except UnicodeError:
                source, parsed = '', []
            source_records.append((file_id, str(path), encoding, str(archive.relative_to(self.root)), digest))
            graph = None
            if source:
                graph = self.resolver.resolve(source, path, cancelled)
            graph_by_reference = graph.by_reference() if graph else {}
            if not parsed:
                results.append({'id':str(uuid.uuid4()),'file_id':file_id,'path':str(path),'source':'', 'start':0,'end':len(raw),
                    'errors':[{'message':'Không giải mã được file; byte gốc đã lưu trong archive','line':1,'column':1}], 'parsed':{}})
            for item in parsed:
                if cancelled():raise ImportCancelled('Đã hủy nhập câu hỏi')
                errors = [asdict(d) for d in item.diagnostics]
                assets = []
                for reference in item.assets:
                    resolution = next((entry for entry in graph_by_reference.get(reference, ()) if entry.dependency_type == 'image'), None)
                    if resolution and resolution.resolution_status == 'RESOLVED' and resolution.selected_path:
                        found = Path(resolution.selected_path)
                        asset_raw = found.read_bytes()
                        asset_hash = hashlib.sha256(asset_raw).hexdigest()
                        stored = self.asset_store.stage_bytes(asset_raw, found.suffix.lower(), batch)
                        assets.append({'reference':reference,'hash':asset_hash,'relative_path':stored['relative_path'],
                                       'staging_path':stored['staging_path'],
                                       'bytes':len(asset_raw),'source_context':resolution.source_context,
                                       'dependency_type':resolution.dependency_type,'resolution_status':resolution.resolution_status,
                                       'candidates':list(resolution.candidates)})
                    else:
                        status = resolution.resolution_status if resolution else 'MISSING_ASSET'
                        message = resolution.message if resolution else f'Thiếu tài nguyên: {reference}'
                        assets.append({'reference':reference,'hash':'','relative_path':'','staging_path':'','bytes':0,
                                       'source_context':resolution.source_context if resolution else str(path.parent.resolve()),
                                       'dependency_type':resolution.dependency_type if resolution else 'image',
                                       'resolution_status':status,'candidates':list(resolution.candidates) if resolution else []})
                        errors.append({'message':f'{status}: {reference} — {message}','line':source.count('\n',0,item.start)+1,'column':1})
                if graph:
                    for dependency in graph.references:
                        if dependency.resolution_status != 'RESOLVED' and dependency.dependency_type != 'image':
                            errors.append({'message':f'{dependency.resolution_status}: {dependency.original_reference} — {dependency.message}',
                                           'line':source.count('\n',0,item.start)+1,'column':1})
                cog_level = detect_cognitive_level(item.source, item.question_type)
                parsed_data = {'type':item.question_type,'solution':item.solution,'answer':item.answer,'environment':item.environment,
                    'assets':assets,'resource_graph':serialize_graph(graph) if graph else None,
                    'analysis_hash':hashlib.sha256(item.source.encode()).hexdigest(),'analysis_version':PARSER_VERSION,'analysis_start':0,'analysis_end':len(item.source)}
                if cog_level:
                    parsed_data['classification'] = {'cognitive_level': cog_level}
                results.append({'id':str(uuid.uuid4()),'file_id':file_id,'path':str(path),'source':item.source,'start':item.start,'end':item.end,
                    'errors':errors,'parsed':parsed_data})
            progress(number + 1, len(paths))
        hashes=[hashlib.sha256(normalized_source(r['source']).encode()).hexdigest() for r in results]
        existing=set()
        with self.services.database.connect() as c:
            for start in range(0,len(hashes),256):
                if cancelled():raise ImportCancelled('Đã hủy nhập câu hỏi')
                chunk=hashes[start:start+256]
                existing.update(r[0] for r in c.execute('SELECT DISTINCT normalized_hash FROM question_analysis WHERE normalized_hash IN ('+','.join('?' for _ in chunk)+')',chunk))
        seen=set()
        for result,key in zip(results,hashes):
            result['duplicate']=key in existing or key in seen;seen.add(key)
            result['parsed']['duplicate_suggestion']=result['duplicate']
        if cancelled(): raise ImportCancelled()
        with self.services.database.transaction() as connection:
            connection.execute('INSERT INTO import_batches VALUES (?,?,?)',(batch,'staged',datetime.now(timezone.utc).isoformat()))
            connection.executemany('INSERT INTO source_files VALUES (?,?,?,?,?)',source_records)
            for result in results:
                if cancelled():raise ImportCancelled('Đã hủy nhập câu hỏi')
                connection.execute('INSERT INTO import_items(id,batch_id,source_file_id,start_offset,end_offset,raw_source,status,diagnostics_json,parsed_json,question_id) VALUES (?,?,?,?,?,?,?,?,?,NULL)',(
                    result['id'],batch,result['file_id'],result['start'],result['end'],result['source'],
                    'error' if result['errors'] else 'ready',json.dumps(result['errors'],ensure_ascii=False),json.dumps(result['parsed'],ensure_ascii=False)))
        return batch, results

    def assign_classification(self,item_ids,taxonomy_id,cognitive_level):
        from latex_question_studio.domain.curriculum import classification
        if cognitive_level not in (None,'NB','TH','VD','VDC'):raise ValueError('Mức độ không hợp lệ')
        with self.services.database.transaction() as c:
            nodes=[dict(r) for r in c.execute('SELECT t.*,p.subject AS profile_subject,p.grade AS profile_grade FROM taxonomy_nodes t LEFT JOIN curriculum_profiles p ON p.root_id=t.id')]
            if taxonomy_id not in {n['id'] for n in nodes}:raise ValueError('Chọn bài hoặc dạng trên cây CSDL')
            values={**classification(nodes,taxonomy_id),'taxonomy_id':taxonomy_id,'cognitive_level':cognitive_level}
            for item_id in item_ids:
                row=c.execute("SELECT parsed_json FROM import_items WHERE id=? AND status IN ('ready','error')",(item_id,)).fetchone()
                if not row:raise ValueError('Câu không còn trong hàng chờ')
                data=json.loads(row[0]);data['classification']=values
                c.execute('UPDATE import_items SET parsed_json=? WHERE id=?',(json.dumps(data,ensure_ascii=False),item_id))
        return values

    def commit(self, batch, selected_ids=None, cancelled=lambda:False):
        try:
            return self._commit(batch, selected_ids, cancelled)
        finally:
            # A canceled or failed commit must not leave a durable staging tree.
            self.asset_store.cleanup_batch(batch)

    def _commit(self, batch, selected_ids=None, cancelled=lambda:False):
        count = 0
        now = datetime.now(timezone.utc).isoformat()
        with self.services.database.transaction() as connection:
            for row in connection.execute("SELECT * FROM import_items WHERE batch_id=? AND status='ready'",(batch,)).fetchall():
                if cancelled():raise ImportCancelled('Đã hủy ghi batch; dữ liệu chưa được ghi')
                if selected_ids is not None and row['id'] not in selected_ids: continue
                data = json.loads(row['parsed_json'])
                question = Question(str(uuid.uuid4()),(row['working_source'] if row['working_source'] is not None else row['raw_source']),data['type'],data['solution'],None,data.get('classification',{}).get('cognitive_level'),1)
                connection.execute('INSERT INTO questions VALUES (?,?,?,?,?,?,?,?,?)',(
                    question.id,question.latex_source,question.question_type,question.solution,None,question.cognitive_level,1,now,now))
                connection.execute('INSERT INTO question_metadata VALUES (?,?)',(question.id,json.dumps({'answer':data['answer'],'environment':data['environment'],'source_origin':'original','import_item':row['id'],**data.get('classification',{})},ensure_ascii=False)))
                from latex_question_studio.persistence.analysis import record,PARSER_VERSION
                cached=None
                if data.get('analysis_version')==PARSER_VERSION and data.get('analysis_hash')==hashlib.sha256(question.latex_source.encode()).hexdigest():
                    from latex_question_studio.parsing.latex import ParsedQuestion
                    start=data['analysis_start'];end=data['analysis_end']
                    cached=[ParsedQuestion(question.latex_source[start:end],start,end,data['environment'],data['type'],data['solution'],data['answer'],[a['reference'] for a in data['assets']],[])]
                record(connection,question.id,question.latex_source,cached)
                values=data.get('classification',{})
                if values.get('taxonomy_id'):
                    connection.execute('INSERT INTO question_taxonomy VALUES (?,?)',(question.id,values['taxonomy_id']))
                snapshot={**question.__dict__,'metadata':{'answer':data['answer'],'environment':data['environment'],'source_origin':'original','import_item':row['id'],**values}}
                connection.execute('INSERT INTO question_revisions VALUES (?,?,?,?)',(question.id,1,json.dumps(snapshot,ensure_ascii=False),now))
                for asset in data.get('assets',[]):
                    self.asset_store.promote(asset)
                    connection.execute('INSERT OR IGNORE INTO assets VALUES (?,?,?,?)',(asset['hash'],asset['hash'],asset['relative_path'],asset['bytes']))
                    connection.execute('INSERT INTO question_assets(question_id,asset_id,original_reference,source_context,dependency_type,resolution_status,candidates_json) VALUES (?,?,?,?,?,?,?)',
                                       (question.id,asset['hash'],asset['reference'],asset.get('source_context','legacy'),asset.get('dependency_type','image'),asset.get('resolution_status','RESOLVED'),json.dumps(asset.get('candidates',[]),ensure_ascii=False)))
                connection.execute("UPDATE import_items SET status='imported',question_id=? WHERE id=?",(question.id,row['id']))
                count += 1
            connection.execute("UPDATE import_batches SET status='reviewed' WHERE id=?",(batch,))
        return count

    def pending(self):
        with self.services.database.connect() as connection:
            return [dict(row) for row in connection.execute("SELECT i.*,s.original_path FROM import_items i JOIN source_files s ON i.source_file_id=s.id WHERE i.status IN ('error','ready') ORDER BY i.rowid DESC LIMIT 500")]

    def repair(self,item_id,source):
        from latex_question_studio.parsing.latex import parse_questions
        with self.services.database.connect() as c:
            row=c.execute('SELECT i.*,s.original_path FROM import_items i JOIN source_files s ON s.id=i.source_file_id WHERE i.id=?',(item_id,)).fetchone()
        if not row or row['status']=='imported':raise ValueError('Mục không còn trong hàng chờ')
        items=parse_questions(source)
        if len(items)!=1:raise ValueError('Mỗi mục sửa phải chứa đúng một câu')
        item=items[0];errors=[asdict(d) for d in item.diagnostics];assets=[]
        graph=self.resolver.resolve(source,Path(row['original_path']),lambda:False)
        graph_by_reference=graph.by_reference()
        for reference in item.assets:
            resolution=next((entry for entry in graph_by_reference.get(reference,()) if entry.dependency_type=='image'),None)
            found=Path(resolution.selected_path) if resolution and resolution.resolution_status=='RESOLVED' and resolution.selected_path else None
            if not found:errors.append({'message':(resolution.resolution_status if resolution else 'MISSING_ASSET')+': '+reference,'line':1,'column':1});continue
            raw=found.read_bytes();digest=hashlib.sha256(raw).hexdigest();stored=self.asset_store.stage_bytes(raw,found.suffix.lower(),row['batch_id'])
            assets.append({'reference':reference,'hash':digest,'relative_path':stored['relative_path'],'staging_path':stored['staging_path'],'bytes':len(raw),
                           'source_context':resolution.source_context,'dependency_type':resolution.dependency_type,
                           'resolution_status':resolution.resolution_status,'candidates':list(resolution.candidates)})
        from latex_question_studio.persistence.analysis import PARSER_VERSION
        classification = json.loads(row['parsed_json']).get('classification', {})
        if 'cognitive_level' not in classification:
            detected = detect_cognitive_level(source)
            if detected:
                classification['cognitive_level'] = detected
        data={'classification':classification,'type':item.question_type,'solution':item.solution,'answer':item.answer,'environment':item.environment,'assets':assets,
              'resource_graph':serialize_graph(graph),'analysis_hash':hashlib.sha256(source.encode()).hexdigest(),'analysis_version':PARSER_VERSION,'analysis_start':item.start,'analysis_end':item.end}
        with self.services.database.transaction() as c:
            c.execute('UPDATE import_items SET working_source=?,diagnostics_json=?,parsed_json=?,status=? WHERE id=?',(source,json.dumps(errors,ensure_ascii=False),json.dumps(data,ensure_ascii=False),'error' if errors else 'ready',item_id))
            c.execute('INSERT INTO import_repairs VALUES (?,?,?,?,?)',(str(uuid.uuid4()),item_id,source,json.dumps(errors,ensure_ascii=False),datetime.now(timezone.utc).isoformat()))
        return errors
