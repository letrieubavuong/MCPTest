from dataclasses import dataclass
from latex_question_studio.app.config import AppConfig
from latex_question_studio.persistence.database import Database
from latex_question_studio.persistence.questions import QuestionRepository

@dataclass(frozen=True)
class Services:
    config: AppConfig
    database: Database
    questions: QuestionRepository


def create_services(config: AppConfig) -> Services:
    database = Database(config.database_path)
    database.initialize()
    return Services(config, database, QuestionRepository(database))
