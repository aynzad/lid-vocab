# Leben Vocab

Export vocabulary study CSVs for the German "Leben in Deutschland" question
catalog.

The current CLI uses deterministic fixture providers for export smoke runs while
the project modules cover the official BAMF PDF parser, answer matching,
vocabulary extraction, translation routing, caching, and CSV writing.

## Requirements

- Python 3.11 or newer
- The committed `lid2026.pdf` file in the repository root

## Setup

Create a virtual environment and install the package with test dependencies:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e '.[dev]'
```

## Run the CLI

Export an English CSV for Berlin:

```sh
.venv/bin/leben-vocab export --state Berlin --target-lang en --output dist/words_en.csv
```

Export a Farsi CSV for Bayern:

```sh
.venv/bin/leben-vocab export --state Bayern --target-lang fa --output dist/words_fa.csv
```

Generated CSV files should be written under `dist/`. That folder is ignored by
git, so local exports do not show up as source changes.

CSV output columns are:

```text
word,type,display,translation,example,example_source,question_id,count,target_language
```

Rows are sorted by `count` descending, and every row includes the requested
target language.

## Run Tests

```sh
.venv/bin/python -m pytest
```

## Development Notes

- Source code lives in `src/leben_vocab`.
- Tests live in `tests`.
- Local environment files, caches, build output, and virtual environments are
  ignored by git.
