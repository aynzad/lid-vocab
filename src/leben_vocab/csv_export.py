import csv
from pathlib import Path

from leben_vocab.vocabulary import VocabularyItem

CSV_COLUMNS = [
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


def write_vocabulary_csv(
    items: list[VocabularyItem], target_language: str, output_path: Path
) -> None:
    rows = sorted(items, key=lambda item: (-item.count, item.word))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for item in rows:
            writer.writerow(
                {
                    "word": item.word,
                    "type": item.kind,
                    "display": item.display,
                    "translation": item.translation,
                    "example": item.example,
                    "example_source": item.example_source,
                    "question_id": item.question_id,
                    "count": item.count,
                    "target_language": target_language,
                }
            )
