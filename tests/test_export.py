import csv
import json
from pathlib import Path

from leben_vocab.answers import StructuredAnswer
from leben_vocab.blacklist import VocabularyBlacklist
from leben_vocab.export import export_vocabulary
from leben_vocab.official_corpus import parse_official_questions, select_questions_for_state
from leben_vocab.translation import FixtureTranslationProvider


class SelectedQuestionAnswerProvider:
    def __init__(self, state):
        questions = select_questions_for_state(
            parse_official_questions(Path("lid2026.pdf")), state
        )
        self.answers = []
        for question in questions:
            option = next(
                (
                    option
                    for option in question.options
                    if option.text and not option.is_image_only
                ),
                question.options[0],
            )
            self.answers.append(
                StructuredAnswer(
                    question_id=question.id,
                    correct_option_id=option.id,
                    question_text=question.text,
                    correct_answer_text=option.text,
                )
            )

    def load_answer_keys(self):
        return self.answers


def test_official_export_uses_pdf_corpus_and_writes_many_rows_with_step_log(tmp_path):
    output_path = tmp_path / "dist" / "words_en.csv"
    log_path = tmp_path / "dist" / "logs" / "words_en.jsonl"

    export_vocabulary(
        state="Berlin",
        target_language="en",
        output_path=output_path,
        answer_provider=SelectedQuestionAnswerProvider("Berlin"),
        translation_provider=FixtureTranslationProvider(),
        log_path=log_path,
    )

    with output_path.open(newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert len(rows) > 100
    assert {row["target_language"] for row in rows} == {"en"}

    log_entries = [
        json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()
    ]
    assert [entry["step"] for entry in log_entries] == [
        "parse_corpus",
        "select_questions",
        "load_answers",
        "match_answers",
        "extract_vocabulary",
        "filter_vocabulary",
        "merge_vocabulary",
        "filter_min_count",
        "translate_vocabulary",
        "write_csv",
    ]
    assert log_entries[0]["question_count"] == 460
    assert log_entries[1]["selected_question_count"] == 310
    assert log_entries[7]["vocabulary_count"] == len(rows)
    assert log_entries[7]["min_count"] == 2
    assert log_entries[8]["provider"] == "fixture"
    assert all(int(row["count"]) >= 2 for row in rows)


class OrderedTranslationProvider:
    name = "ordered"

    def translate(self, word, target_language):
        translations = {
            ("leben", "en"): "to live",
            ("leben", "fa"): "زندگی کردن",
        }
        return translations.get((word, target_language), f"{word}-{target_language}")


def test_export_joins_multiple_translations_in_requested_language_order(tmp_path):
    output_path = tmp_path / "dist" / "words.csv"

    export_vocabulary(
        state="Berlin",
        target_languages=["en", "fa"],
        output_path=output_path,
        answer_provider=SelectedQuestionAnswerProvider("Berlin"),
        translation_provider=OrderedTranslationProvider(),
        normalizer=None,
        log_path=tmp_path / "dist" / "logs" / "words.jsonl",
    )

    with output_path.open(newline="", encoding="utf-8") as csv_file:
        leben = next(row for row in csv.DictReader(csv_file) if row["word"] == "leben")

    assert leben["translation"] == "to live , زندگی کردن"
    assert leben["target_language"] == "en,fa"


def test_export_filters_blacklisted_words_before_translation(tmp_path):
    output_path = tmp_path / "dist" / "words.csv"

    export_vocabulary(
        state="Berlin",
        target_languages=["en", "fa"],
        output_path=output_path,
        answer_provider=SelectedQuestionAnswerProvider("Berlin"),
        translation_provider=OrderedTranslationProvider(),
        normalizer=None,
        log_path=tmp_path / "dist" / "logs" / "words.jsonl",
        blacklist=VocabularyBlacklist(frozenset({"deutschland", "die"})),
    )

    with output_path.open(newline="", encoding="utf-8") as csv_file:
        words = {row["word"] for row in csv.DictReader(csv_file)}

    assert "deutschland" not in words
    assert "die" not in words
    assert "leben" in words


def test_export_filters_words_below_custom_min_count_before_translation(tmp_path):
    output_path = tmp_path / "dist" / "words.csv"
    log_path = tmp_path / "dist" / "logs" / "words.jsonl"

    export_vocabulary(
        state="Berlin",
        target_language="en",
        output_path=output_path,
        answer_provider=SelectedQuestionAnswerProvider("Berlin"),
        translation_provider=FixtureTranslationProvider(),
        log_path=log_path,
        min_count=5,
    )

    with output_path.open(newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))

    log_entries = [
        json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()
    ]
    min_count_log = next(
        entry for entry in log_entries if entry["step"] == "filter_min_count"
    )

    assert rows
    assert all(int(row["count"]) >= 5 for row in rows)
    assert min_count_log["min_count"] == 5
    assert min_count_log["filtered_count"] > 0
