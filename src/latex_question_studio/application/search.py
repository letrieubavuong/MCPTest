from difflib import SequenceMatcher
from datetime import datetime,timezone
import hashlib
import json
import re
import unicodedata
import uuid
from latex_question_studio.persistence.questions import QuestionRepository

class SearchService:
    def __init__(self,services):self.services=services

    def find(self,text='',filters=None,limit=100,offset=0,taxonomy_id=None,count_only=False):
        if not 1<=limit<=500 or offset<0:raise ValueError('Invalid page bounds')
        join,where,parameters=self.query_parts(text,filters,taxonomy_id)
        if join is None:return 0 if count_only else []
        order='bm25(questions_fts),q.id' if join else 'q.created_at,q.id'
        if count_only:
            sql='SELECT count(*) FROM questions q LEFT JOIN question_metadata m ON m.question_id=q.id'+join+' WHERE '+' AND '.join(where)
            with self.services.database.connect() as c:return c.execute(sql,parameters).fetchone()[0]
        sql='SELECT q.* FROM questions q LEFT JOIN question_metadata m ON m.question_id=q.id'+join+' WHERE '+' AND '.join(where)+' ORDER BY '+order+' LIMIT ? OFFSET ?'
        with self.services.database.connect() as c:return [QuestionRepository._question(r) for r in c.execute(sql,parameters+[limit,offset])]

    def query_parts(self,text='',filters=None,taxonomy_id=None):
        filters=filters or {};parameters=[];where=["coalesce(json_extract(m.data_json,'$.archived'),0)=0"]
        join=''
        if text.strip():
            tokens=re.findall(r"[^\W_]+",text.lower().replace('đ','d'),re.UNICODE)
            if not tokens:return None,[],[]
            query=' AND '.join('"'+token+'"*' for token in tokens)
            join=' JOIN questions_fts f ON f.question_id=q.id'
            where.append('questions_fts MATCH ?');parameters.append(query)
        for field,value in filters.items():
            if not value:continue
            if field in ('question_type','cognitive_level','difficulty_legacy'):
                where.append('q.'+field+'=?');parameters.append(value)
            elif field in ('subject','grade','chapter','lesson','topic','source'):
                where.append("json_extract(m.data_json,'$."+field+"')=?");parameters.append(value)
            elif field=='tag':
                where.append("EXISTS(SELECT 1 FROM json_each(json_extract(m.data_json,'$.tags')) WHERE value=?)");parameters.append(value)
        if taxonomy_id:
            where.append("q.id IN (WITH RECURSIVE subtree(id) AS (SELECT ? UNION SELECT t.id FROM taxonomy_nodes t JOIN subtree s ON t.parent_id=s.id) SELECT question_id FROM question_taxonomy WHERE taxonomy_id IN (SELECT id FROM subtree))");parameters.append(taxonomy_id)
        return join,where,parameters

    @staticmethod
    def fingerprint(source):
        # Conservative normalization: never remove numbers, answers, math or meaningful spaces.
        return hashlib.sha256(source.replace('\r\n','\n').encode('utf-8')).hexdigest()

    def duplicates(self,question_id,threshold=.75,limit=100,cancelled=lambda:False):
        q=self.services.questions.get(question_id)
        if not q:return []
        results=[];fingerprint=self.fingerprint(q.latex_source)
        with self.services.database.connect() as c:
            for row in c.execute("SELECT q.id,q.latex_source FROM questions q LEFT JOIN question_metadata m ON q.id=m.question_id WHERE q.id<>? AND coalesce(json_extract(m.data_json,'$.archived'),0)=0",(question_id,)):
                if cancelled():break
                exact=self.fingerprint(row['latex_source'])==fingerprint
                if exact:score=1.0
                elif abs(len(row['latex_source'])-len(q.latex_source))>max(len(q.latex_source),1)*.5:continue
                else:
                    matcher=SequenceMatcher(None,q.latex_source,row['latex_source'],autojunk=False)
                    # These upper bounds cannot exclude a result accepted by ratio().
                    if matcher.real_quick_ratio()<threshold:continue
                    if threshold>0.9 and matcher.quick_ratio()<threshold:continue
                    score=matcher.ratio()
                if score>=threshold:results.append({'id':row['id'],'source':row['latex_source'],'score':score,'exact':exact})
        return sorted(results,key=lambda r:(not r['exact'],-r['score']))[:limit]

    def merge(self,primary_id,secondary_id):
        if primary_id==secondary_id:raise ValueError('Cannot merge same question')
        now=datetime.now(timezone.utc).isoformat()
        with self.services.database.transaction() as c:
            rows=c.execute('SELECT * FROM questions WHERE id IN (?,?)',(primary_id,secondary_id)).fetchall()
            if len(rows)!=2:raise ValueError('Missing question')
            snapshot={'questions':[dict(r) for r in rows],'metadata':[dict(r) for r in c.execute('SELECT * FROM question_metadata WHERE question_id IN (?,?)',(primary_id,secondary_id))]}
            c.execute('INSERT INTO question_merges VALUES (?,?,?,?,?)',(str(uuid.uuid4()),primary_id,secondary_id,json.dumps(snapshot,ensure_ascii=False),now))
            row=c.execute('SELECT data_json FROM question_metadata WHERE question_id=?',(secondary_id,)).fetchone()
            data=json.loads(row[0]) if row else {};data.update({'archived':True,'merged_into':primary_id})
            c.execute('INSERT INTO question_metadata VALUES (?,?) ON CONFLICT(question_id) DO UPDATE SET data_json=excluded.data_json',(secondary_id,json.dumps(data,ensure_ascii=False)))
            c.execute('UPDATE questions SET revision=revision+1,updated_at=? WHERE id=?',(now,secondary_id))
            q=QuestionRepository._question(c.execute('SELECT * FROM questions WHERE id=?',(secondary_id,)).fetchone());QuestionRepository._snapshot(c,q,now)
        # The secondary source, answers/assets/revisions remain retrievable by ID.
