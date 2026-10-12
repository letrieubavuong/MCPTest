from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.assets import AssetStore
from latex_question_studio.application.library import LibraryService
from latex_question_studio.application.services import create_services


def test_asset_management_report_dry_run_and_safe_gc(tmp_path):
    services=create_services(AppConfig.load(tmp_path/'data'));store=AssetStore(services.config.data_dir)
    staged=store.stage_bytes(b'orphan', '.png', 'management');store.promote(staged)
    report=LibraryService(services).asset_report();assert report['asset_count']==0
    with services.database.transaction() as connection:
        connection.execute('INSERT INTO assets VALUES (?,?,?,?)',(staged['hash'],staged['hash'],staged['relative_path'],staged['bytes']))
    preview=LibraryService(services).asset_gc(dry_run=True);assert staged['relative_path'] in preview['removable']
    assert (services.config.data_dir/staged['relative_path']).exists()
    removed=LibraryService(services).asset_gc(dry_run=False);assert staged['relative_path'] in removed['removable']
    assert not (services.config.data_dir/staged['relative_path']).exists()


def test_asset_report_detects_corrupt_bytes(tmp_path):
    services=create_services(AppConfig.load(tmp_path/'data'));store=AssetStore(services.config.data_dir)
    staged=store.stage_bytes(b'original', '.png', 'corrupt');store.promote(staged)
    with services.database.transaction() as connection:
        connection.execute('INSERT INTO assets VALUES (?,?,?,?)',(staged['hash'],staged['hash'],staged['relative_path'],staged['bytes']))
    (services.config.data_dir/staged['relative_path']).write_bytes(b'changed')
    report=LibraryService(services).asset_report();assert report['corrupt']==1 and report['missing']==0


def test_gc_keeps_asset_referenced_by_exam_snapshot(tmp_path):
    services=create_services(AppConfig.load(tmp_path/'data'));store=AssetStore(services.config.data_dir)
    staged=store.stage_bytes(b'published', '.png', 'published');store.promote(staged)
    with services.database.transaction() as connection:
        connection.execute('INSERT INTO assets VALUES (?,?,?,?)',(staged['hash'],staged['hash'],staged['relative_path'],staged['bytes']))
        connection.execute('INSERT INTO exam_papers VALUES (?,?,?)',('paper','Published','now'))
        connection.execute('INSERT INTO exam_versions VALUES (?,?,?,?,?,?)',('version','paper',1,'{}',__import__('json').dumps({'assets':{'assets/'+staged['hash']+'.png':str(tmp_path)}}),'now'))
    report=LibraryService(services).asset_gc(dry_run=True);assert report['removable']==[]
