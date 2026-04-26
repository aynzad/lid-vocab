from dataclasses import dataclass
import json
import re
from typing import Any, Callable
from urllib.request import urlopen

from leben_vocab.corpus import Question


@dataclass(frozen=True)
class AnswerKey:
    question_id: str
    correct_option_id: str


@dataclass(frozen=True)
class StructuredAnswer:
    question_id: str
    correct_option_id: str
    question_text: str = ""


class AnswerMatchingError(ValueError):
    pass


class FixtureAnswerProvider:
    def __init__(self, answers: list[StructuredAnswer] | None = None) -> None:
        self._answers = answers or [
            StructuredAnswer(question_id="1", correct_option_id="a"),
            StructuredAnswer(question_id="BE-1", correct_option_id="a"),
        ]

    def load_answer_keys(self) -> list[StructuredAnswer]:
        return self._answers


class PinnedGitHubAnswerProvider:
    SOURCE_URL = (
        "https://raw.githubusercontent.com/leben-in-deutschland/"
        "leben-in-deutschland-app/"
        "b1832e7145080e0f70ebd680f24efc0933892e18/"
        "src/web/data/question.json"
    )

    def __init__(
        self,
        source_url: str = SOURCE_URL,
        fetch_json: Callable[[str], Any] | None = None,
    ) -> None:
        self.source_url = source_url
        self._fetch_json = fetch_json or _fetch_json

    def load_answer_keys(self) -> list[StructuredAnswer]:
        records = self._fetch_json(self.source_url)
        return [_structured_answer_from_record(record) for record in records]


def match_answer_keys(
    questions: list[Question], answers: list[StructuredAnswer]
) -> list[AnswerKey]:
    answers_by_id = {answer.question_id: answer for answer in answers}
    answers_by_text = {
        _normalize_question_text(answer.question_text): answer
        for answer in answers
        if answer.question_text
    }
    matches: list[AnswerKey] = []
    missing_question_ids: list[str] = []

    for question in questions:
        answer = answers_by_id.get(question.id)
        if answer is None:
            answer = answers_by_text.get(_normalize_question_text(question.text))
        if answer is None:
            missing_question_ids.append(question.id)
            continue
        _ensure_option_exists(question, answer.correct_option_id)
        matches.append(
            AnswerKey(
                question_id=question.id,
                correct_option_id=answer.correct_option_id,
            )
        )

    if missing_question_ids:
        raise AnswerMatchingError(
            "Unable to match correct answers; unmatched question ids: "
            + ", ".join(missing_question_ids)
        )

    return matches


def _ensure_option_exists(question: Question, option_id: str) -> None:
    if not any(option.id == option_id for option in question.options):
        raise AnswerMatchingError(
            f"Question {question.id} references missing correct option {option_id!r}"
        )


def _normalize_question_text(text: str) -> str:
    normalized = (
        text.lower()
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return " ".join(normalized.split())


def _fetch_json(url: str) -> Any:
    with urlopen(url, timeout=30) as response:
        return json.load(response)


def _structured_answer_from_record(record: dict[str, Any]) -> StructuredAnswer:
    question_id = str(
        record.get("num") or record.get("question_id") or record.get("id") or ""
    )
    correct_option_id = str(
        record.get("solution")
        or record.get("correct_option_id")
        or record.get("answer")
        or ""
    ).lower()
    question_text = str(record.get("question") or record.get("question_text") or "")
    if not question_id or correct_option_id not in {"a", "b", "c", "d"}:
        raise AnswerMatchingError(
            f"Structured answer record is missing a usable id or answer: {record!r}"
        )
    return StructuredAnswer(
        question_id=question_id,
        correct_option_id=correct_option_id,
        question_text=question_text,
    )
