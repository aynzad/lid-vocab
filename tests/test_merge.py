from leben_vocab.merge import merge_related_items
from leben_vocab.vocabulary import VocabularyItem


def item(word, kind="noun", display=None, count=1):
    return VocabularyItem(
        word=word,
        kind=kind,
        display=display or word,
        translation="",
        example="example",
        example_source="question",
        question_id="1",
        count=count,
    )


def test_merges_feminine_role_pair_into_base_noun():
    merged = merge_related_items(
        [
            item("bürger", display="der Bürger, Bürger", count=3),
            item("bürgerin", display="die Bürgerin, Bürgerinnen", count=2),
        ]
    )

    assert [(item.word, item.count) for item in merged] == [("bürger", 5)]


def test_merges_inflected_word_variant_into_base_word():
    merged = merge_related_items(
        [
            item("ausländisch", kind="word", count=1),
            item("ausländische", kind="word", count=2),
        ]
    )

    assert [(item.word, item.count) for item in merged] == [("ausländisch", 3)]


def test_merges_compound_noun_into_highest_count_existing_part():
    merged = merge_related_items(
        [
            item("wahl", display="die Wahl, Wahlen", count=4),
            item("bundestagswahl", display="die Bundestagswahl, Bundestagswahlen", count=2),
        ],
        compound_lookup=FakeCompoundLookup(
            {"Bundestagswahl": ["Bundestag", "Wahl"]}
        ),
    )

    assert [(item.word, item.count) for item in merged] == [("wahl", 6)]


class FakeCompoundLookup:
    def __init__(self, compounds):
        self.compounds = compounds

    def compound_parts(self, token):
        return self.compounds.get(token, [])
