import re
from pathlib import Path

import pymupdf

from leben_vocab.corpus import AnswerOption, Question

STATE_CODES = {
    "Baden-Württemberg": "BW",
    "Bayern": "BY",
    "Berlin": "BE",
    "Brandenburg": "BB",
    "Bremen": "HB",
    "Hamburg": "HH",
    "Hessen": "HE",
    "Mecklenburg-Vorpommern": "MV",
    "Niedersachsen": "NI",
    "Nordrhein-Westfalen": "NW",
    "Rheinland-Pfalz": "RP",
    "Saarland": "SL",
    "Sachsen": "SN",
    "Sachsen-Anhalt": "ST",
    "Schleswig-Holstein": "SH",
    "Thüringen": "TH",
}

_TASK_RE = re.compile(r"^Aufgabe\s+(\d+)$")
_PAGE_HEADER_RE = re.compile(r"^Seite\s+\d+\s+von\s+\d+$")
_OPTION_MARKERS = ("", "□")


def parse_official_questions(pdf_path: Path) -> list[Question]:
    document = pymupdf.open(pdf_path)
    questions: list[Question] = []
    current_state: str | None = None
    current_number: int | None = None
    current_lines: list[str] = []

    for page in document:
        for raw_line in page.get_text("text").splitlines():
            line = raw_line.strip()
            if not line or _is_ignored_line(line):
                continue

            detected_state = _detect_state_heading(line)
            if detected_state is not None:
                if current_number is not None:
                    questions.append(
                        _build_question(current_number, current_state, current_lines)
                    )
                    current_number = None
                    current_lines = []
                current_state = detected_state
                continue

            task_match = _TASK_RE.match(line)
            if task_match:
                if current_number is not None:
                    questions.append(
                        _build_question(current_number, current_state, current_lines)
                    )
                current_number = int(task_match.group(1))
                current_lines = []
                continue

            if current_number is not None:
                current_lines.append(line)

    if current_number is not None:
        questions.append(_build_question(current_number, current_state, current_lines))

    return questions


def select_questions_for_state(
    questions: list[Question], state: str = "Berlin"
) -> list[Question]:
    return [
        question
        for question in questions
        if question.state is None or question.state == state
    ]


def _build_question(number: int, state: str | None, lines: list[str]) -> Question:
    question_lines: list[str] = []
    option_texts: list[str] = []
    current_option_index: int | None = None
    in_options = False

    for line in lines:
        option_text = _strip_option_marker(line)
        if option_text is not None:
            in_options = True
            option_texts.append(option_text)
            current_option_index = len(option_texts) - 1
            continue

        if in_options and current_option_index is not None:
            option_texts[current_option_index] = (
                f"{option_texts[current_option_index]} {line}".strip()
            )
            continue

        if _is_image_label(line):
            continue
        question_lines.append(line)

    question_id = str(number) if state is None else f"{STATE_CODES[state]}-{number}"
    return Question(
        id=question_id,
        state=state,
        text=" ".join(question_lines),
        options=tuple(_build_options(option_texts, question_lines)),
    )


def _build_options(
    option_texts: list[str], question_lines: list[str]
) -> list[AnswerOption]:
    option_ids = ["a", "b", "c", "d"]
    image_only_options = _options_are_image_only(option_texts, question_lines)
    options: list[AnswerOption] = []
    for option_id, text in zip(option_ids, option_texts, strict=False):
        options.append(
            AnswerOption(
                id=option_id,
                text="" if image_only_options else text,
                is_image_only=image_only_options,
            )
        )
    return options


def _strip_option_marker(line: str) -> str | None:
    if not line.startswith(_OPTION_MARKERS):
        return None
    return line[1:].strip()


def _detect_state_heading(line: str) -> str | None:
    if not line.startswith("Fragen für"):
        return None
    for state in sorted(STATE_CODES, key=len, reverse=True):
        if state in line:
            return state
    return None


def _is_ignored_line(line: str) -> bool:
    return (
        line in {"Teil I", "Teil II", "Allgemeine Fragen"}
        or _PAGE_HEADER_RE.match(line) is not None
        or line.startswith("© ")
    )


def _is_image_label(line: str) -> bool:
    return re.fullmatch(r"Bild\s+\d+", line) is not None


def _options_are_image_only(
    option_texts: list[str], question_lines: list[str]
) -> bool:
    if option_texts and all(_is_image_label(text) for text in option_texts):
        return True
    question_text = " ".join(question_lines)
    return (
        question_text.startswith("Welches Bundesland ist")
        and bool(option_texts)
        and all(text in {"1", "2", "3", "4"} for text in option_texts)
    )
