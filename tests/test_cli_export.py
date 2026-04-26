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
        "[leben-vocab] parse corpus",
        "[leben-vocab] write csv",
    ]


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
