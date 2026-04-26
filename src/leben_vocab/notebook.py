from __future__ import annotations

from dataclasses import dataclass
import difflib
import json
import re
from pathlib import Path
from typing import Any, Iterable

from leben_vocab.answers import PinnedGitHubAnswerProvider, StructuredAnswer
from leben_vocab.corpus import AnswerOption, Question
from leben_vocab.official_corpus import parse_official_questions, select_questions_for_state


NOTEBOOK_CATEGORIES = [
    "Constitution & Rights",
    "Government & Federalism",
    "Elections & Parties",
    "Law, Courts & Administration",
    "History, Memory & Reunification",
    "Europe & Foreign Relations",
    "Society, Family, Education & Work",
    "Symbols, Geography & State Facts",
]

REVIEWED_STATUS = "reviewed"
UNREVIEWED_STATUS = "unreviewed"


@dataclass(frozen=True)
class SeededAnswerRecord:
    question_id: str
    state: str | None
    question: str
    options: list[dict[str, Any]]
    seed_correct_option_id: str
    seed_correct_answer_text: str
    match_method: str
    match_confidence: float
    needs_review: bool
    review_status: str = UNREVIEWED_STATUS

    def to_dict(self) -> dict[str, Any]:
        return {
            "question_id": self.question_id,
            "state": self.state,
            "question": self.question,
            "options": self.options,
            "seed_correct_option_id": self.seed_correct_option_id,
            "seed_correct_answer_text": self.seed_correct_answer_text,
            "match_method": self.match_method,
            "match_confidence": self.match_confidence,
            "needs_review": self.needs_review,
            "review_status": self.review_status,
        }


class NotebookValidationError(ValueError):
    pass


def export_qa_seed(
    state: str,
    output_path: Path,
    review_md_path: Path,
    pdf_path: Path = Path("lid2026.pdf"),
    answer_provider: Any | None = None,
) -> list[SeededAnswerRecord]:
    questions = select_questions_for_state(parse_official_questions(pdf_path), state)
    answer_provider = answer_provider or PinnedGitHubAnswerProvider()
    records = seed_answer_records(questions, answer_provider.load_answer_keys())

    _write_json(output_path, [record.to_dict() for record in records])
    _write_text(review_md_path, render_answer_review_markdown(state, records))
    return records


def seed_answer_records(
    questions: list[Question], answers: list[StructuredAnswer]
) -> list[SeededAnswerRecord]:
    return [_seed_answer_record(question, answers) for question in questions]


def export_notebook_pack(
    state: str,
    answers_path: Path,
    output_path: Path,
    prompt_path: Path,
    pdf_path: Path = Path("lid2026.pdf"),
) -> None:
    questions = select_questions_for_state(parse_official_questions(pdf_path), state)
    records = _read_answer_records(answers_path)
    validated_records = validate_reviewed_answer_records(questions, records)

    _write_text(output_path, render_ai_pack_markdown(state, validated_records))
    _write_text(prompt_path, render_notebook_prompt(state, output_path))


