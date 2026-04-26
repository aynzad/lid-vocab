from leben_vocab.blacklist import VocabularyBlacklist, filter_blacklisted_items
from leben_vocab.vocabulary import VocabularyItem


def item(word):
    return VocabularyItem(
        word=word,
        kind="word",
        display=word,
        translation="",
        example="example",
        example_source="question",
        question_id="1",
        count=1,
    )


def test_blacklist_loads_words_case_insensitively_and_ignores_comments(tmp_path):
    path = tmp_path / "blacklist.txt"
    path.write_text(
        """
        # function words
        Die
        von # preposition

        Berlin
        """,
        encoding="utf-8",
    )

    blacklist = VocabularyBlacklist.from_path(path)

    assert blacklist.words == frozenset({"die", "von", "berlin"})
    assert blacklist.source_path == path


def test_filter_blacklisted_items_removes_only_matching_normalized_words():
    blacklist = VocabularyBlacklist(frozenset({"die", "berlin"}))

    filtered = filter_blacklisted_items(
        [item("die"), item("leben"), item("berlin")],
        blacklist,
    )

    assert [item.word for item in filtered] == ["leben"]


def test_default_blacklist_covers_common_names_places_and_cognates():
    blacklist = VocabularyBlacklist.from_path()

    assert {
        "berlin",
        "friedrich",
        "usa",
        "integration",
        "universität",
        "dänemark",
        "köln",
        "schweiz",
        "schweden",
        "schwede",
        "schwedisch",
        "schweizen",
        "schweizerisch",
        "türkei",
        "türkisch",
        "ägypten",
    } <= blacklist.words
