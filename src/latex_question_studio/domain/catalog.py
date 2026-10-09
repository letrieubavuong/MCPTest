"""Versioned curriculum registry. Legacy migration functions remain frozen."""
from functools import lru_cache
from pathlib import Path
import json

@lru_cache(maxsize=1)
def builtin_catalog():
    return json.loads((Path(__file__).parent/'data/curricula.json').read_text(encoding='utf-8'))

def validate_catalog(value):
    if value.get('schema_version')!=1:raise ValueError('Phiên bản danh mục không hỗ trợ')
    ids=set()
    for profile in value['profiles']:
        for key in ('root_id','subject','grade','book','version'):
            if not isinstance(profile.get(key),str) or not profile[key]:raise ValueError('Thiếu thông tin chương trình: '+key)
        lookup={n['id']:n for n in profile['nodes']}
        if len(lookup)!=len(profile['nodes']) or ids.intersection(lookup):raise ValueError('ID danh mục bị trùng')
        root=lookup.get(profile['root_id'])
        if not root or root['parent_id'] is not None:raise ValueError('Nút gốc chương trình không hợp lệ')
        for n in lookup.values():
            if n['kind'] not in ('subject','grade','chapter','lesson','topic') or not n['name'] or not isinstance(n['display_order'],int):raise ValueError('Nút chương trình không hợp lệ')
            visited=set();current=n
            while current['parent_id'] is not None:
                if current['id'] in visited or current['parent_id'] not in lookup:raise ValueError('Cây chương trình sai liên kết')
                visited.add(current['id']);current=lookup[current['parent_id']]
            if current['id']!=profile['root_id']:raise ValueError('Nút không thuộc chương trình')
        ids.update(lookup)
    return value

def install(connection,value):
    validate_catalog(value)
    for p in value['profiles']:
        existing=connection.execute('SELECT subject,grade,book,version FROM curriculum_profiles WHERE root_id=?',(p['root_id'],)).fetchone()
        if existing and tuple(existing)!=(p['subject'],p['grade'],p['book'],p['version']):raise ValueError('ID chương trình đã dùng; hãy tạo ID mới cho phiên bản khác')
        pending=list(p['nodes']);installed=set()
        while pending:
            for n in list(pending):
                if n['parent_id'] is not None and n['parent_id'] not in installed:continue
                previous=connection.execute('SELECT parent_id,kind FROM taxonomy_nodes WHERE id=?',(n['id'],)).fetchone()
                if previous and tuple(previous)!=(n['parent_id'],n['kind']):raise ValueError('Không được đổi liên kết ID danh mục đã dùng')
                connection.execute('INSERT OR IGNORE INTO taxonomy_nodes VALUES (?,?,?,?,?,?)',tuple(n.get(k) for k in ('id','parent_id','kind','name','code','description')))
                installed.add(n['id']);pending.remove(n)
        connection.execute('INSERT OR IGNORE INTO curriculum_profiles VALUES (?,?,?,?,?)',(p['root_id'],p['subject'],p['grade'],p['book'],p['version']))
        for n in p['nodes']:connection.execute('INSERT OR IGNORE INTO curriculum_order VALUES (?,?)',(n['id'],n['display_order']))

def migration_sql():
    def quote(v):return "'"+str(v).replace("'","''")+"'"
    statements=[]
    for p in builtin_catalog()['profiles']:
        statements.append('INSERT OR IGNORE INTO curriculum_profiles VALUES ('+','.join(quote(p[k]) for k in ('root_id','subject','grade','book','version'))+')')
        for n in p['nodes']:statements.append('INSERT OR IGNORE INTO curriculum_order VALUES ('+quote(n['id'])+','+str(n['display_order'])+')')
    return tuple(statements)