def validate_reviewed_answer_records(
    questions: list[Question], records: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    errors: list[str] = []
    records_by_id: dict[str, dict[str, Any]] = {}
    duplicates: set[str] = set()

    for record in records:
        question_id = str(record.get("question_id") or "")
        if not question_id:
            errors.append("Found answer record without question_id")
            continue
        if question_id in records_by_id:
            duplicates.add(question_id)
            continue
        records_by_id[question_id] = record

    for duplicate in sorted(duplicates, key=_question_sort_key):
        errors.append(f"Duplicate answer record for {duplicate}")

    selected_ids = {question.id for question in questions}
    extra_ids = set(records_by_id) - selected_ids
    for extra_id in sorted(extra_ids, key=_question_sort_key):
        errors.append(f"Answer record {extra_id} is not selected for this state")

    for question in questions:
        record = records_by_id.get(question.id)
        if record is None:
            errors.append(f"Missing reviewed answer for {question.id}")
            continue

        if record.get("review_status") != REVIEWED_STATUS:
            errors.append(f"Answer record {question.id} is not reviewed")

        correct_option_id = str(record.get("seed_correct_option_id") or "")
        option = _option_by_id(question.options, correct_option_id)
        if option is None:
            errors.append(
                f"Answer record {question.id} references invalid option "
                f"{correct_option_id!r}"
            )
            continue

        expected_answer_text = _answer_text_for_option(option, record)
        if str(record.get("seed_correct_answer_text") or "") != expected_answer_text:
            record["seed_correct_answer_text"] = expected_answer_text
        record["state"] = question.state
        record["question"] = question.text
        record["options"] = _serialized_options(question.options)

    if errors:
        raise NotebookValidationError("; ".join(errors))

    return [
        records_by_id[question.id]
        for question in sorted(questions, key=lambda item: _question_sort_key(item.id))
    ]


def render_ai_pack_markdown(state: str, records: list[dict[str, Any]]) -> str:
    lines = [
        f"# Leben in Deutschland AI Notebook Pack: {state}",
        "",
        "Use this verified Q&A data to create a compact knowledge-base notebook.",
        "Only `review_status: reviewed` records should appear in this pack.",
        "",
        "## Notebook Categories",
        "",
    ]
    lines.extend(f"- {category}" for category in NOTEBOOK_CATEGORIES)
    lines.extend(
        [
            "",
            "## Verified Q&A",
            "",
        ]
    )

    for record in records:
        lines.extend(
            [
                f"### Q{record['question_id']}",
                "",
                f"Question: {record['question']}",
                "",
                "Options:",
            ]
        )
        for option in record["options"]:
            image_note = " [image-only]" if option.get("is_image_only") else ""
            lines.append(f"- {option['id']}: {option['text']}{image_note}".rstrip())
        lines.extend(
            [
                "",
                f"Correct: {record['seed_correct_option_id']} - "
                f"{record['seed_correct_answer_text']}",
                f"Citation: Q{record['question_id']}: "
                f"{record['seed_correct_answer_text']}",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def render_notebook_prompt(state: str, ai_pack_path: Path) -> str:
    categories = "\n".join(f"- {category}" for category in NOTEBOOK_CATEGORIES)
    return f"""# Prompt: Compact LiD Knowledge-Base Notebook

Create a Markdown-only, print-ready compact knowledge-base notebook for the Leben in Deutschland test for {state}.

Use the verified Q&A pack at `{ai_pack_path}` as the only source of test facts. Do not add uncited facts.

Rules:
- Write the note body in English.
- Preserve exact German terms, names, laws, dates, numbers, and correct answer text when useful.
- Use moderate filtering: keep Germany-specific exam knowledge, especially numbers, dates, ages, thresholds, named people, places, laws, institutions, parties, courts, symbols, historical events, state facts, and non-obvious legal/social rules.
- Drop noisy common-sense items unless they contain a Germany-specific term or likely exam trap.
- Merge repeated facts into one note and list all supporting citations.
- Add a global category index near the top.
- In the global category index, every category must be a Markdown link that correctly jumps to that category header in the same file.
- Do not add category-level note indexes.
- Use Markdown ordered lists for notes, with every note marker written as `1.` so Markdown auto-numbers them.
- Each note must use this exact shape, including blank lines, four-space indentation, and blockquote metadata:
  `1. Fact in one compact sentence.`

  `    > Keywords: keyword, keyword`

  `    > Questions: 152,155`
- Every note must include at least one supporting question number in `Questions:`.
- Question references must come from pack citations; strip the leading `Q` for normal IDs (`Q152` -> `152`) and keep state IDs without the leading `Q` (`QBE-1` -> `BE-1`).
- Use the exact German correct answer text from the pack to verify each note's source facts, but do not print full citations unless the German term or answer text is useful in the note body.
- Keep the notebook compact and optimized for memorization.

Use these categories:
{categories}

Output only the finished Markdown notebook.
"""


def render_answer_review_markdown(
    state: str, records: Iterable[SeededAnswerRecord]
) -> str:
    records = list(records)
    needs_review_count = sum(record.needs_review for record in records)
    lines = [
        f"# Answer Review: {state}",
        "",
        f"- Total selected questions: {len(records)}",
        f"- Records flagged for review: {needs_review_count}",
        "",
        "Set `review_status` to `reviewed` in the JSON only after checking the answer.",
        "",
    ]

    for record in records:
        marker = "REVIEW" if record.needs_review else "CHECK"
        lines.extend(
            [
                f"## {marker} Q{record.question_id}",
                "",
                f"Question: {record.question}",
                "",
                "Options:",
            ]
        )
        for option in record.options:
            image_note = " [image-only]" if option["is_image_only"] else ""
            lines.append(f"- {option['id']}: {option['text']}{image_note}".rstrip())
        lines.extend(
            [
                "",
                f"Seed answer: {record.seed_correct_option_id} - "
                f"{record.seed_correct_answer_text}",
                f"Match: {record.match_method}, confidence "
                f"{record.match_confidence:.3f}",
                f"Review status: {record.review_status}",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def _seed_answer_record(
    question: Question, answers: list[StructuredAnswer]
) -> SeededAnswerRecord:
    exact_id_answer = next(
        (
            answer
            for answer in answers
            if answer.prefer_id and answer.question_id == question.id
        ),
        None,
    )
    if exact_id_answer is not None:
        question_score = _question_similarity(
            _normalize_text(question.text), _normalize_text(exact_id_answer.question_text)
        )
        return _record_from_answer(
            question=question,
            answer=exact_id_answer,
            match_method="id",
            match_confidence=1.0 if not exact_id_answer.question_text else question_score,
            needs_review=bool(exact_id_answer.question_text and question_score < 0.90),
        )

    candidates = sorted(
        (
            _score_answer_candidate(question, answer)
            for answer in answers
            if answer.question_text
        ),
        key=lambda item: item[0],
        reverse=True,
    )
    if not candidates:
        return _empty_record(question, "none", 0.0)

    best_score, question_score, option_score, best_answer = candidates[0]
    second_score = candidates[1][0] if len(candidates) > 1 else 0.0
    match_method = "exact-text" if question_score == 1.0 else "fuzzy-text"
    confidence = round(max(question_score, best_score / 1.2), 3)
    needs_review = (
        question_score < 0.82
        or best_score - second_score < 0.03
        or (
            best_answer.correct_answer_text
            and not _is_image_answer(best_answer.correct_answer_text)
            and option_score < 0.70
        )
    )

    if needs_review and question_score < 0.65:
        return _empty_record(question, match_method, confidence)

    return _record_from_answer(
        question=question,
        answer=best_answer,
        match_method=match_method,
        match_confidence=confidence,
        needs_review=needs_review,
    )


def _record_from_answer(
    question: Question,
    answer: StructuredAnswer,
    match_method: str,
    match_confidence: float,
    needs_review: bool,
) -> SeededAnswerRecord:
    option = _resolve_seed_option(question, answer)
    correct_answer_text = ""
    correct_option_id = option.id if option is not None else ""
    if option is not None:
        correct_answer_text = _answer_text_for_option(
            option,
            {
                "question_id": question.id,
                "seed_correct_answer_text": answer.correct_answer_text,
            },
        )
    elif answer.correct_answer_text:
        correct_answer_text = answer.correct_answer_text
        needs_review = True

    return SeededAnswerRecord(
        question_id=question.id,
        state=question.state,
        question=question.text,
        options=_serialized_options(question.options),
        seed_correct_option_id=correct_option_id,
        seed_correct_answer_text=correct_answer_text,
        match_method=match_method,
        match_confidence=round(match_confidence, 3),
        needs_review=needs_review or option is None,
    )


def _resolve_seed_option(
    question: Question, answer: StructuredAnswer
) -> AnswerOption | None:
    if answer.correct_answer_text and not _is_image_answer(answer.correct_answer_text):
        scored_options = sorted(
            (
                (
                    _question_similarity(
                        _normalize_text(answer.correct_answer_text),
                        _normalize_text(option.text),
                    ),
                    option,
                )
                for option in question.options
                if option.text
            ),
            key=lambda item: item[0],
            reverse=True,
        )
        if scored_options and scored_options[0][0] >= 0.70:
            return scored_options[0][1]
    return _option_by_id(question.options, answer.correct_option_id)


def _empty_record(
    question: Question, match_method: str, match_confidence: float
) -> SeededAnswerRecord:
    return SeededAnswerRecord(
        question_id=question.id,
        state=question.state,
        question=question.text,
        options=_serialized_options(question.options),
        seed_correct_option_id="",
        seed_correct_answer_text="",
        match_method=match_method,
        match_confidence=round(match_confidence, 3),
        needs_review=True,
    )


def _score_answer_candidate(
    question: Question, answer: StructuredAnswer
) -> tuple[float, float, float, StructuredAnswer]:
    question_score = _question_similarity(
        _normalize_text(question.text), _normalize_text(answer.question_text)
    )
    option_score = _best_option_score(question.options, answer.correct_answer_text)
    return question_score + (0.2 * option_score), question_score, option_score, answer


def _best_option_score(
    options: tuple[AnswerOption, ...], correct_answer_text: str
) -> float:
    if _is_image_answer(correct_answer_text):
        return 1.0
    normalized_answer = _normalize_text(correct_answer_text)
    if not normalized_answer:
        return 0.0
    return max(
        (
            _question_similarity(normalized_answer, _normalize_text(option.text))
            for option in options
            if option.text
        ),
        default=0.0,
    )


def _answer_text_for_option(option: AnswerOption, record: dict[str, Any]) -> str:
    if option.text:
        return option.text
    existing_answer_text = str(record.get("seed_correct_answer_text") or "")
    if existing_answer_text:
        return existing_answer_text
    return f"Bild {str(record.get('seed_correct_option_id') or option.id).upper()}"


def _serialized_options(options: tuple[AnswerOption, ...]) -> list[dict[str, Any]]:
    return [
        {"id": option.id, "text": option.text, "is_image_only": option.is_image_only}
        for option in options
    ]


def _option_by_id(
    options: tuple[AnswerOption, ...], option_id: str
) -> AnswerOption | None:
    return next((option for option in options if option.id == option_id), None)


def _normalize_text(text: str) -> str:
    normalized = (
        text.lower()
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return " ".join(normalized.split())


def _question_similarity(left: str, right: str) -> float:
    plain = difflib.SequenceMatcher(None, left, right).ratio()
    sorted_left = " ".join(sorted(left.split()))
    sorted_right = " ".join(sorted(right.split()))
    sorted_ratio = difflib.SequenceMatcher(None, sorted_left, sorted_right).ratio()
    return max(plain, sorted_ratio)


def _is_image_answer(answer_text: str) -> bool:
    return _normalize_text(answer_text).startswith("bild ")


def _question_sort_key(question_id: str) -> tuple[int, str, int]:
    if question_id.isdigit():
        return (0, "", int(question_id))
    prefix, _, number = question_id.partition("-")
    return (1, prefix, int(number) if number.isdigit() else 0)


def _read_answer_records(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as answer_file:
        data = json.load(answer_file)
    if not isinstance(data, list):
        raise NotebookValidationError("Reviewed answer file must contain a JSON list")
    return data


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
