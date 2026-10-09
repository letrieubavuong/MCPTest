from pathlib import Path
import json
import zipfile
import pytest
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.library import LibraryService


def test_metadata_revision_taxonomy_backup_restore(tmp_path):
    services=create_services(AppConfig.load(tmp_path/'app'));library=LibraryService(services)
    q=services.questions.create("source tiếng Việt")
    parent=library.add_taxonomy("Toán","subject")
    child=library.add_taxonomy("Đại số","chapter",parent)
    library.save_metadata(q.id,{'subject':'Toán','tags':['hàm số'],'taxonomy_id':child})
    assert services.questions.get(q.id).revision==2
    assert library.metadata(q.id)['tags']==['hàm số']
    assert len(library.taxonomy())==2
    assets=services.config.data_dir/'assets';assets.mkdir();(assets/'sample.png').write_bytes(b'original image')
    archive=library.backup(tmp_path/'backup.zip')
    services.questions.create('later')
    rollback=library.restore_backup(archive)
    assert rollback.is_file()
    assert services.questions.count()==1
    assert (assets/'sample.png').read_bytes()==b'original image'
    restored=library.restore_revision(q.id,1)
    assert restored.latex_source==q.latex_source
    assert restored.revision==4
    assert len(library.revisions(q.id))==4


def test_bad_backup_does_not_replace_library(tmp_path):
    services=create_services(AppConfig.load(tmp_path/'app'));library=LibraryService(services)
    services.questions.create('preserve')
    file=tmp_path/'bad.zip'
    with zipfile.ZipFile(file,'w') as z:z.writestr('manifest.json',json.dumps({'version':1,'files':{'../outside':'bad','studio.db':'bad'}}))
    with pytest.raises(ValueError):library.restore_backup(file)
    assert services.questions.count()==1
