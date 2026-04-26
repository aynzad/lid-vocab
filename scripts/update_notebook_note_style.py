#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path


NOTE_RE = re.compile(r"^N\d{3}\. (.+)$")
QUESTION_RE = re.compile(r"\bQ([A-Z]+-\d+|\d+):")


class ConversionError(ValueError):
    pass


def convert_notebook_markdown(markdown: str) -> str:
    lines = markdown.splitlines()
    converted: list[str] = []
    note_count = 0
    index = 0
    skip_blank_after_category_index = False

    while index < len(lines):
        line = lines[index]

        if line.startswith("Index: [N"):
            skip_blank_after_category_index = True
            index += 1
            continue

        if skip_blank_after_category_index and line == "":
            skip_blank_after_category_index = False
            index += 1
            continue

        skip_blank_after_category_index = False

        note_match = NOTE_RE.match(line)
        if note_match:
            if index + 2 >= len(lines):
                raise ConversionError(f"Incomplete note block at line {index + 1}")

            keywords_line = lines[index + 1]
            citations_line = lines[index + 2]
            if not keywords_line.startswith("Keywords: "):
                raise ConversionError(f"Missing Keywords line after line {index + 1}")
            if not citations_line.startswith("Citations: "):
                raise ConversionError(f"Missing Citations line after line {index + 1}")

            questions = QUESTION_RE.findall(citations_line)
            if not questions:
                raise ConversionError(f"No question citations found at line {index + 3}")

            note_count += 1
            converted.extend(
                [
                    f"1. {note_match.group(1)}",
                    "",
                    f"    > {keywords_line}",
                    "",
                    f"    > Questions: {','.join(questions)}",
                ]
            )
            index += 3
            continue

        converted.append(line)
        index += 1

    if note_count == 0:
        already_converted = re.search(r"^1\. ", markdown, re.MULTILINE) and re.search(
            r"^    > Questions: ", markdown, re.MULTILINE
        )
        if already_converted:
            return markdown if markdown.endswith("\n") else markdown + "\n"
        raise ConversionError("No old-style notes found to convert")

    return "\n".join(converted).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Convert a generated LiD notebook from N###/Citations note blocks "
            "to ordered-list notes with blockquoted Keywords and Questions."
        )
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="dist/berlin_notebook.md",
        type=Path,
        help="Notebook Markdown file to update in place.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit with 1 if the file would change; do not write it.",
    )
    args = parser.parse_args()

    original = args.path.read_text(encoding="utf-8")
    converted = convert_notebook_markdown(original)

    if args.check:
        return 0 if converted == original else 1

    args.path.write_text(converted, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
