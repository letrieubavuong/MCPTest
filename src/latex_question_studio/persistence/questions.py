from dataclasses import asdict
from datetime import datetime, timezone
import json
import uuid
from latex_question_studio.domain.question import Question, validate_question
from latex_question_studio.persistence.database import Database

class ConcurrentEditError(RuntimeError):
    pass

class QuestionRepository:
    def __init__(self, database: Database):
        self.database = database

    @staticmethod
    def _question(row) -> Question:
        return Question(**{key: row[key] for key in Question.__dataclass_fields__})

    @staticmethod
    def _snapshot(connection, question: Question, timestamp: str) -> None:
        data = asdict(question)
        if connection.execute("SELECT 1 FROM sqlite_master WHERE name='question_metadata'").fetchone():
            row = connection.execute("SELECT data_json FROM question_metadata WHERE question_id=?", (question.id,)).fetchone()
            data['metadata'] = json.loads(row[0]) if row else {}
        connection.execute(
            "INSERT INTO question_revisions VALUES (?,?,?,?)",
            (question.id, question.revision, json.dumps(data, ensure_ascii=False), timestamp),
        )

    def create(self, latex_source: str, question_type: str = "unknown", solution: str = "",
               difficulty_legacy: int | None = None, cognitive_level: str | None = None) -> Question:
        validate_question(latex_source, question_type, difficulty_legacy, cognitive_level)
        question = Question(str(uuid.uuid4()), latex_source, question_type, solution, difficulty_legacy, cognitive_level, 1)
        now = datetime.now(timezone.utc).isoformat()
        with self.database.transaction() as connection:
            connection.execute("INSERT INTO questions VALUES (?,?,?,?,?,?,?,?,?)", (
                question.id, latex_source, question_type, solution, difficulty_legacy, cognitive_level, 1, now, now,
            ))
            self._snapshot(connection, question, now)
        return question

    def get(self, question_id: str) -> Question | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM questions WHERE id=?", (question_id,)).fetchone()
            return self._question(row) if row else None

    def list_page(self, limit: int = 100, offset: int = 0) -> list[Question]:
        if not 1 <= limit <= 500 or offset < 0:
            raise ValueError("Invalid page bounds")
        with self.database.connect() as connection:
            return [self._question(row) for row in connection.execute(
                "SELECT * FROM questions ORDER BY created_at,id LIMIT ? OFFSET ?", (limit, offset))]

    def count(self) -> int:
        with self.database.connect() as connection:
            return connection.execute("SELECT count(*) FROM questions").fetchone()[0]

    def update(self, question: Question) -> Question:
        validate_question(question.latex_source, question.question_type, question.difficulty_legacy, question.cognitive_level)
        updated = Question(question.id, question.latex_source, question.question_type, question.solution,
                           question.difficulty_legacy, question.cognitive_level, question.revision + 1)
        now = datetime.now(timezone.utc).isoformat()
        with self.database.transaction() as connection:
            result = connection.execute(
                """UPDATE questions SET latex_source=?,question_type=?,solution=?,difficulty_legacy=?,
                   cognitive_level=?,revision=?,updated_at=? WHERE id=? AND revision=?""",
                (updated.latex_source, updated.question_type, updated.solution, updated.difficulty_legacy,
                 updated.cognitive_level, updated.revision, now, question.id, question.revision))
            if result.rowcount != 1:
                raise ConcurrentEditError("Question was changed or removed")
            self._snapshot(connection, updated, now)
        return updated

    def delete(self, question_id: str) -> bool:
        with self.database.transaction() as connection:
            return connection.execute("DELETE FROM questions WHERE id=?", (question_id,)).rowcount == 1
