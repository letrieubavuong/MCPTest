from dataclasses import replace
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.search import SearchService
from latex_question_studio.application.library import LibraryService


def test_fts_unicode_filters_update_and_merge(tmp_path):
    s=create_services(AppConfig.load(tmp_path));search=SearchService(s);library=LibraryService(s)
    q=s.questions.create("Đạo hàm của hàm số x² = 2x")
    library.save_metadata(q.id,{'subject':'Toán','grade':'12','tags':['vi phân']})
    assert search.find('dao ham')[0].id==q.id
    assert search.find('vi phan',{'subject':'Toán','grade':'12','tag':'vi phân'})[0].id==q.id
    assert not search.find('dao',{'grade':'11'})
    q=s.questions.get(q.id);s.questions.update(replace(q,latex_source='Tích phân x dx'))
    assert not search.find('dao ham')
    assert search.find('tich phan')[0].id==q.id
    duplicate=s.questions.create('Tích phân x dx')
    suggestions=search.duplicates(q.id)
    assert suggestions[0]['exact']
    search.merge(q.id,duplicate.id)
    assert s.questions.get(duplicate.id).latex_source=='Tích phân x dx'
    assert len(search.find('tich phan'))==1
    with s.database.connect() as c:assert c.execute('SELECT count(*) FROM question_merges').fetchone()[0]==1
    assert search.fingerprint('x=1')!=search.fingerprint('x=2')
    assert search.fingerprint('\\True x')!=search.fingerprint('x')
