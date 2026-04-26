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

The project installs the large spaCy German model package used by the exporter.
If you need to install or refresh it manually:

```sh
.venv/bin/python -m pip install 'de-core-news-lg @ https://github.com/explosion/spacy-models/releases/download/de_core_news_lg-3.8.0/de_core_news_lg-3.8.0-py3-none-any.whl'
```

The exporter loads `de_core_news_lg`, `de_core_news_md`, or `de_core_news_sm`
when available and uses spaCy lemmas to collapse verb forms such as `wählt`
and `wählen`. It also uses `german-nouns` for noun article/plural display.
On Python 3.14, install the packaged noun data without its parser dependency:

```sh
.venv/bin/python -m pip install --no-deps german-nouns==1.2.5
```

The exporter still runs if `german-nouns` is unavailable; noun display then
falls back to the observed token or the small built-in fallback map.

## Run the CLI

For English exports, configure a DeepL API key in your shell or `.env` file to
use DeepL as the primary provider:

```sh
DEEPL_API_KEY=your-key-here
```

The existing lowercase `deepl_api_key` name is also supported, but
`DEEPL_API_KEY` takes precedence when both are set.
If DeepL is unavailable or rate-limited, the exporter falls back to the
`deep-translator` provider and records the successful provider in the cache.

Export an English CSV for Berlin:

```sh
.venv/bin/leben-vocab export --state Berlin --target-lang en --output words_en.csv
```

Export English and Farsi translations in the same CSV cell, in that order:

```sh
.venv/bin/leben-vocab export --state Berlin --target-lang en,fa --output words_en_fa.csv
```

Export a Farsi CSV for Bayern:

```sh
.venv/bin/leben-vocab export --state Bayern --target-lang fa --output words_fa.csv
```

Generated CSV files are written under `dist/`. If `--output` is a relative file
name such as `words_en.csv`, the CLI writes `dist/words_en.csv`. The `dist/`
folder is ignored by git, so local exports do not show up as source changes.
While the export runs, the CLI prints progress messages to stderr for corpus
parsing, state selection, answer matching, vocabulary extraction, translation,
and CSV writing.

Each export also writes a step log under `dist/logs/<output-name>.jsonl`.
The log records counts for parsing, state selection, answer loading, answer
matching, vocabulary extraction, translation, the translation providers used,
and CSV writing. For example:

```sh
sed -n '1,20p' dist/logs/words_en.jsonl
```

Translations are cached in `data/translation-cache.json`. Unlike generated CSVs
and logs, this cache is intended to be committed so future exports can reuse
known translations without calling providers again.

CSV output columns are:

```text
word,display,translation,example,type,example_source,question_id,count,target_language
```

Rows are sorted by `count` descending. Counts are based on normalized forms, so
verb conjugations, noun plurals/cases, and detected noun compound parts count
toward the same lemma. Every row includes the requested target language list.
When multiple target languages are requested, the `translation` cell contains
translations in the same order, separated by ` , `, for example
`to live , زندگی کردن`.

## Run Tests

```sh
.venv/bin/python -m pytest
```

## Development Notes

- Source code lives in `src/leben_vocab`.
- Tests live in `tests`.
- Local environment files, caches, build output, and virtual environments are
  ignored by git.
