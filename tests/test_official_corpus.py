from pathlib import Path

from leben_vocab.official_corpus import (
    parse_official_questions,
    select_questions_for_state,
)


PDF_PATH = Path("lid2026.pdf")


def test_official_pdf_parses_into_460_questions():
    questions = parse_official_questions(PDF_PATH)

    assert len(questions) == 460


def test_general_questions_keep_bamf_numbering():
    questions = parse_official_questions(PDF_PATH)
    general = [question for question in questions if question.state is None]

    assert len(general) == 300
    assert general[0].id == "1"
    assert general[-1].id == "300"


def test_default_selection_returns_general_questions_plus_berlin():
    questions = parse_official_questions(PDF_PATH)

    selected = select_questions_for_state(questions)

    assert len(selected) == 310
    assert [question.id for question in selected[:3]] == ["1", "2", "3"]
    assert [question.id for question in selected[-10:]] == [
        "BE-1",
        "BE-2",
        "BE-3",
        "BE-4",
        "BE-5",
        "BE-6",
        "BE-7",
        "BE-8",
        "BE-9",
        "BE-10",
    ]


def test_non_default_state_selection_is_not_hard_coded_to_berlin():
    questions = parse_official_questions(PDF_PATH)

    selected = select_questions_for_state(questions, state="Bayern")

    assert len(selected) == 310
    assert [question.id for question in selected[-10:]] == [
        "BY-1",
        "BY-2",
        "BY-3",
        "BY-4",
        "BY-5",
        "BY-6",
        "BY-7",
        "BY-8",
        "BY-9",
        "BY-10",
    ]


def test_hyphenated_state_selection_uses_the_full_state_name():
    questions = parse_official_questions(PDF_PATH)

    selected = select_questions_for_state(questions, state="Sachsen-Anhalt")

    assert len(selected) == 310
    assert [question.id for question in selected[-10:]] == [
        "ST-1",
        "ST-2",
        "ST-3",
        "ST-4",
        "ST-5",
        "ST-6",
        "ST-7",
        "ST-8",
        "ST-9",
        "ST-10",
    ]


def test_image_only_answer_options_do_not_fabricate_answer_text():
    questions = parse_official_questions(PDF_PATH)
    berlin_wappen = next(question for question in questions if question.id == "BE-1")

    assert "Welches Wappen gehört" in berlin_wappen.text
    assert [option.text for option in berlin_wappen.options] == ["", "", "", ""]
    assert all(option.is_image_only for option in berlin_wappen.options)
