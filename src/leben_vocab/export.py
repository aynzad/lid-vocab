from pathlib import Path
import json
from typing import Any, Callable

from leben_vocab.blacklist import (
    VocabularyBlacklist,
    filter_blacklisted_items,
)
from leben_vocab.answers import (
    FixtureAnswerProvider,
    PinnedGitHubAnswerProvider,
    match_answer_keys,
)
from leben_vocab.corpus import FixtureCorpusProvider
from leben_vocab.csv_export import write_vocabulary_csv
from leben_vocab.merge import merge_related_items
from leben_vocab.official_corpus import parse_official_questions, select_questions_for_state
from leben_vocab.translation import (
    FixtureTranslationProvider,
    TranslationRouter,
    build_production_translation_router,
)
from leben_vocab.vocabulary import (
    GermanNounLookup,
    GermanVocabularyNormalizer,
    SpacyGermanAnalyzer,
    extract_vocabulary,
)


def export_fixture_vocabulary(
    state: str,
    target_language: str,
    output_path: Path,
    corpus_provider: FixtureCorpusProvider | None = None,
    answer_provider: FixtureAnswerProvider | None = None,
    translation_provider: FixtureTranslationProvider | TranslationRouter | None = None,
) -> None:
    corpus_provider = corpus_provider or FixtureCorpusProvider()
    answer_provider = answer_provider or FixtureAnswerProvider()
    translation_provider = translation_provider or FixtureTranslationProvider()

    questions = corpus_provider.load_questions(state)
    answer_keys = match_answer_keys(questions, answer_provider.load_answer_keys())
    items = extract_vocabulary(questions, answer_keys)
    if isinstance(translation_provider, TranslationRouter):
        translated_items = translation_provider.translate_items(items, target_language)
    else:
        translated_items = [
            item.with_translation(
                translation_provider.translate(item.word, target_language) or ""
            )
            for item in items
        ]
    write_vocabulary_csv(translated_items, target_language, output_path)


def export_vocabulary(
    state: str,
    output_path: Path,
    target_languages: list[str] | None = None,
    target_language: str | None = None,
    pdf_path: Path = Path("lid2026.pdf"),
    answer_provider: Any | None = None,
    translation_provider: FixtureTranslationProvider | TranslationRouter | None = None,
    normalizer: GermanVocabularyNormalizer | None = None,
    log_path: Path | None = None,
    progress: Callable[[str], None] | None = None,
    blacklist: VocabularyBlacklist | None = None,
) -> None:
    answer_provider = answer_provider or PinnedGitHubAnswerProvider()
    translation_provider = translation_provider or build_production_translation_router()
    languages = _target_languages(target_languages, target_language)
    target_language_label = ",".join(languages)
    normalizer = normalizer or GermanVocabularyNormalizer(
        analyzer=SpacyGermanAnalyzer(),
        noun_lookup=GermanNounLookup(),
        include_unknown=True,
    )
    step_log = ExportStepLog(log_path or _default_log_path(output_path))
    emit_progress = progress or _ignore_progress
    blacklist = blacklist or VocabularyBlacklist.from_path()

    emit_progress(f"Parsing corpus from {pdf_path}")
    questions = parse_official_questions(pdf_path)
    step_log.write("parse_corpus", question_count=len(questions), pdf_path=str(pdf_path))

    emit_progress(f"Selecting {state} questions")
    selected_questions = select_questions_for_state(questions, state)
    step_log.write(
        "select_questions",
        state=state,
        selected_question_count=len(selected_questions),
    )

    emit_progress("Loading answer key")
    structured_answers = answer_provider.load_answer_keys()
    step_log.write("load_answers", answer_count=len(structured_answers))

    emit_progress("Matching answers to official questions")
    answer_keys = match_answer_keys(selected_questions, structured_answers)
    step_log.write("match_answers", matched_answer_count=len(answer_keys))

    emit_progress("Extracting vocabulary")
    items = extract_vocabulary(selected_questions, answer_keys, normalizer=normalizer)
    step_log.write("extract_vocabulary", vocabulary_count=len(items))

    unfiltered_count = len(items)
    items = filter_blacklisted_items(items, blacklist)
    filtered_count = unfiltered_count - len(items)
    emit_progress(f"Filtering vocabulary blacklist ({filtered_count} removed)")
    step_log.write(
        "filter_vocabulary",
        vocabulary_count=len(items),
        filtered_count=filtered_count,
        blacklist_path=str(blacklist.source_path) if blacklist.source_path else None,
    )

    unmerged_count = len(items)
    items = merge_related_items(items, compound_lookup=normalizer.noun_lookup)
    merged_count = unmerged_count - len(items)
    emit_progress(f"Merging related vocabulary rows ({merged_count} merged)")
    step_log.write(
        "merge_vocabulary",
        vocabulary_count=len(items),
        merged_count=merged_count,
    )

    emit_progress(
        f"Translating {len(items)} vocabulary rows to {', '.join(languages)}"
    )
    translated_items = _translate_items(items, languages, translation_provider)
    step_log.write(
        "translate_vocabulary",
        translated_count=len(translated_items),
        target_languages=languages,
        **_translation_log_fields(translation_provider),
    )

    emit_progress(f"Writing CSV to {output_path}")
    write_vocabulary_csv(translated_items, target_language_label, output_path)
    step_log.write("write_csv", output_path=str(output_path), row_count=len(translated_items))
    emit_progress(f"Done: wrote {len(translated_items)} rows")


def _translate_items(
    items,
    target_languages: list[str],
    translation_provider: FixtureTranslationProvider | TranslationRouter,
):
    return [
        item.with_translation(
            " , ".join(
                _translate_item(item, target_language, translation_provider)
                for target_language in target_languages
            )
        )
        for item in items
    ]


def _translate_item(
    item,
    target_language: str,
    translation_provider: FixtureTranslationProvider | TranslationRouter,
) -> str:
    if isinstance(translation_provider, TranslationRouter):
        return translation_provider.translate_item(item, target_language).translation
    return translation_provider.translate(item.word, target_language) or ""


def _target_languages(
    target_languages: list[str] | None, target_language: str | None
) -> list[str]:
    if target_languages:
        return target_languages
    if target_language:
        return [target_language]
    raise ValueError("At least one target language is required")


def _default_log_path(output_path: Path) -> Path:
    return output_path.parent / "logs" / f"{output_path.stem}.jsonl"


def _translation_log_fields(
    translation_provider: FixtureTranslationProvider | TranslationRouter,
) -> dict[str, str]:
    if isinstance(translation_provider, TranslationRouter):
        return {
            "deepl_provider": translation_provider.deepl_provider.name,
            "fallback_provider": translation_provider.fallback_provider.name,
            "cache": translation_provider.cache.__class__.__name__,
        }
    return {"provider": translation_provider.name}


class ExportStepLog:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text("", encoding="utf-8")

    def write(self, step: str, **fields: Any) -> None:
        with self.path.open("a", encoding="utf-8") as log_file:
            log_file.write(json.dumps({"step": step, **fields}, ensure_ascii=False))
            log_file.write("\n")


def _ignore_progress(message: str) -> None:
    pass
