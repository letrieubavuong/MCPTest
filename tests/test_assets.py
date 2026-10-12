from pathlib import Path
import json
import shutil

import pytest

from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.assets import AssetResolver
from latex_question_studio.application.importing import ImportService
from latex_question_studio.application.services import create_services


def write_png(path, color):
    from PySide6.QtGui import QImage, QColor
    image = QImage(10, 10, QImage.Format.Format_RGB32)
    image.fill(QColor(color))
    assert image.save(str(path))


def test_resolver_graphicspath_nested_input_and_cycle(tmp_path):
    (tmp_path / 'images').mkdir()
    (tmp_path / 'figures').mkdir()
    write_png(tmp_path / 'images' / 'same.png', 'red')
    write_png(tmp_path / 'figures' / 'same.jpg', 'blue')
    (tmp_path / 'nested.tex').write_text(r'\includegraphics{same}' + '\n' + r'\input{cycle}', encoding='utf-8')
    (tmp_path / 'cycle.tex').write_text(r'\input{nested}', encoding='utf-8')
    source = r'\graphicspath{{images/}{figures/}}' + '\n' + r'\includegraphics{same}' + '\n' + r'\input{nested}'
    graph = AssetResolver().resolve(source, tmp_path / 'main.tex')
    statuses = [entry.resolution_status for entry in graph.references]
    assert 'AMBIGUOUS_ASSET' in statuses
    assert 'CYCLE' in statuses
    assert any(entry.dependency_type == 'source' and entry.resolution_status == 'RESOLVED' for entry in graph.references)
    assert not graph.ready


def test_resolver_rejects_traversal_dynamic_and_unsupported(tmp_path):
    write_png(tmp_path / 'ok.png', 'red')
    source = '\n'.join((r'\includegraphics{../outside.png}', r'\includegraphics{dynamic\name}', r'\includegraphics{ok.svg}'))
    graph = AssetResolver().resolve(source, tmp_path / 'main.tex')
    assert [entry.resolution_status for entry in graph.references] == ['BLOCKED_PATH', 'NEEDS_REVIEW', 'UNSUPPORTED_FORMAT']


def test_import_stages_content_addressed_asset_after_source_move(tmp_path):
    services = create_services(AppConfig.load(tmp_path / 'data'))
    project = tmp_path / 'project'
    project.mkdir()
    write_png(project / 'answer.png', 'green')
    source_path = project / 'questions.tex'
    source_path.write_text(r'\begin{ex}A\includegraphics{answer.png}\end{ex}', encoding='utf-8')
    batch, rows = ImportService(services).stage([source_path])
    assert rows[0]['errors'] == []
    assert rows[0]['parsed']['assets'][0]['resolution_status'] == 'RESOLVED'
    assert rows[0]['parsed']['assets'][0]['source_context'] == str(project.resolve())
    assert ImportService(services).commit(batch) == 1
    shutil.rmtree(project)
    with services.database.connect() as connection:
        row = connection.execute('SELECT qa.original_reference,qa.source_context,qa.resolution_status,a.relative_path FROM question_assets qa JOIN assets a ON a.id=qa.asset_id').fetchone()
        assert row['original_reference'] == 'answer.png' and row['resolution_status'] == 'RESOLVED'
        assert Path(services.config.data_dir / row['relative_path']).is_file()


def test_import_does_not_mark_ambiguous_or_missing_ready(tmp_path):
    services = create_services(AppConfig.load(tmp_path / 'data'))
    project = tmp_path / 'project'
    project.mkdir()
    write_png(project / 'same.png', 'red')
    write_png(project / 'same.jpg', 'blue')
    source_path = project / 'questions.tex'
    source_path.write_text(r'\graphicspath{{./}}\begin{ex}A\includegraphics{same}\end{ex}', encoding='utf-8')
    batch, rows = ImportService(services).stage([source_path])
    assert rows[0]['errors'] and 'AMBIGUOUS_ASSET' in rows[0]['errors'][0]['message']
    assert ImportService(services).commit(batch) == 0
    with services.database.connect() as connection:
        assert connection.execute('SELECT count(*) FROM questions').fetchone()[0] == 0


def test_asset_store_stages_atomic_promotes_verifies_and_reports_gc(tmp_path):
    from latex_question_studio.application.assets import AssetStore
    from latex_question_studio.persistence.database import Database
    store = AssetStore(tmp_path)
    staged = store.stage_bytes(b'one image', '.png', 'batch-1')
    assert not (tmp_path / staged['relative_path']).exists()
    store.promote(staged)
    assert store.verify(staged['relative_path'], staged['hash'])['ok']
    db = Database(tmp_path / 'studio.db');db.initialize()
    with db.transaction() as connection:
        connection.execute('INSERT INTO assets VALUES (?,?,?,?)',(staged['hash'],staged['hash'],staged['relative_path'],staged['bytes']))
        report = store.garbage_collect(connection, dry_run=True)
        assert report['unlinked'] == 1 and report['removable']
        store.garbage_collect(connection, dry_run=False)
    assert not (tmp_path / staged['relative_path']).exists()
    store.cleanup_batch('batch-1')
