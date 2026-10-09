"""SQLite connections and transaction-safe, versioned migrations.

Only opens the new application's database. Legacy databases are never opened here.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import uuid

from latex_question_studio.domain.curriculum import migration_sql, math_migration_sql

SCHEMA_VERSION = 9
MIGRATIONS = {
    1: (
        """CREATE TABLE taxonomy_nodes (
            id TEXT PRIMARY KEY, parent_id TEXT REFERENCES taxonomy_nodes(id),
            kind TEXT NOT NULL, name TEXT NOT NULL, code TEXT, legacy_level INTEGER)""",
        """CREATE TABLE questions (
            id TEXT PRIMARY KEY, latex_source TEXT NOT NULL CHECK(length(trim(latex_source)) > 0),
            question_type TEXT NOT NULL CHECK(question_type IN ('unknown','mcq','true_false','short_answer','essay')),
            solution TEXT NOT NULL DEFAULT '',
            difficulty_legacy INTEGER CHECK(difficulty_legacy BETWEEN 0 AND 4),
            cognitive_level TEXT CHECK(cognitive_level IN ('NB','TH','VD','VDC')),
            revision INTEGER NOT NULL CHECK(revision > 0),
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL)""",
        """CREATE TABLE question_revisions (
            question_id TEXT NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
            revision INTEGER NOT NULL, snapshot_json TEXT NOT NULL, created_at TEXT NOT NULL,
            PRIMARY KEY(question_id, revision))""",
        """CREATE TABLE question_taxonomy (
            question_id TEXT REFERENCES questions(id) ON DELETE CASCADE,
            taxonomy_id TEXT REFERENCES taxonomy_nodes(id),
            PRIMARY KEY(question_id, taxonomy_id))""",
        "CREATE INDEX ix_taxonomy_parent ON taxonomy_nodes(parent_id)",
        "CREATE INDEX ix_questions_type ON questions(question_type)",
    ),
    2: (
        "CREATE TABLE question_metadata(question_id TEXT PRIMARY KEY REFERENCES questions(id) ON DELETE CASCADE, data_json TEXT NOT NULL DEFAULT '{}')",
        "CREATE TABLE source_files(id TEXT PRIMARY KEY, original_path TEXT NOT NULL, encoding TEXT NOT NULL, archive_path TEXT NOT NULL, byte_hash TEXT NOT NULL)",
        "CREATE TABLE import_batches(id TEXT PRIMARY KEY, status TEXT NOT NULL, created_at TEXT NOT NULL)",
        "CREATE TABLE import_items(id TEXT PRIMARY KEY, batch_id TEXT REFERENCES import_batches(id), source_file_id TEXT REFERENCES source_files(id), start_offset INTEGER, end_offset INTEGER, raw_source TEXT NOT NULL, status TEXT NOT NULL, diagnostics_json TEXT NOT NULL, parsed_json TEXT NOT NULL, question_id TEXT REFERENCES questions(id) ON DELETE SET NULL)",
        "CREATE INDEX ix_import_batch ON import_items(batch_id)",
        "CREATE TABLE assets(id TEXT PRIMARY KEY, content_hash TEXT UNIQUE NOT NULL, relative_path TEXT NOT NULL, bytes INTEGER NOT NULL)",
        "CREATE TABLE question_assets(question_id TEXT REFERENCES questions(id) ON DELETE CASCADE, asset_id TEXT REFERENCES assets(id), original_reference TEXT NOT NULL, PRIMARY KEY(question_id, original_reference))",
    ),
    3: (
        "CREATE VIRTUAL TABLE questions_fts USING fts5(question_id UNINDEXED, source, metadata, tokenize='unicode61 remove_diacritics 2')",
        "INSERT INTO questions_fts SELECT q.id,replace(replace(q.latex_source,'đ','d'),'Đ','D'),coalesce(m.data_json,'') FROM questions q LEFT JOIN question_metadata m ON m.question_id=q.id",
        "CREATE TRIGGER questions_search_insert AFTER INSERT ON questions BEGIN INSERT INTO questions_fts VALUES (new.id,replace(replace(new.latex_source,'đ','d'),'Đ','D'),''); END",
        "CREATE TRIGGER questions_search_update AFTER UPDATE ON questions BEGIN DELETE FROM questions_fts WHERE question_id=old.id; INSERT INTO questions_fts SELECT new.id,replace(replace(new.latex_source,'đ','d'),'Đ','D'),coalesce((SELECT data_json FROM question_metadata WHERE question_id=new.id),''); END",
        "CREATE TRIGGER questions_search_delete AFTER DELETE ON questions BEGIN DELETE FROM questions_fts WHERE question_id=old.id; END",
        "CREATE TRIGGER metadata_search_insert AFTER INSERT ON question_metadata BEGIN UPDATE questions_fts SET metadata=replace(replace(new.data_json,'đ','d'),'Đ','D') WHERE question_id=new.question_id; END",
        "CREATE TRIGGER metadata_search_update AFTER UPDATE ON question_metadata BEGIN UPDATE questions_fts SET metadata=replace(replace(new.data_json,'đ','d'),'Đ','D') WHERE question_id=new.question_id; END",
        "CREATE TRIGGER metadata_search_delete AFTER DELETE ON question_metadata BEGIN UPDATE questions_fts SET metadata='' WHERE question_id=old.question_id; END",
        "CREATE TABLE question_merges(id TEXT PRIMARY KEY,primary_id TEXT REFERENCES questions(id),secondary_id TEXT REFERENCES questions(id),snapshot_json TEXT NOT NULL,created_at TEXT NOT NULL)",
    ),
    4: (
        "CREATE TABLE exam_papers(id TEXT PRIMARY KEY,title TEXT NOT NULL,created_at TEXT NOT NULL)",
        "CREATE TABLE exam_versions(id TEXT PRIMARY KEY,paper_id TEXT REFERENCES exam_papers(id),seed INTEGER NOT NULL,matrix_json TEXT NOT NULL,snapshot_json TEXT NOT NULL,created_at TEXT NOT NULL)",
        "CREATE TABLE exam_questions(version_id TEXT REFERENCES exam_versions(id),position INTEGER NOT NULL,question_id TEXT REFERENCES questions(id),revision INTEGER NOT NULL,permutation_json TEXT NOT NULL,answer_json TEXT NOT NULL,PRIMARY KEY(version_id,position),UNIQUE(version_id,question_id))",
    ),
    5: (
        "DROP TRIGGER questions_search_insert", "DROP TRIGGER questions_search_update", "DROP TRIGGER questions_search_delete",
        "DROP TRIGGER metadata_search_insert", "DROP TRIGGER metadata_search_update", "DROP TRIGGER metadata_search_delete",
        "DELETE FROM questions_fts",
        "INSERT INTO questions_fts(rowid,question_id,source,metadata) SELECT q.rowid,q.id,replace(replace(q.latex_source,'đ','d'),'Đ','D'),replace(replace(coalesce(m.data_json,''),'đ','d'),'Đ','D') FROM questions q LEFT JOIN question_metadata m ON m.question_id=q.id",
        "CREATE TRIGGER questions_search_insert AFTER INSERT ON questions BEGIN INSERT INTO questions_fts(rowid,question_id,source,metadata) VALUES (new.rowid,new.id,replace(replace(new.latex_source,'đ','d'),'Đ','D'),''); END",
        "CREATE TRIGGER questions_search_update AFTER UPDATE OF latex_source ON questions BEGIN DELETE FROM questions_fts WHERE rowid=old.rowid; INSERT INTO questions_fts(rowid,question_id,source,metadata) SELECT new.rowid,new.id,replace(replace(new.latex_source,'đ','d'),'Đ','D'),replace(replace(coalesce((SELECT data_json FROM question_metadata WHERE question_id=new.id),''),'đ','d'),'Đ','D'); END",
        "CREATE TRIGGER questions_search_delete AFTER DELETE ON questions BEGIN DELETE FROM questions_fts WHERE rowid=old.rowid; END",
        "CREATE TRIGGER metadata_search_insert AFTER INSERT ON question_metadata BEGIN UPDATE questions_fts SET metadata=replace(replace(new.data_json,'đ','d'),'Đ','D') WHERE rowid=(SELECT rowid FROM questions WHERE id=new.question_id); END",
        "CREATE TRIGGER metadata_search_update AFTER UPDATE ON question_metadata BEGIN UPDATE questions_fts SET metadata=replace(replace(new.data_json,'đ','d'),'Đ','D') WHERE rowid=(SELECT rowid FROM questions WHERE id=new.question_id); END",
        "CREATE TRIGGER metadata_search_delete AFTER DELETE ON question_metadata BEGIN UPDATE questions_fts SET metadata='' WHERE rowid=(SELECT rowid FROM questions WHERE id=old.question_id); END",
        "CREATE INDEX ix_questions_created ON questions(created_at,id)",
    ),
    6: (
        "ALTER TABLE import_items ADD COLUMN working_source TEXT",
        "CREATE TABLE import_repairs(id TEXT PRIMARY KEY,item_id TEXT REFERENCES import_items(id),source TEXT NOT NULL,diagnostics_json TEXT NOT NULL,created_at TEXT NOT NULL)",
    ),
    7: (
        "CREATE TABLE lessons(id TEXT PRIMARY KEY,title TEXT NOT NULL,revision INTEGER NOT NULL,document_json TEXT NOT NULL,updated_at TEXT NOT NULL)",
        "CREATE TABLE lesson_revisions(lesson_id TEXT REFERENCES lessons(id) ON DELETE CASCADE,revision INTEGER NOT NULL,document_json TEXT NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(lesson_id,revision))",
        "CREATE TABLE lesson_exports(id TEXT PRIMARY KEY,lesson_id TEXT REFERENCES lessons(id),revision INTEGER NOT NULL,audience TEXT NOT NULL,snapshot_json TEXT NOT NULL,relative_path TEXT NOT NULL,created_at TEXT NOT NULL)",
    ),
    8: migration_sql(),
    9: math_migration_sql(),
}

class Database:
    def __init__(self, path: Path):
        self.path = Path(path).resolve()
        self.last_backup: Path | None = None

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
        finally:
            connection.close()

    @contextmanager
    def transaction(self):
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            try:
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise RuntimeError("Database is newer than this application")
            if version == 0:
                tables = connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
                if tables:
                    raise RuntimeError("Unrecognized database; refusing to modify it")
            if version == SCHEMA_VERSION:
                return
        if self.path.stat().st_size > 0:
            self.last_backup = self.backup(self.path.parent / "backups")
        with self.transaction() as connection:
            # Re-read after acquiring the writer lock to avoid concurrent migrations.
            version = connection.execute("PRAGMA user_version").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise RuntimeError("Database is newer than this application")
            for target in range(version + 1, SCHEMA_VERSION + 1):
                for statement in MIGRATIONS[target]:
                    connection.execute(statement)
                connection.execute(f"PRAGMA user_version={target}")

    def backup(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        destination = directory / f"studio-{stamp}-{uuid.uuid4().hex[:8]}.db"
        with self.connect() as source:
            target = sqlite3.connect(destination)
            try:
                source.backup(target)
            finally:
                target.close()
        return destination
