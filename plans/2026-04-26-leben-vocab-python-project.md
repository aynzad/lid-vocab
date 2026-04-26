# Leben Vocab Python Project

## Summary
- Build a greenfield Python package in `/Users/aesfahani/Work/lid-vocab` with `src/leben_vocab` layout and CLI entry point `leben-vocab`.
- Use committed `/Users/aesfahani/Work/lid-vocab/lid2026.pdf` as the official BAMF source of question wording and options. No v1 download command.
- Use the MIT GitHub 460-question JSON as the default structured answer provider, pinned by commit, only for correct answer letters.
- Load DeepL credentials from `.env`; the existing key is named `deepl_api_key`, so config should support both `DEEPL_API_KEY` and `deepl_api_key`, with uppercase env taking precedence.

## Key Changes
- Add `pyproject.toml` with dependencies: `pymupdf`, `spacy`, `de-core-news-lg`, `german-nouns`, optional `HanTa`, `deepl`, `deep-translator`, `python-dotenv`, and `pytest`.
- Add `.gitignore` entries for `.env`, caches, build outputs, and virtualenvs so API keys are not committed.
- Implement:
  - BAMF PDF parser returning 460 official `Question` objects.
  - Pluggable `AnswerProvider`, with default pinned GitHub JSON provider and fixture provider for tests.
  - Answer matching by official number first, normalized/fuzzy text fallback second, with an audit/failure if selected questions cannot be matched confidently.
  - State filtering: default `Berlin`; corpus size is 300 general + 10 selected-state questions.
  - Vocabulary extraction only from question text and correct answer text.
  - Verb normalization to infinitive lemma via spaCy.
  - Noun formatting via `german-nouns`, with best-effort article/plural fallback when incomplete.
  - Translation cache keyed by normalized word/type/target language/provider.
- CLI:
  - `leben-vocab export --state Berlin --target-lang en --output words_en.csv`
  - `leben-vocab export --state Bayern --target-lang fa --output words_fa.csv`

## Public Contracts
- CSV columns exactly: `word,type,display,translation,example,example_source,question_id,count,target_language`.
- Rows sorted by `count` descending.
- Internal item shape includes `word`, `type`, `display`, `count`, `translations`, and one `example` with `source`, `text`, `question_id`.
- `question_id` uses BAMF numbering: `1..300` for general, state-prefixed IDs like `BE-1..BE-10`.

## Test Plan
- Use fixtures, not live downloads or live translation APIs.
- Validate:
  - Full `lid2026.pdf` parse returns 460 questions.
  - Berlin selection returns 310 questions.
  - Correct answer mapping works by number and fuzzy text fallback.
  - Incorrect answer options are excluded.
  - Verb lemmatization and noun display formatting.
  - English routes to DeepL; Farsi/other targets route to GoogleTranslator.
  - `.env` loading supports existing lowercase `deepl_api_key`.
  - Translation cache prevents duplicate provider calls.
  - CSV structure and count-descending sorting.
- Add CLI smoke tests with temp output paths and mocked providers.

## Assumptions
- `lid2026.pdf` remains committed as the canonical v1 official source.
- BAMF PDF wording always wins over third-party wording.
- Image-only options contribute no answer vocabulary, but their question text is still processed.
- Exports fail if translation is unavailable and not cached.
