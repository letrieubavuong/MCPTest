from dataclasses import dataclass
from typing import Literal

QuestionType = Literal["unknown", "mcq", "true_false", "short_answer", "essay"]

@dataclass(frozen=True)
class Question:
    id: str
    latex_source: str
    question_type: QuestionType
    solution: str
    difficulty_legacy: int | None
    cognitive_level: str | None
    revision: int


def validate_question(source: str, question_type: str, difficulty: int | None, cognitive: str | None) -> None:
    if not source.strip():
        raise ValueError("Question source is empty")
    if question_type not in ("unknown", "mcq", "true_false", "short_answer", "essay"):
        raise ValueError("Invalid question type")
    if difficulty is not None and (type(difficulty) is not int or difficulty not in range(5)):
        raise ValueError("Invalid legacy difficulty")
    if cognitive not in (None, "NB", "TH", "VD", "VDC"):
        raise ValueError("Invalid cognitive level")
