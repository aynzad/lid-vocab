from pathlib import Path

from leben_vocab.answers import FixtureAnswerProvider, match_answer_keys
from leben_vocab.corpus import FixtureCorpusProvider
from leben_vocab.csv_export import write_vocabulary_csv
from leben_vocab.translation import FixtureTranslationProvider
from leben_vocab.vocabulary import extract_vocabulary


def export_fixture_vocabulary(
    state: str,
    target_language: str,
    output_path: Path,
    corpus_provider: FixtureCorpusProvider | None = None,
    answer_provider: FixtureAnswerProvider | None = None,
    translation_provider: FixtureTranslationProvider | None = None,
) -> None:
    corpus_provider = corpus_provider or FixtureCorpusProvider()
    answer_provider = answer_provider or FixtureAnswerProvider()
    translation_provider = translation_provider or FixtureTranslationProvider()

    questions = corpus_provider.load_questions(state)
    answer_keys = match_answer_keys(questions, answer_provider.load_answer_keys())
    items = extract_vocabulary(questions, answer_keys)
    translated_items = [
        item.with_translation(translation_provider.translate(item.word, target_language))
        for item in items
    ]
    write_vocabulary_csv(translated_items, target_language, output_path)
