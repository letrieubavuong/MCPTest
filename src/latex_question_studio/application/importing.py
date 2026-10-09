from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import uuid
from latex_question_studio.parsing.latex import parse_questions, normalized_source
from latex_question_studio.domain.question import Question
from latex_question_studio.persistence.questions import QuestionRepository

class ImportCancelled(Exception):
    pass

class ImportService:
    def __init__(self, services):
        self.services = services
        self.root = services.config.data_dir

    def stage(self, paths, cancelled=lambda: False, progress=lambda done, total: None):
        batch = str(uuid.uuid4())
        results, source_records = [], []
        with self.services.database.connect() as c:
            known = {normalized_source(r[0]) for r in c.execute('SELECT latex_source FROM questions')}

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
            if not parsed:
                results.append({'id':str(uuid.uuid4()),'file_id':file_id,'path':str(path),'source':'', 'start':0,'end':len(raw),
                    'errors':[{'message':'Không giải mã được file; byte gốc đã lưu trong archive','line':1,'column':1}], 'parsed':{}})
            for item in parsed:
                errors = [asdict(d) for d in item.diagnostics]
                assets = []
                for reference in item.assets:
                    candidate = path.parent / reference
                    options = [candidate] if candidate.suffix else [candidate.with_suffix(ext) for ext in ('.pdf','.png','.jpg','.jpeg')]
                    found = next((p for p in options if p.is_file()), None)
                    if found:
                        asset_raw = found.read_bytes()
                        asset_hash = hashlib.sha256(asset_raw).hexdigest()
                        stored = self.root / 'assets' / (asset_hash + found.suffix.lower())
                        stored.parent.mkdir(parents=True, exist_ok=True)
                        if not stored.exists(): stored.write_bytes(asset_raw)
                        assets.append({'reference':reference,'hash':asset_hash,'relative_path':str(stored.relative_to(self.root)),'bytes':len(asset_raw)})
                    else:
                        errors.append({'message':f'Thiếu tài nguyên: {reference}','line':source.count('\n',0,item.start)+1,'column':1})
                results.append({'id':str(uuid.uuid4()),'file_id':file_id,'path':str(path),'source':item.source,'start':item.start,'end':item.end,
                    'errors':errors,'parsed':{'type':item.question_type,'solution':item.solution,'answer':item.answer,'environment':item.environment,'assets':assets}})
            progress(number + 1, len(paths))
        for result in results:
            key = normalized_source(result['source'])
            result['duplicate'] = key in known
            known.add(key)
            result['parsed']['duplicate_suggestion'] = result['duplicate']
        if cancelled(): raise ImportCancelled()
        with self.services.database.transaction() as connection:
            connection.execute('INSERT INTO import_batches VALUES (?,?,?)',(batch,'staged',datetime.now(timezone.utc).isoformat()))
            connection.executemany('INSERT INTO source_files VALUES (?,?,?,?,?)',source_records)
            for result in results:
                connection.execute('INSERT INTO import_items(id,batch_id,source_file_id,start_offset,end_offset,raw_source,status,diagnostics_json,parsed_json,question_id) VALUES (?,?,?,?,?,?,?,?,?,NULL)',(
                    result['id'],batch,result['file_id'],result['start'],result['end'],result['source'],
                    'error' if result['errors'] else 'ready',json.dumps(result['errors'],ensure_ascii=False),json.dumps(result['parsed'],ensure_ascii=False)))
        return batch, results

    def commit(self, batch, selected_ids=None):
        count = 0
        now = datetime.now(timezone.utc).isoformat()
        with self.services.database.transaction() as connection:
            for row in connection.execute("SELECT * FROM import_items WHERE batch_id=? AND status='ready'",(batch,)).fetchall():
                if selected_ids is not None and row['id'] not in selected_ids: continue
                data = json.loads(row['parsed_json'])
                question = Question(str(uuid.uuid4()),(row['working_source'] if row['working_source'] is not None else row['raw_source']),data['type'],data['solution'],None,None,1)
                connection.execute('INSERT INTO questions VALUES (?,?,?,?,?,?,?,?,?)',(
                    question.id,question.latex_source,question.question_type,question.solution,None,None,1,now,now))
                QuestionRepository._snapshot(connection,question,now)
                connection.execute('INSERT INTO question_metadata VALUES (?,?)',(question.id,json.dumps({'answer':data['answer'],'environment':data['environment'],'source_origin':'original','import_item':row['id']},ensure_ascii=False)))
                for asset in data['assets']:
                    connection.execute('INSERT OR IGNORE INTO assets VALUES (?,?,?,?)',(asset['hash'],asset['hash'],asset['relative_path'],asset['bytes']))
                    connection.execute('INSERT INTO question_assets VALUES (?,?,?)',(question.id,asset['hash'],asset['reference']))
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
        for reference in item.assets:
            candidate=Path(row['original_path']).parent/reference
            options=[candidate] if candidate.suffix else [candidate.with_suffix(ext) for ext in ('.pdf','.png','.jpg','.jpeg')]
            found=next((p for p in options if p.is_file()),None)
            if not found:errors.append({'message':'Thiếu ảnh: '+reference,'line':1,'column':1});continue
            raw=found.read_bytes();digest=hashlib.sha256(raw).hexdigest();stored=self.root/'assets'/(digest+found.suffix.lower());stored.parent.mkdir(exist_ok=True)
            if not stored.exists():stored.write_bytes(raw)
            assets.append({'reference':reference,'hash':digest,'relative_path':str(stored.relative_to(self.root)),'bytes':len(raw)})
        data={'type':item.question_type,'solution':item.solution,'answer':item.answer,'environment':item.environment,'assets':assets}
        with self.services.database.transaction() as c:
            c.execute('UPDATE import_items SET working_source=?,diagnostics_json=?,parsed_json=?,status=? WHERE id=?',(source,json.dumps(errors,ensure_ascii=False),json.dumps(data,ensure_ascii=False),'error' if errors else 'ready',item_id))
            c.execute('INSERT INTO import_repairs VALUES (?,?,?,?,?)',(str(uuid.uuid4()),item_id,source,json.dumps(errors,ensure_ascii=False),datetime.now(timezone.utc).isoformat()))
        return errors
