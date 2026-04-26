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
.venv/bin/lid-vocab export --state Berlin --target-lang en --output words_en.csv
```

Export English and Farsi translations in the same CSV cell, in that order:

```sh
.venv/bin/lid-vocab export --state Berlin --target-lang en,fa --output words_en_fa.csv
```

By default, exports keep only rows with a count of 2 or higher. Use
`--min-count` to make the list shorter or pass `--min-count 1` to keep
singletons:

```sh
.venv/bin/lid-vocab export --state Berlin --target-lang en,fa --output words_en_fa.csv --min-count 3
```

Export a Farsi CSV for Bayern:

```sh
.venv/bin/lid-vocab export --state Bayern --target-lang fa --output words_fa.csv
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

## Build a Compact Knowledge-Base Notebook

The notebook workflow is review-first. The local `lid2026.pdf` is still the
canonical source for question wording and answer options, but the generated
notebook pack only trusts a reviewed answer JSON file. This avoids silently
using an answer source whose numbering or wording no longer matches the PDF.

Seed a reviewed-answer file and a human review checklist:

```sh
.venv/bin/lid-vocab qa-seed \
  --state Berlin \
  --output data/answers-reviewed.json \
  --review-md dist/berlin_answer_review.md
```

The JSON records include:

```text
question_id,state,question,options,seed_correct_option_id,seed_correct_answer_text,match_method,match_confidence,needs_review,review_status
```

Review `dist/berlin_answer_review.md`, correct any seeded answer in
`data/answers-reviewed.json`, and set each accepted record to:

```json
"review_status": "reviewed"
```

After every selected question is reviewed, create the AI-readable pack and the
ready-to-use notebook prompt:

```sh
.venv/bin/lid-vocab notebook-pack \
  --state Berlin \
  --answers data/answers-reviewed.json \
  --output dist/berlin_ai_pack.md \
  --prompt dist/berlin_notebook_prompt.md
```

`notebook-pack` fails if any selected question is missing, duplicated,
unreviewed, or points to an invalid answer option. The generated prompt asks
the AI to create a Markdown-only, print-ready notebook with compact English
notes, German answer citations such as `Q152: 1933 bis 1945`, keywords, stable
note numbers, a global category index, and category-level indexes.

## Run Tests

```sh
.venv/bin/python -m pytest
```

## Development Notes

- Source code lives in `src/leben_vocab`.
- Tests live in `tests`.
- Local environment files, caches, build output, and virtual environments are
  ignored by git.
