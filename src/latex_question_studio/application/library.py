from dataclasses import replace
from contextlib import closing
from pathlib import Path
import json
import sqlite3
import tempfile
import uuid
import zipfile
import hashlib
from latex_question_studio.persistence.database import Database, SCHEMA_VERSION

class LibraryService:
    def __init__(self, services): self.services = services

    def metadata(self, question_id):
        with self.services.database.connect() as c:
            row=c.execute("SELECT data_json FROM question_metadata WHERE question_id=?",(question_id,)).fetchone()
            return json.loads(row[0]) if row else {}

    def save_metadata(self, question_id, values, replace_existing=False):
        from latex_question_studio.persistence.questions import QuestionRepository
        from datetime import datetime,timezone
        with self.services.database.transaction() as c:
            qrow=c.execute("SELECT * FROM questions WHERE id=?",(question_id,)).fetchone()
            if not qrow:raise ValueError("Câu hỏi không tồn tại")
            from latex_question_studio.domain.question import validate_question
            current=dict(qrow)
            for key in ('question_type','difficulty_legacy','cognitive_level'):
                if key in values:current[key]=values[key] if values[key] is not None and values[key]!='' else (None if key!='question_type' else current[key])
            validate_question(current['latex_source'],current['question_type'],current['difficulty_legacy'],current['cognitive_level'])
            c.execute('UPDATE questions SET question_type=?,difficulty_legacy=?,cognitive_level=? WHERE id=?',(current['question_type'],current['difficulty_legacy'],current['cognitive_level'],question_id))
            row=c.execute("SELECT data_json FROM question_metadata WHERE question_id=?",(question_id,)).fetchone()
            data=json.loads(row[0]) if row else {}
            data = dict(values) if replace_existing else {**data, **values}
            c.execute("INSERT INTO question_metadata VALUES (?,?) ON CONFLICT(question_id) DO UPDATE SET data_json=excluded.data_json",(question_id,json.dumps(data,ensure_ascii=False)))
            c.execute("UPDATE questions SET revision=revision+1, updated_at=? WHERE id=?",(datetime.now(timezone.utc).isoformat(),question_id))
            q=QuestionRepository._question(c.execute("SELECT * FROM questions WHERE id=?",(question_id,)).fetchone())
            snapshot={**q.__dict__,"metadata":data}
            c.execute("INSERT INTO question_revisions VALUES (?,?,?,?)",(question_id,q.revision,json.dumps(snapshot,ensure_ascii=False),datetime.now(timezone.utc).isoformat()))
            c.execute("DELETE FROM question_taxonomy WHERE question_id=?",(question_id,))
            if data.get('taxonomy_id'):
                c.execute("INSERT INTO question_taxonomy VALUES (?,?)",(question_id,data['taxonomy_id']))

    def taxonomy(self):
        with self.services.database.connect() as c:
            return [dict(r) for r in c.execute("SELECT t.*,count(q.question_id) AS count FROM taxonomy_nodes t LEFT JOIN question_taxonomy q ON q.taxonomy_id=t.id GROUP BY t.id ORDER BY t.name")]

    def add_taxonomy(self, name, kind, parent_id=None):
        if not name.strip():raise ValueError("Tên phân loại không được rỗng")
        node=str(uuid.uuid4())
        with self.services.database.transaction() as c:
            c.execute("INSERT INTO taxonomy_nodes VALUES (?,?,?,?,?,?)",(node,parent_id,kind,name.strip(),None,None))
        return node

    def revisions(self, question_id):
        with self.services.database.connect() as c:
            return [dict(r) for r in c.execute("SELECT * FROM question_revisions WHERE question_id=? ORDER BY revision DESC",(question_id,))]

    def restore_revision(self, question_id, revision):
        q=self.services.questions.get(question_id)
        with self.services.database.connect() as c:
            row=c.execute("SELECT snapshot_json FROM question_revisions WHERE question_id=? AND revision=?",(question_id,revision)).fetchone()
        if not row:raise ValueError("Phiên bản không tồn tại")
        data=json.loads(row[0])
        result=self.services.questions.update(replace(q,latex_source=data['latex_source'],solution=data['solution'],question_type=data['question_type'],difficulty_legacy=data['difficulty_legacy'],cognitive_level=data['cognitive_level']))
        if 'metadata' in data:
            self.save_metadata(question_id,data['metadata'],replace_existing=True)
            result=self.services.questions.get(question_id)
        return result

    def backup(self, destination):
        destination=Path(destination)
        root=self.services.config.data_dir
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            db=self.services.database.backup(Path(temporary))
            manifest={}
            temp=destination.with_suffix(destination.suffix+'.tmp')
            with zipfile.ZipFile(temp,'w',zipfile.ZIP_DEFLATED) as archive:
                archive.write(db,'studio.db')
                manifest['studio.db']=hashlib.sha256(db.read_bytes()).hexdigest()
                for dirname in ('assets','sources','lesson_exports'):
                    for file in (root/dirname).rglob('*'):
                        if file.is_file():
                            name=file.relative_to(root).as_posix()
                            archive.write(file,name)
                            manifest[name]=hashlib.sha256(file.read_bytes()).hexdigest()
                archive.writestr('manifest.json',json.dumps({'version':1,'files':manifest}))
            temp.replace(destination)
        return destination

    def restore_backup(self, archive_path):
        root=self.services.config.data_dir
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            staging=Path(temporary)
            with zipfile.ZipFile(archive_path) as archive:
                entries=archive.infolist()
                if sum(e.file_size for e in entries)>2_000_000_000:raise ValueError("Backup quá lớn")
                manifest=json.loads(archive.read('manifest.json'))
                if manifest.get('version')!=1 or 'studio.db' not in manifest['files']:raise ValueError("Backup không hợp lệ")
                for name,digest in manifest['files'].items():
                    parts=Path(name).parts
                    if name!='studio.db' and (len(parts)<2 or parts[0] not in ('assets','sources','lesson_exports')):raise ValueError("Đường dẫn backup không hợp lệ")
                    if any(part in ('..','.') for part in parts) or Path(name).is_absolute():raise ValueError("Đường dẫn backup không an toàn")
                    raw=archive.read(name)
                    if hashlib.sha256(raw).hexdigest()!=digest:raise ValueError("Checksum backup không đúng")
                    target=staging/name
                    if not target.resolve().is_relative_to(staging.resolve()):raise ValueError('Đường dẫn backup không an toàn')
                    target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw)
            with closing(sqlite3.connect(staging/'studio.db')) as c:
                if c.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError("DB backup hỏng")
                version=c.execute('PRAGMA user_version').fetchone()[0]
                if not 1<=version<=SCHEMA_VERSION:raise ValueError("Schema backup không hỗ trợ")
                if c.execute('PRAGMA foreign_key_check').fetchall():raise ValueError("Backup sai liên kết")
            rollback=self.services.database.backup(root/'backups')
            for dirname in ('assets','sources','lesson_exports'):
                (root/dirname).mkdir(exist_ok=True)
                for file in (staging/dirname).rglob('*'):
                    if not file.is_file():continue
                    target=root/file.relative_to(staging);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(file.read_bytes())
            try:
                with closing(sqlite3.connect(staging/'studio.db')) as source:
                    with self.services.database.connect() as destination:source.backup(destination)
                self.services.database.initialize()
            except Exception:
                with closing(sqlite3.connect(rollback)) as source:
                    with self.services.database.connect() as destination:source.backup(destination)
                raise
        return rollback
