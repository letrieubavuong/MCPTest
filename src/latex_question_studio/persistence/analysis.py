"""Disposable structural validation cache; never replaces authoritative source/revisions."""
from dataclasses import asdict
import hashlib,json
from latex_question_studio.parsing.latex import parse_questions,normalized_source,ParsedQuestion,Diagnostic
PARSER_VERSION=3

def record(connection,qid,source,items=None):
    items=parse_questions(source) if items is None else items
    valid=len(items)==1 and not items[0].diagnostics
    values=(qid,hashlib.sha256(source.encode()).hexdigest(),hashlib.sha256(normalized_source(source).encode()).hexdigest(),PARSER_VERSION,int(valid),json.dumps([asdict(item) for item in items],ensure_ascii=False))
    connection.execute('INSERT INTO question_analysis VALUES (?,?,?,?,?,?) ON CONFLICT(question_id) DO UPDATE SET source_hash=excluded.source_hash,normalized_hash=excluded.normalized_hash,parser_version=excluded.parser_version,valid=excluded.valid,parsed_json=excluded.parsed_json',values)
    return items

def ensure(database,join='',where=None,parameters=None,cancelled=lambda:False):
    where=list(where or []);parameters=list(parameters or [])
    if cancelled():raise InterruptedError('Đã hủy phân tích nguồn câu hỏi')
    # Snapshot IDs once; repeatedly scanning the scope for LIMIT 256 is quadratic.
    # Sources remain bounded to one batch and are read under the writer lock.
    sql='SELECT q.id FROM questions q LEFT JOIN question_metadata m ON m.question_id=q.id LEFT JOIN question_analysis a ON a.question_id=q.id'+join+' WHERE '+' AND '.join(where+['(a.question_id IS NULL OR a.parser_version<>?)'])
    with database.connect() as c:ids=[row[0] for row in c.execute(sql,parameters+[PARSER_VERSION])]
    for start in range(0,len(ids),256):
        if cancelled():raise InterruptedError('Đã hủy phân tích nguồn câu hỏi')
        chunk=ids[start:start+256]
        with database.transaction() as c:
            rows=c.execute('SELECT q.id,q.latex_source FROM questions q LEFT JOIN question_analysis a ON a.question_id=q.id WHERE q.id IN ('+','.join('?' for _ in chunk)+') AND (a.question_id IS NULL OR a.parser_version<>?)',chunk+[PARSER_VERSION]).fetchall()
            for row in rows:
                if cancelled():raise InterruptedError('Đã hủy phân tích nguồn câu hỏi')
                record(c,row['id'],row['latex_source'])


def parsed(database,qid,expected_source=None):
    with database.transaction() as c:
        q=c.execute('SELECT latex_source FROM questions WHERE id=?',(qid,)).fetchone()
        if not q:raise ValueError('Câu hỏi đã bị xóa')
        if expected_source is not None and q[0]!=expected_source:
            # An edit raced the caller's pinned revision. Never mix new answers
            # with old source or overwrite the current validation cache.
            return parse_questions(expected_source)
        row=c.execute('SELECT * FROM question_analysis WHERE question_id=?',(qid,)).fetchone()
        if not row or row['parser_version']!=PARSER_VERSION:return record(c,qid,q[0])
        items=[]
        for values in json.loads(row['parsed_json']):
            values['diagnostics']=[Diagnostic(**d) for d in values['diagnostics']];items.append(ParsedQuestion(**values))
        return items
