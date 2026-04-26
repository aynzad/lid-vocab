import csv

from leben_vocab.cli import main


def test_export_command_writes_berlin_english_fixture_csv(tmp_path):
    output_path = tmp_path / "dist" / "words_en.csv"

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
    with output_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)

    assert reader.fieldnames == [
        "word",
        "type",
        "display",
        "translation",
        "example",
        "example_source",
        "question_id",
        "count",
        "target_language",
    ]
    assert rows
    assert {row["target_language"] for row in rows} == {"en"}


def test_export_command_sorts_fixture_rows_by_count_descending(tmp_path):
    output_path = tmp_path / "words_en.csv"

    main(
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

    with output_path.open(newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert [(row["word"], row["count"]) for row in rows] == [
        ("demokratie", "2"),
        ("wahl", "1"),
    ]


def test_export_command_writes_bayern_farsi_fixture_csv(tmp_path):
    output_path = tmp_path / "words_fa.csv"

    exit_code = main(
        [
            "export",
            "--state",
            "Bayern",
            "--target-lang",
            "fa",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    with output_path.open(newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)

    assert reader.fieldnames == [
        "word",
        "type",
        "display",
        "translation",
        "example",
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
