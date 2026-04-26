import csv
from unittest.mock import ANY

from leben_vocab.cli import main
from leben_vocab.export import export_fixture_vocabulary


def test_main_delegates_to_official_export(monkeypatch, tmp_path):
    output_path = tmp_path / "dist" / "words_en.csv"
    calls = []

    def fake_export_vocabulary(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("leben_vocab.cli.export_vocabulary", fake_export_vocabulary)

    exit_code = main(
        [
            "export",
            "--state",
            "Berlin",
            "--target-lang",
            "en",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert calls == [
        {
            "state": "Berlin",
            "target_languages": ["en"],
            "output_path": output_path,
            "min_count": 2,
            "progress": ANY,
        }
    ]


def test_main_routes_relative_outputs_to_dist(monkeypatch):
    calls = []

    def fake_export_vocabulary(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("leben_vocab.cli.export_vocabulary", fake_export_vocabulary)

    main(
        [
            "export",
            "--state",
            "Berlin",
            "--target-lang",
            "en",
            "--output",
            "words_en.csv",
        ]
    )

    assert calls[0]["output_path"].as_posix() == "dist/words_en.csv"


def test_main_preserves_ordered_target_language_list(monkeypatch):
    calls = []

    def fake_export_vocabulary(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("leben_vocab.cli.export_vocabulary", fake_export_vocabulary)

    main(
        [
            "export",
            "--state",
            "Berlin",
            "--target-lang",
            "en,fa",
            "--output",
            "words.csv",
        ]
    )

    assert calls[0]["target_languages"] == ["en", "fa"]


def test_main_passes_custom_min_count(monkeypatch):
    calls = []

    def fake_export_vocabulary(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("leben_vocab.cli.export_vocabulary", fake_export_vocabulary)

    main(
        [
            "export",
            "--state",
            "Berlin",
            "--target-lang",
            "en",
            "--output",
            "words.csv",
            "--min-count",
            "4",
        ]
    )

    assert calls[0]["min_count"] == 4


def test_main_prints_export_progress_to_stderr(monkeypatch, capsys):
    def fake_export_vocabulary(**kwargs):
        kwargs["progress"]("parse corpus")
        kwargs["progress"]("write csv")

    monkeypatch.setattr("leben_vocab.cli.export_vocabulary", fake_export_vocabulary)

    main(
        [
            "export",
            "--state",
            "Berlin",
            "--target-lang",
            "en",
            "--output",
            "words_en.csv",
        ]
    )

    captured = capsys.readouterr()
    assert captured.err.splitlines() == [
        "[lid-vocab] parse corpus",
        "[lid-vocab] write csv",
    ]


def test_main_delegates_to_qa_seed_with_default_state(monkeypatch):
    calls = []

    def fake_export_qa_seed(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("leben_vocab.cli.export_qa_seed", fake_export_qa_seed)

    exit_code = main(
        [
            "qa-seed",
            "--output",
            "answers-reviewed.json",
            "--review-md",
            "answer_review.md",
        ]
    )

    assert exit_code == 0
    assert calls == [
        {
            "state": "Berlin",
            "output_path": ANY,
            "review_md_path": ANY,
        }
    ]
    assert calls[0]["output_path"].as_posix() == "data/answers-reviewed.json"
    assert calls[0]["review_md_path"].as_posix() == "dist/answer_review.md"


def test_main_preserves_explicit_qa_seed_output_roots(monkeypatch):
    calls = []

    def fake_export_qa_seed(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("leben_vocab.cli.export_qa_seed", fake_export_qa_seed)

    main(
        [
            "qa-seed",
            "--state",
            "Bayern",
            "--output",
            "data/bayern-answers.json",
            "--review-md",
            "dist/bayern-review.md",
        ]
    )

    assert calls[0]["state"] == "Bayern"
    assert calls[0]["output_path"].as_posix() == "data/bayern-answers.json"
    assert calls[0]["review_md_path"].as_posix() == "dist/bayern-review.md"


def test_main_delegates_to_notebook_pack(monkeypatch):
    calls = []

    def fake_export_notebook_pack(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(
        "leben_vocab.cli.export_notebook_pack", fake_export_notebook_pack
    )

    exit_code = main(
        [
            "notebook-pack",
            "--state",
            "Berlin",
            "--answers",
            "data/answers-reviewed.json",
            "--output",
            "berlin_ai_pack.md",
            "--prompt",
            "berlin_notebook_prompt.md",
        ]
    )

    assert exit_code == 0
    assert calls == [
        {
            "state": "Berlin",
            "answers_path": ANY,
            "output_path": ANY,
            "prompt_path": ANY,
        }
    ]
    assert calls[0]["answers_path"].as_posix() == "data/answers-reviewed.json"
    assert calls[0]["output_path"].as_posix() == "dist/berlin_ai_pack.md"
    assert calls[0]["prompt_path"].as_posix() == "dist/berlin_notebook_prompt.md"


def test_fixture_export_writes_berlin_english_csv(tmp_path):
    output_path = tmp_path / "dist" / "words_en.csv"

    export_fixture_vocabulary(
        state="Berlin",
        target_language="en",
        output_path=output_path,
    )

    with output_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)

    assert reader.fieldnames == [
        "word",
        "display",
        "translation",
        "example",
        "type",
        "example_source",
        "question_id",
        "count",
        "target_language",
    ]
    assert rows
    assert {row["target_language"] for row in rows} == {"en"}


def test_fixture_export_sorts_rows_by_count_descending(tmp_path):
    output_path = tmp_path / "words_en.csv"

    export_fixture_vocabulary(
        state="Berlin",
        target_language="en",
        output_path=output_path,
    )

    with output_path.open(newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert [(row["word"], row["count"]) for row in rows] == [
        ("demokratie", "2"),
        ("wahl", "1"),
    ]


def test_fixture_export_writes_bayern_farsi_csv(tmp_path):
    output_path = tmp_path / "words_fa.csv"

    export_fixture_vocabulary(
        state="Bayern",
        target_language="fa",
        output_path=output_path,
    )

    with output_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)

    assert reader.fieldnames == [
        "word",
        "display",
        "translation",
        "example",
        "type",
        "example_source",
        "question_id",
        "count",
        "target_language",
    ]
    assert [(row["word"], row["count"]) for row in rows] == [
        ("demokratie", "2"),
        ("wahl", "1"),
    ]
    assert {row["target_language"] for row in rows} == {"fa"}
    assert rows[-1]["question_id"] == "BY-1"
