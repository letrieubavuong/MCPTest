from dataclasses import replace
import json
import sqlite3
import pytest
from latex_question_studio.persistence.database import Database, MIGRATIONS
from latex_question_studio.persistence.questions import QuestionRepository, ConcurrentEditError

@pytest.fixture
def database(tmp_path):
    db = Database(tmp_path / "data with spaces" / "studio.db")
    db.initialize()
    return db


def test_crud_reopen_and_exact_source(database):
    repo = QuestionRepository(database)
    source = "\\begin{ex}\n% tiếng Việt và dấu ngoặc { }\n2 + 2 = ?\n\\end{ex}\n"
    first = repo.create(source, "mcq", difficulty_legacy=4)
    assert first.cognitive_level is None
    reopened = Database(database.path)
    reopened.initialize()
    repo = QuestionRepository(reopened)
    assert repo.get(first.id).latex_source == source
    updated = repo.update(replace(first, solution="Lời giải", cognitive_level="VD"))
    assert updated.revision == 2
    assert repo.get(first.id) == updated
    with database.connect() as connection:
        rows = connection.execute("SELECT snapshot_json FROM question_revisions ORDER BY revision").fetchall()
        assert len(rows) == 2
        assert json.loads(rows[0][0])["latex_source"] == source
    with pytest.raises(ConcurrentEditError):
        repo.update(first)
    assert repo.count() == 1
    assert len(repo.list_page(limit=1)) == 1
    assert repo.delete(first.id)
    assert not repo.delete(first.id)
    assert repo.get(first.id) is None
    with database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM question_revisions").fetchone()[0] == 0


def test_revision_failure_rolls_back_entire_edit(database):
    repo = QuestionRepository(database)
    q = repo.create("original")
    with database.transaction() as connection:
        connection.execute("""CREATE TRIGGER fail_revision BEFORE INSERT ON question_revisions
                              BEGIN SELECT RAISE(ABORT, 'test failure'); END""")
    with pytest.raises(sqlite3.IntegrityError):
        repo.update(replace(q, latex_source="must roll back"))
    assert repo.get(q.id) == q


def test_foreign_keys_and_transaction_rollback(database):
    with pytest.raises(sqlite3.IntegrityError):
        with database.transaction() as connection:
            connection.execute("INSERT INTO taxonomy_nodes(id,kind,name) VALUES ('root','grade','12')")
            connection.execute("INSERT INTO taxonomy_nodes(id,parent_id,kind,name) VALUES ('bad','missing','lesson','X')")
    with database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM taxonomy_nodes").fetchone()[0] == 0
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_failed_migration_is_atomic_and_retryable(tmp_path, monkeypatch):
    db = Database(tmp_path / "studio.db")
    original = MIGRATIONS[1]
    monkeypatch.setitem(MIGRATIONS, 1, original + ("INVALID SQL",))
    with pytest.raises(sqlite3.OperationalError):
        db.initialize()
    with db.connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 0
        assert connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall() == []
    monkeypatch.setitem(MIGRATIONS, 1, original)
    db.initialize()
    assert QuestionRepository(db).count() == 0


def test_backup_can_be_reopened(database, tmp_path):
    repo = QuestionRepository(database)
    q = repo.create("backup source")
    backup = database.backup(tmp_path / "backup directory")
    repo.delete(q.id)
    restored = Database(backup)
    restored.initialize()
    assert QuestionRepository(restored).get(q.id) == q


def test_migration_preserves_existing_data_and_creates_backup(database, monkeypatch):
    import latex_question_studio.persistence.database as module
    q = QuestionRepository(database).create("retained source")
    current = module.SCHEMA_VERSION
    monkeypatch.setattr(module, "SCHEMA_VERSION", current + 1)
    monkeypatch.setitem(MIGRATIONS, current + 1, ("CREATE TABLE upgrade_marker(id INTEGER PRIMARY KEY)",))
    database.initialize()
    assert database.last_backup.is_file()
    assert QuestionRepository(database).get(q.id) == q
    with sqlite3.connect(database.last_backup) as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == current
    with database.connect() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == current + 1


def test_newer_and_unrecognized_database_untouched(tmp_path):
    for newer in (False, True):
        path = tmp_path / ("newer.db" if newer else "legacy.db")
        with sqlite3.connect(path) as connection:
            connection.execute("CREATE TABLE legacy(value TEXT)")
            connection.execute("INSERT INTO legacy VALUES ('preserve')")
            if newer:
                connection.execute("PRAGMA user_version=99")
        before = path.read_bytes()
        with pytest.raises(RuntimeError):
            Database(path).initialize()
        assert path.read_bytes() == before


@pytest.mark.parametrize("kwargs", [
    {"latex_source": " "}, {"latex_source": "x", "question_type": "bad"},
    {"latex_source": "x", "difficulty_legacy": 5},
    {"latex_source": "x", "cognitive_level": "made-up"},
])
def test_invalid_questions_do_not_write(database, kwargs):
    repo = QuestionRepository(database)
    with pytest.raises(ValueError):
        repo.create(**kwargs)
    assert repo.count() == 0
