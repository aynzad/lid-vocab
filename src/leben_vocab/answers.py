from dataclasses import dataclass
import difflib
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
    correct_answer_text: str = ""
    prefer_id: bool = True


class AnswerMatchingError(ValueError):
    pass


class FixtureAnswerProvider:
    def __init__(self, answers: list[StructuredAnswer] | None = None) -> None:
        self._answers = answers or [
            StructuredAnswer(question_id="1", correct_option_id="a"),
            StructuredAnswer(question_id="BE-1", correct_option_id="a"),
            StructuredAnswer(question_id="BY-1", correct_option_id="a"),
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
    answers_by_id = {
        answer.question_id: answer for answer in answers if answer.prefer_id
    }
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
            answer = _match_by_question_text(question, answers_by_text, answers)
        if answer is None:
            missing_question_ids.append(question.id)
            continue
        matches.append(
            AnswerKey(
                question_id=question.id,
                correct_option_id=_resolve_correct_option_id(question, answer),
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


def _match_by_question_text(
    question: Question,
    answers_by_text: dict[str, StructuredAnswer],
    answers: list[StructuredAnswer],
) -> StructuredAnswer | None:
    normalized_question = _normalize_question_text(question.text)
    exact = answers_by_text.get(normalized_question)
    if exact is not None:
        return exact

    scored_answers = sorted(
        (
            _score_answer_candidate(question, normalized_question, answer)
            for answer in answers
            if answer.question_text
        ),
        key=lambda item: item[0],
        reverse=True,
    )
    if not scored_answers:
        return None

    best_score, question_score, option_score, best_answer = scored_answers[0]
    second_score = scored_answers[1][0] if len(scored_answers) > 1 else 0.0
    if question_score >= 0.82 and best_score - second_score >= 0.03:
        return best_answer
    if question_score >= 0.65 and option_score >= 0.70:
        return best_answer
    return None


def _score_answer_candidate(
    question: Question, normalized_question: str, answer: StructuredAnswer
) -> tuple[float, float, float, StructuredAnswer]:
    question_score = _question_similarity(
        normalized_question,
        _normalize_question_text(answer.question_text),
    )
    option_score = _best_option_score(question, answer.correct_answer_text)
    return question_score + (0.2 * option_score), question_score, option_score, answer


def _best_option_score(question: Question, correct_answer_text: str) -> float:
    normalized_answer = _normalize_question_text(correct_answer_text)
    if not normalized_answer:
        return 0.0
    scores = [
        _question_similarity(normalized_answer, _normalize_question_text(option.text))
        for option in question.options
        if option.text
    ]
    return max(scores, default=0.0)


def _resolve_correct_option_id(question: Question, answer: StructuredAnswer) -> str:
    if answer.correct_answer_text:
        option_id = _match_correct_answer_text(question, answer.correct_answer_text)
        if option_id is not None:
            return option_id

    _ensure_option_exists(question, answer.correct_option_id)
    return answer.correct_option_id


def _match_correct_answer_text(
    question: Question, correct_answer_text: str
) -> str | None:
    normalized_answer = _normalize_question_text(correct_answer_text)
    if normalized_answer.startswith("bild "):
        return None

    scored_options = sorted(
        (
            (
                _question_similarity(
                    normalized_answer, _normalize_question_text(option.text)
                ),
                option.id,
            )
            for option in question.options
            if option.text
        ),
        key=lambda item: item[0],
        reverse=True,
    )
    if not scored_options:
        return None

    best_score, option_id = scored_options[0]
    if best_score >= 0.70:
        return option_id
    return None


def _question_similarity(left: str, right: str) -> float:
    plain = difflib.SequenceMatcher(None, left, right).ratio()
    sorted_left = " ".join(sorted(left.split()))
    sorted_right = " ".join(sorted(right.split()))
    sorted_ratio = difflib.SequenceMatcher(None, sorted_left, sorted_right).ratio()
    return max(plain, sorted_ratio)


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
    correct_answer_text = str(record.get(correct_option_id) or "")
    if not question_id or correct_option_id not in {"a", "b", "c", "d"}:
        raise AnswerMatchingError(
            f"Structured answer record is missing a usable id or answer: {record!r}"
        )
    return StructuredAnswer(
        question_id=question_id,
        correct_option_id=correct_option_id,
        question_text=question_text,
        correct_answer_text=correct_answer_text,
        prefer_id=False,
    )
