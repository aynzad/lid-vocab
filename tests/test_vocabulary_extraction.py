from leben_vocab.answers import AnswerKey
from leben_vocab.corpus import AnswerOption, Question
from leben_vocab.vocabulary import GermanVocabularyNormalizer, extract_vocabulary


def test_extraction_uses_question_text_and_correct_answer_text_only():
    questions = [
        Question(
            id="1",
            state=None,
            text="Die Bürger wählen das Parlament.",
            options=(
                AnswerOption(id="a", text="die Regierung"),
                AnswerOption(id="b", text="die Monarchie"),
            ),
        )
    ]

    items = extract_vocabulary(
        questions,
        [AnswerKey(question_id="1", correct_option_id="a")],
        normalizer=GermanVocabularyNormalizer(
            verb_lemmas={"wählen": "wählen"},
            noun_forms={
                "bürger": ("der", "Bürger", "Bürger"),
                "parlament": ("das", "Parlament", "Parlamente"),
                "regierung": ("die", "Regierung", "Regierungen"),
                "monarchie": ("die", "Monarchie", "Monarchien"),
            },
        ),
    )

    assert [(item.word, item.kind, item.display) for item in items] == [
        ("bürger", "noun", "der Bürger, Bürger"),
        ("wählen", "verb", "wählen"),
        ("parlament", "noun", "das Parlament, Parlamente"),
        ("regierung", "noun", "die Regierung, Regierungen"),
    ]
    assert "monarchie" not in {item.word for item in items}


def test_extraction_counts_items_and_keeps_one_traceable_example():
    questions = [
        Question(
            id="1",
            state=None,
            text="Die Bürger wählen das Parlament.",
            options=(AnswerOption(id="a", text="die Bürger"),),
        ),
        Question(
            id="2",
            state=None,
            text="Viele Bürger lesen.",
            options=(AnswerOption(id="a", text="das Parlament"),),
        ),
    ]

    items = extract_vocabulary(
        questions,
        [
            AnswerKey(question_id="1", correct_option_id="a"),
            AnswerKey(question_id="2", correct_option_id="a"),
        ],
        normalizer=GermanVocabularyNormalizer(
            verb_lemmas={"wählen": "wählen", "lesen": "lesen"},
            noun_forms={
                "bürger": ("der", "Bürger", "Bürger"),
                "parlament": ("das", "Parlament", "Parlamente"),
            },
        ),
    )

    by_word = {item.word: item for item in items}
    assert by_word["bürger"].count == 3
    assert by_word["bürger"].example == "Die Bürger wählen das Parlament."
    assert by_word["bürger"].example_source == "question"
    assert by_word["bürger"].question_id == "1"


def test_image_only_correct_answer_contributes_no_answer_vocabulary():
    questions = [
        Question(
            id="BE-1",
            state="Berlin",
            text="Welches Wappen gehört zum Bundesland Berlin?",
            options=(AnswerOption(id="a", text="", is_image_only=True),),
        )
    ]

    items = extract_vocabulary(
        questions,
        [AnswerKey(question_id="BE-1", correct_option_id="a")],
        normalizer=GermanVocabularyNormalizer(
            noun_forms={
                "wappen": (None, "Wappen", None),
                "bundesland": ("das", "Bundesland", "Bundesländer"),
                "berlin": (None, "Berlin", None),
            },
        ),
    )

    assert [item.word for item in items] == ["wappen", "bundesland", "berlin"]
    assert items[0].display == "Wappen"
