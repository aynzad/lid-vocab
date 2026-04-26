import pytest

from leben_vocab.answers import (
    AnswerKey,
    AnswerMatchingError,
    FixtureAnswerProvider,
    PinnedGitHubAnswerProvider,
    StructuredAnswer,
    match_answer_keys,
)
from leben_vocab.corpus import AnswerOption, Question
from leben_vocab.vocabulary import extract_vocabulary


def test_answer_matching_prefers_official_question_numbers():
    questions = [
        Question(
            id="42",
            state=None,
            text="Welche Partei ist im Deutschen Bundestag vertreten?",
            options=(
                AnswerOption(id="a", text="Partei A"),
                AnswerOption(id="b", text="Partei B"),
                AnswerOption(id="c", text="Partei C"),
                AnswerOption(id="d", text="Partei D"),
            ),
        )
    ]
    provider = FixtureAnswerProvider(
        [
            StructuredAnswer(
                question_id="42",
                correct_option_id="c",
                question_text="Third-party wording that must not be authoritative",
            )
        ]
    )

    matches = match_answer_keys(questions, provider.load_answer_keys())

    assert matches == [AnswerKey(question_id="42", correct_option_id="c")]


def test_answer_matching_falls_back_to_normalized_question_text():
    questions = [
        Question(
            id="17",
            state=None,
            text="Wer wählt den Deutschen Bundestag?",
            options=(
                AnswerOption(id="a", text="die Bundesregierung"),
                AnswerOption(id="b", text="das Volk"),
                AnswerOption(id="c", text="der Bundesrat"),
                AnswerOption(id="d", text="die Gerichte"),
            ),
        )
    ]
    provider = FixtureAnswerProvider(
        [
            StructuredAnswer(
                question_id="third-party-17",
                correct_option_id="b",
                question_text="Wer waehlt den deutschen Bundestag",
            )
        ]
    )

    matches = match_answer_keys(questions, provider.load_answer_keys())

    assert matches == [AnswerKey(question_id="17", correct_option_id="b")]


def test_answer_matching_uses_correct_answer_text_to_resolve_similar_questions():
    questions = [
        Question(
            id="143",
            state=None,
            text="Eine Richterin/ein Richter in Deutschland gehört zur …",
            options=(
                AnswerOption(id="a", text="Judikative."),
                AnswerOption(id="b", text="Exekutive."),
            ),
        ),
        Question(
            id="144",
            state=None,
            text="Eine Richterin/ein Richter gehört in Deutschland zur …",
            options=(
                AnswerOption(id="a", text="vollziehenden Gewalt."),
                AnswerOption(id="b", text="rechtsprechenden Gewalt."),
            ),
        ),
    ]
    provider = FixtureAnswerProvider(
        [
            StructuredAnswer(
                question_id="third-party-199",
                correct_option_id="a",
                question_text="Ein Richter/eine Richterin in Deutschland gehört zur …",
                correct_answer_text="Judikative",
                prefer_id=False,
            ),
            StructuredAnswer(
                question_id="third-party-204",
                correct_option_id="a",
                question_text="Ein Richter/eine Richterin gehört in Deutschland zur …",
                correct_answer_text="rechtsprechenden Gewalt",
                prefer_id=False,
            ),
        ]
    )

    matches = match_answer_keys(questions, provider.load_answer_keys())

    assert matches == [
        AnswerKey(question_id="143", correct_option_id="a"),
        AnswerKey(question_id="144", correct_option_id="b"),
    ]


def test_answer_matching_fails_with_audit_friendly_diagnostics():
    questions = [
        Question(
            id="99",
            state=None,
            text="Welche Aufgabe hat der Bundesrat?",
            options=(
                AnswerOption(id="a", text="Option A"),
                AnswerOption(id="b", text="Option B"),
                AnswerOption(id="c", text="Option C"),
                AnswerOption(id="d", text="Option D"),
            ),
        )
    ]
    provider = FixtureAnswerProvider(
        [
            StructuredAnswer(
                question_id="not-99",
                correct_option_id="a",
                question_text="Eine andere Frage",
            )
        ]
    )

    with pytest.raises(AnswerMatchingError, match="unmatched question ids: 99"):
        match_answer_keys(questions, provider.load_answer_keys())


def test_pinned_github_provider_loads_correct_answer_data_for_matching_only():
    requested_urls = []

    def fetch_json(url):
        requested_urls.append(url)
        return [
            {
                "num": "1",
                "question": "Third-party wording for matching fallback only",
                "a": "Do not use this wording",
                "b": "Do not use this wording either",
                "solution": "b",
            }
        ]

    provider = PinnedGitHubAnswerProvider(fetch_json=fetch_json)

    assert provider.load_answer_keys() == [
        StructuredAnswer(
            question_id="1",
            correct_option_id="b",
            question_text="Third-party wording for matching fallback only",
            correct_answer_text="Do not use this wording either",
            prefer_id=False,
        )
    ]
    assert requested_urls == [PinnedGitHubAnswerProvider.SOURCE_URL]
    assert "b1832e7145080e0f70ebd680f24efc0933892e18" in provider.SOURCE_URL


def test_vocabulary_input_uses_correct_answer_and_excludes_distractors():
    question = Question(
        id="5",
        state=None,
        text="Eine neutrale Frage.",
        options=(
            AnswerOption(id="a", text="Demokratie"),
            AnswerOption(id="b", text="Wahl"),
        ),
    )

    items = extract_vocabulary(
        [question],
        [AnswerKey(question_id="5", correct_option_id="b")],
    )

    assert [item.word for item in items] == ["wahl"]
