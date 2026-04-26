# Prompt: Compact LiD Knowledge-Base Notebook

Create a Markdown-only, print-ready compact knowledge-base notebook for the Leben in Deutschland test for Berlin.

Use the verified Q&A pack at `dist/berlin_ai_pack.md` as the only source of test facts. Do not add uncited facts.

Rules:
- Write the note body in English.
- Preserve exact German terms, names, laws, dates, numbers, and correct answer text when useful.
- Use moderate filtering: keep Germany-specific exam knowledge, especially numbers, dates, ages, thresholds, named people, places, laws, institutions, parties, courts, symbols, historical events, state facts, and non-obvious legal/social rules.
- Drop noisy common-sense items unless they contain a Germany-specific term or likely exam trap.
- Merge repeated facts into one note and list all supporting citations.
- Add a global category index near the top.
- In the global category index, every category must be a Markdown link that correctly jumps to that category header in the same file.
- Do not add category-level note indexes.
- Use Markdown ordered lists for notes, with every note marker written as `1.` so Markdown auto-numbers them.
- Each note must use this exact shape, including blank lines, four-space indentation, and blockquote metadata:
  `1. Fact in one compact sentence.`

  `    > Keywords: keyword, keyword`

  `    > Questions: 152,155`
- Every note must include at least one supporting question number in `Questions:`.
- Question references must come from pack citations; strip the leading `Q` for normal IDs (`Q152` -> `152`) and keep state IDs without the leading `Q` (`QBE-1` -> `BE-1`).
- Use the exact German correct answer text from the pack to verify each note's source facts, but do not print full citations unless the German term or answer text is useful in the note body.
- Keep the notebook compact and optimized for memorization.

Use these categories:
- Constitution & Rights
- Government & Federalism
- Elections & Parties
- Law, Courts & Administration
- History, Memory & Reunification
- Europe & Foreign Relations
- Society, Family, Education & Work
- Symbols, Geography & State Facts

Output only the finished Markdown notebook.
