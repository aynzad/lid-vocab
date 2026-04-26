import json

import pytest

from leben_vocab.answers import StructuredAnswer
from leben_vocab.corpus import AnswerOption, Question
from leben_vocab.notebook import (
    NotebookValidationError,
    REVIEWED_STATUS,
    render_ai_pack_markdown,
    render_notebook_prompt,
    seed_answer_records,
    validate_reviewed_answer_records,
)


def test_seed_records_preserve_all_options_and_review_fields():
    question = Question(
        id="1",
        state=None,
        text="Was bedeutet Volkssouveränität?",
        options=(
            AnswerOption(id="a", text="Alle Staatsgewalt geht vom Volke aus."),
            AnswerOption(id="b", text="Die Regierung entscheidet allein."),
            AnswerOption(id="c", text="Nur Gerichte entscheiden."),
            AnswerOption(id="d", text="Nur Parteien entscheiden."),
        ),
    )
    answers = [
        StructuredAnswer(
            question_id="third-party-1",
            correct_option_id="a",
            question_text="Was bedeutet Volkssouveränität?",
            correct_answer_text="Alle Staatsgewalt geht vom Volke aus.",
            prefer_id=False,
        )
    ]

    records = seed_answer_records([question], answers)

    assert records[0].question_id == "1"
    assert [option["id"] for option in records[0].options] == ["a", "b", "c", "d"]
    assert records[0].seed_correct_option_id == "a"
    assert records[0].seed_correct_answer_text == "Alle Staatsgewalt geht vom Volke aus."
    assert records[0].match_method == "exact-text"
    assert records[0].needs_review is False
    assert records[0].review_status == "unreviewed"


def test_seed_records_handle_image_only_answers():
    question = Question(
        id="BE-1",
        state="Berlin",
        text="Welches ist das Wappen von Berlin?",
        options=(
            AnswerOption(id="a", text="", is_image_only=True),
            AnswerOption(id="b", text="", is_image_only=True),
            AnswerOption(id="c", text="", is_image_only=True),
            AnswerOption(id="d", text="", is_image_only=True),
        ),
    )
    answers = [
        StructuredAnswer(
            question_id="third-party-be-1",
            correct_option_id="b",
            question_text="Welches ist das Wappen von Berlin?",
            correct_answer_text="Bild 2",
            prefer_id=False,
        )
    ]

    record = seed_answer_records([question], answers)[0]

    assert record.seed_correct_option_id == "b"
    assert record.seed_correct_answer_text == "Bild 2"
    assert all(option["is_image_only"] for option in record.options)


def test_seed_records_resolve_correct_answer_text_when_option_letters_differ():
    question = Question(
        id="1",
        state=None,
        text="In Deutschland dürfen Menschen offen etwas gegen die Regierung sagen, weil …",
        options=(
            AnswerOption(id="a", text="hier Religionsfreiheit gilt."),
            AnswerOption(id="b", text="die Menschen Steuern zahlen."),
            AnswerOption(id="c", text="die Menschen das Wahlrecht haben."),
            AnswerOption(id="d", text="hier Meinungsfreiheit gilt."),
        ),
    )
    answers = [
        StructuredAnswer(
            question_id="1",
            correct_option_id="a",
            question_text="In Deutschland dürfen Menschen offen etwas gegen die Regierung sagen, weil …",
            correct_answer_text="hier Meinungsfreiheit gilt.",
            prefer_id=False,
        )
    ]

    record = seed_answer_records([question], answers)[0]

    assert record.seed_correct_option_id == "d"
    assert record.seed_correct_answer_text == "hier Meinungsfreiheit gilt."
    assert record.needs_review is False


def test_misaligned_answer_source_is_flagged_instead_of_silently_accepted():
    question = Question(
        id="5",
        state=None,
        text="Wahlen in Deutschland sind frei. Was bedeutet das?",
        options=(
            AnswerOption(id="a", text="Man darf Geld annehmen."),
            AnswerOption(id="b", text="Nur Personen ohne Gefängnis dürfen wählen."),
            AnswerOption(id="c", text="Niemand darf zur Stimmabgabe gezwungen werden."),
            AnswerOption(id="d", text="Alle Personen müssen wählen."),
        ),
    )
    answers = [
        StructuredAnswer(
            question_id="5",
            correct_option_id="a",
            question_text="Was bedeutet die Abkürzung DDR?",
            correct_answer_text="Deutsche Demokratische Republik",
            prefer_id=False,
        )
    ]

    record = seed_answer_records([question], answers)[0]

    assert record.needs_review is True
    assert record.seed_correct_option_id == ""
    assert record.match_confidence < 0.65


