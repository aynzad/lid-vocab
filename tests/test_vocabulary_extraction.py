from leben_vocab.answers import AnswerKey
from leben_vocab.corpus import AnswerOption, Question
from leben_vocab.vocabulary import (
    GermanNounLookup,
    GermanVocabularyNormalizer,
    VocabularyItem,
    SpacyGermanAnalyzer,
    extract_vocabulary,
)


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
    by_word = {item.word: item for item in items}
    assert by_word["regierung"].example == "die Regierung"
    assert by_word["regierung"].example_source == "answer"
    assert "monarchie" not in {item.word for item in items}


def test_spacy_verb_lemma_deduplicates_conjugated_forms():
    questions = [
        Question(
            id="1",
            state=None,
            text="Die Bürger wählen.",
            options=(AnswerOption(id="a", text="Der Bürger wählt."),),
        )
    ]

    items = extract_vocabulary(
        questions,
        [AnswerKey(question_id="1", correct_option_id="a")],
        normalizer=GermanVocabularyNormalizer(
            analyzer=SpacyGermanAnalyzer(FakeSpacyModel()),
            noun_lookup=GermanNounLookup(
                {
                    "bürger": {
                        "lemma": "Bürger",
                        "article": "der",
                        "plural": "Bürger",
                    }
                }
            ),
        ),
    )

    by_word = {item.word: item for item in items}
    assert by_word["wählen"].kind == "verb"
    assert by_word["wählen"].display == "wählen"
    assert by_word["wählen"].count == 2
    assert by_word["wählen"].example == "Die Bürger wählen."


def test_contextual_spacy_lemma_counts_different_verb_forms_together():
    questions = [
        Question(
            id="1",
            state=None,
            text="Ich wähle. Du wählst. Sie wählte. Wir haben gewählt.",
            options=(AnswerOption(id="a", text="Sie wählen."),),
        )
    ]

    items = extract_vocabulary(
        questions,
        [AnswerKey(question_id="1", correct_option_id="a")],
        normalizer=GermanVocabularyNormalizer(
            analyzer=SpacyGermanAnalyzer(ContextualFakeSpacyModel()),
        ),
    )

    by_word = {item.word: item for item in items}
    assert by_word["wählen"].count == 5
    assert "wählst" not in by_word


def test_german_noun_lookup_formats_article_and_plural_with_fallbacks():
    normalizer = GermanVocabularyNormalizer(
        noun_lookup=GermanNounLookup(
            {
                "staat": {"lemma": "Staat", "article": "der", "plural": "Staaten"},
                "wappen": {"lemma": "Wappen", "article": None, "plural": None},
                "bürger": {"lemma": "Bürger", "article": "der", "plural": None},
            }
        )
    )

    assert normalizer.normalize("Staat") == ("staat", "noun", "der Staat, Staaten")
    assert normalizer.normalize("Wappen") == ("wappen", "noun", "Wappen")
    assert normalizer.normalize("Bürger") == ("bürger", "noun", "der Bürger")


def test_german_noun_lookup_prefers_lemma_entry_for_plural_surface():
    normalizer = GermanVocabularyNormalizer(
        noun_lookup=GermanNounLookup(FakeGermanNounsWithPluralCollision())
    )

    assert normalizer.normalize("Wahlen") == ("wahl", "noun", "die Wahl, Wahlen")


def test_compound_nouns_count_the_compound_and_its_parts():
    questions = [
        Question(
            id="1",
            state=None,
            text="Die Bundestagswahl und die Wahlbenachrichtigung.",
            options=(AnswerOption(id="a", text="die Wahl"),),
        )
    ]

    items = extract_vocabulary(
        questions,
        [AnswerKey(question_id="1", correct_option_id="a")],
        normalizer=GermanVocabularyNormalizer(
            noun_lookup=GermanNounLookup(FakeGermanNounsWithCompounds()),
        ),
    )

    by_word = {item.word: item for item in items}
    assert by_word["bundestagswahl"].count == 1
    assert by_word["wahlbenachrichtigung"].count == 1
    assert by_word["wahl"].count == 3


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


def test_vocabulary_item_example_falls_back_to_empty_string():
    item = VocabularyItem(
        word="staat",
        kind="noun",
        display="der Staat, Staaten",
        translation="",
        example=None,
        example_source="question",
        question_id="1",
        count=1,
    )

    assert item.example == ""


class FakeSpacyModel:
    def __call__(self, text):
        return [
            FakeToken(token)
            for token in text.split()
        ]


class FakeToken:
    def __init__(self, text):
        self.text = text.strip(".")
        self.lemma_ = {
            "wählt": "wählen",
            "wählen": "wählen",
        }.get(self.text.lower(), self.text.lower())
        self.pos_ = "VERB" if self.lemma_ == "wählen" else "NOUN"
        self.is_alpha = self.text.isalpha()


class ContextualFakeSpacyModel:
    def __call__(self, text):
        return [ContextualFakeToken(token, text) for token in text.split()]


class ContextualFakeToken:
    def __init__(self, text, context):
        self.text = text.strip(".")
        normalized = self.text.lower()
        self.lemma_ = {
            "wähle": "wählen",
            "wählt": "wählen",
            "wählte": "wählen",
            "gewählt": "wählen",
            "wählen": "wählen",
        }.get(normalized, normalized)
        if normalized == "wählst" and context != "wählst":
            self.lemma_ = "wählen"
        self.pos_ = "VERB" if self.lemma_ == "wählen" or normalized == "wählst" else "NOUN"
        self.is_alpha = self.text.isalpha()


class FakeGermanNounsWithPluralCollision:
    def __getitem__(self, key):
        entries = {
            "Wahlen": [
                {"lemma": "Wahlen", "pos": ["Substantiv"], "flexion": {}},
                {
                    "lemma": "Wahl",
                    "genus": "f",
                    "pos": ["Substantiv"],
                    "flexion": {
                        "nominativ singular": "Wahl",
                        "nominativ plural": "Wahlen",
                    },
                },
            ],
        }
        return entries.get(key, [])


class FakeGermanNounsWithCompounds:
    def __getitem__(self, key):
        entries = {
            "Bundestagswahl": [
                {
                    "lemma": "Bundestagswahl",
                    "genus": "f",
                    "flexion": {
                        "nominativ singular": "Bundestagswahl",
                        "nominativ plural": "Bundestagswahlen",
                    },
                }
            ],
            "Wahlbenachrichtigung": [
                {
                    "lemma": "Wahlbenachrichtigung",
                    "genus": "f",
                    "flexion": {
                        "nominativ singular": "Wahlbenachrichtigung",
                        "nominativ plural": "Wahlbenachrichtigungen",
                    },
                }
            ],
            "Wahl": [
                {
                    "lemma": "Wahl",
                    "genus": "f",
                    "flexion": {
                        "nominativ singular": "Wahl",
                        "nominativ plural": "Wahlen",
                    },
                }
            ],
            "Benachrichtigung": [
                {
                    "lemma": "Benachrichtigung",
                    "genus": "f",
                    "flexion": {
                        "nominativ singular": "Benachrichtigung",
                        "nominativ plural": "Benachrichtigungen",
                    },
                }
            ],
        }
        return entries.get(key, [])

    def parse_compound(self, token):
        return {
            "Bundestagswahl": ["Bundestag", "Wahl"],
            "Wahlbenachrichtigung": ["Wahl", "Benachrichtigung"],
        }.get(token, [])
