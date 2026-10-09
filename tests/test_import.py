from pathlib import Path
import json
import sqlite3
import pytest
from latex_question_studio.parsing.latex import parse_questions, group
from latex_question_studio.app.config import AppConfig
from latex_question_studio.application.services import create_services
from latex_question_studio.application.importing import ImportService, ImportCancelled

SOURCE = r"""% \begin{ex} ignored
\begin{ex}%[1A1B1]
Nested $\frac{a}{b}$ and escaped \{x\}, percent \%.
\choice
{A {nested}}
{\True B}
{C}
{D}
\loigiai{Solution {with nesting} and \begin{listEX}\item x\end{listEX}}
\end{ex}
\begin{ex}
\choiceTFt{\True one}{two}{\True three}{four}
\end{ex}
\begin{vidu*}\shortans[oly]{1,25}\end{vidu*}
"""

def test_parser_round_trip_nested_comment_and_answers():
    items = parse_questions(SOURCE)
    assert len(items) == 3
    for q in items:
        assert q.source == SOURCE[q.start:q.end]
        assert not q.diagnostics
    assert items[0].question_type == 'mcq'
    assert items[0].answer['options'][1]['correct']
    assert 'with nesting' in items[0].solution
    assert items[1].question_type == 'true_false'
    assert items[2].answer['value'] == '1,25'


def test_malformed_retained_and_positioned():
    source = '\n\n' + r'\begin{ex} \choice{a}{b}'
    q = parse_questions(source)[0]
    assert q.source == source[2:]
    assert q.diagnostics[0].line == 3
    assert any('Unclosed' in d.message for d in q.diagnostics)
    assert parse_questions('no environment')[0].source == 'no environment'
    assert parse_questions(r'\begin{ex}{bad\end{ex}')[0].diagnostics


def test_import_stage_archive_commit_reopen_missing_asset(tmp_path):
    services = create_services(AppConfig.load(tmp_path / 'app'))
    importer = ImportService(services)
    file = tmp_path / 'nguồn có khoảng trắng.tex'
    raw = SOURCE.encode('utf-8')
    file.write_bytes(raw)
    image = tmp_path / 'image.png'
    image.write_bytes(b'asset fixture')
    assetfile = tmp_path / 'assets.tex'
    assetfile.write_text(r'\begin{ex}\includegraphics[width=2cm]{image.png}\end{ex}',encoding='utf-8')
    missing = tmp_path / 'missing.tex'
    missing.write_text(r'\begin{ex}\includegraphics{missing.png}\end{ex}',encoding='utf-8')
    batch, results = importer.stage([file,assetfile,missing])
    assert len(results) == 5
    assert sum(bool(r['errors']) for r in results) == 1
    assert importer.commit(batch) == 4
    assert importer.commit(batch) == 0
    assert file.read_bytes() == raw
    assert any(p.read_bytes() == raw for p in (services.config.data_dir/'sources').iterdir())
    assert services.questions.count() == 4
    assert len(importer.pending()) == 1
    reopened = create_services(AppConfig.load(services.config.data_dir))
    assert reopened.questions.count() == 4
    assert len(ImportService(reopened).pending()) == 1
    with services.database.connect() as connection:
        assert connection.execute('SELECT count(*) FROM question_assets').fetchone()[0] == 1


def test_cancel_no_batch_or_question(tmp_path):
    services = create_services(AppConfig.load(tmp_path/'app'))
    with pytest.raises(ImportCancelled):
        ImportService(services).stage([tmp_path/'does-not-exist.tex'],cancelled=lambda:True)
    with services.database.connect() as connection:
        assert connection.execute('SELECT count(*) FROM import_batches').fetchone()[0] == 0
    assert services.questions.count() == 0