def test_validate_reviewed_records_rejects_unreviewed_missing_duplicate_and_invalid():
    questions = [
        Question(
            id="1",
            state=None,
            text="Question one?",
            options=(
                AnswerOption(id="a", text="Answer A"),
                AnswerOption(id="b", text="Answer B"),
            ),
        ),
        Question(
            id="2",
            state=None,
            text="Question two?",
            options=(
                AnswerOption(id="a", text="Answer A"),
                AnswerOption(id="b", text="Answer B"),
            ),
        ),
    ]
    records = [
        {
            "question_id": "1",
            "question": "Question one?",
            "options": [],
            "seed_correct_option_id": "z",
            "seed_correct_answer_text": "",
            "review_status": "unreviewed",
        },
        {
            "question_id": "1",
            "question": "Question one?",
            "options": [],
            "seed_correct_option_id": "a",
            "seed_correct_answer_text": "Answer A",
            "review_status": REVIEWED_STATUS,
        },
    ]

    with pytest.raises(NotebookValidationError) as exc_info:
        validate_reviewed_answer_records(questions, records)

    message = str(exc_info.value)
    assert "Duplicate answer record for 1" in message
    assert "Answer record 1 is not reviewed" in message
    assert "invalid option 'z'" in message
    assert "Missing reviewed answer for 2" in message


def test_validate_reviewed_records_returns_selected_records_in_question_order():
    questions = [
        Question(
            id="2",
            state=None,
            text="Question two?",
            options=(AnswerOption(id="a", text="Answer two"),),
        ),
        Question(
            id="1",
            state=None,
            text="Question one?",
            options=(AnswerOption(id="a", text="Answer one"),),
        ),
    ]
    records = [
        {
            "question_id": "2",
            "question": "Question two?",
            "options": [],
            "seed_correct_option_id": "a",
            "seed_correct_answer_text": "Answer two",
            "review_status": REVIEWED_STATUS,
        },
        {
            "question_id": "1",
            "question": "Question one?",
            "options": [],
            "seed_correct_option_id": "a",
            "seed_correct_answer_text": "Answer one",
            "review_status": REVIEWED_STATUS,
        },
    ]

    validated = validate_reviewed_answer_records(questions, records)

    assert [record["question_id"] for record in validated] == ["1", "2"]


def test_rendered_pack_and_prompt_include_notebook_contract(tmp_path):
    records = [
        {
            "question_id": "152",
            "question": "Wann waren die Nationalsozialisten an der Macht?",
            "options": [{"id": "a", "text": "1933 bis 1945", "is_image_only": False}],
            "seed_correct_option_id": "a",
            "seed_correct_answer_text": "1933 bis 1945",
            "review_status": REVIEWED_STATUS,
        }
    ]
    pack = render_ai_pack_markdown("Berlin", records)
    prompt = render_notebook_prompt("Berlin", tmp_path / "pack.md")

    assert "Citation: Q152: 1933 bis 1945" in pack
    assert "Constitution & Rights" in prompt
    assert "global category index" in prompt
    assert "Markdown link that correctly jumps to that category header" in prompt
    assert "Merge repeated facts into one note" in prompt
    assert "Markdown-only" in prompt
    assert "Keywords:" in prompt
    assert "Do not add category-level note indexes" in prompt
    assert "1. Fact in one compact sentence." in prompt
    assert "> Questions: 152,155" in prompt
    assert "Q152` -> `152" in prompt


def test_reviewed_answer_json_example_is_serializable():
    question = Question(
        id="1",
        state=None,
        text="Question?",
        options=(AnswerOption(id="a", text="Answer"),),
    )
    answer = StructuredAnswer(
        question_id="1",
        correct_option_id="a",
        question_text="Question?",
        correct_answer_text="Answer",
        prefer_id=False,
    )

    record = seed_answer_records([question], [answer])[0]

    assert json.loads(json.dumps([record.to_dict()]))[0]["question_id"] == "1"
