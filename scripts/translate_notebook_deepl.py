#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import string
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from leben_vocab.translation import load_deepl_api_key


CATEGORY_ANCHORS = {
    "Constitution & Rights": "constitution--rights",
    "Government & Federalism": "government--federalism",
    "Elections & Parties": "elections--parties",
    "Law, Courts & Administration": "law-courts--administration",
    "History, Memory & Reunification": "history-memory--reunification",
    "Europe & Foreign Relations": "europe--foreign-relations",
    "Society, Family, Education & Work": "society-family-education--work",
    "Symbols, Geography & State Facts": "symbols-geography--state-facts",
}

FA_CATEGORY_OVERRIDES = {
    "Europe & Foreign Relations": "اروپا و روابط خارجی",
}

FA_TEXT_FIXUPS = {
    "Europe": "اروپا",
    "European": "اروپایی",
}


class DeepLError(RuntimeError):
    pass


def collect_protected_terms(markdown: str, pack_markdown: str | None = None) -> list[str]:
    terms: set[str] = {"LiD", "Berlin"}
    for line in markdown.splitlines():
        if line.startswith("    > Keywords: "):
            for term in line.removeprefix("    > Keywords: ").split(","):
                cleaned = term.strip()
                if cleaned:
                    terms.add(cleaned)
    if pack_markdown:
        for match in re.finditer(r"^Citation: Q[^:]+: (.+)$", pack_markdown, re.M):
            cleaned = match.group(1).strip()
            if cleaned and len(cleaned) <= 100:
                terms.add(cleaned)
    filtered_terms = {
        term
        for term in terms
        if not re.fullmatch(r"[\d%.,:;/ -]+", term)
    }
    return sorted(filtered_terms, key=len, reverse=True)


def token_for_index(index: int) -> str:
    letters = string.ascii_uppercase
    value = index
    encoded = ""
    while True:
        encoded = letters[value % len(letters)] + encoded
        value = value // len(letters) - 1
        if value < 0:
            break
    return f"__{encoded}__"


def protect_terms(text: str, protected_terms: list[str]) -> tuple[str, dict[str, str]]:
    matching_terms = [term for term in protected_terms if term in text]
    if not matching_terms:
        return text, {}

    pattern = re.compile("|".join(re.escape(term) for term in matching_terms))
    replacements: dict[str, str] = {}
    parts: list[str] = []
    position = 0

    def replace(match: re.Match[str]) -> str:
        term = match.group(0)
        token = token_for_index(len(replacements))
        replacements[token] = term
        return token

    for match in pattern.finditer(text):
        parts.append(text[position : match.start()])
        parts.append(replace(match))
        position = match.end()
    parts.append(text[position:])
    return "".join(parts), replacements


def restore_terms(text: str, replacements: dict[str, str]) -> str:
    restored = text
    for token, term in replacements.items():
        restored = restored.replace(token, term)
    return restored


def apply_fa_fixups(text: str) -> str:
    fixed = text
    for source, target in FA_TEXT_FIXUPS.items():
        fixed = re.sub(rf"\b{re.escape(source)}\b", target, fixed)
    return fixed


def deepl_translate_batch(
    texts: list[str],
    api_key: str,
    source_lang: str,
    target_lang: str,
) -> list[str]:
    if not texts:
        return []

    data = urlencode(
        [
            ("text", text)
            for text in texts
        ]
        + [
            ("source_lang", source_lang),
            ("target_lang", target_lang),
            ("preserve_formatting", "1"),
        ]
    ).encode("utf-8")
    request = Request(
        "https://api-free.deepl.com/v2/translate",
        data=data,
        headers={"Authorization": f"DeepL-Auth-Key {api_key}"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=60) as response:
            payload = json.load(response)
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise DeepLError(f"DeepL HTTP {error.code}: {detail}") from error
    except URLError as error:
        raise DeepLError(f"DeepL request failed: {error.reason}") from error

    translations = payload.get("translations") or []
    if len(translations) != len(texts):
        raise DeepLError(
            f"DeepL returned {len(translations)} translations for {len(texts)} texts"
        )
    return [item["text"] for item in translations]


def translate_texts(
    texts: list[str], api_key: str, protected_terms: list[str], batch_size: int = 40
) -> list[str]:
    protected_texts: list[str] = []
    replacement_maps: list[dict[str, str]] = []
    for text in texts:
        protected, replacements = protect_terms(text, protected_terms)
        protected_texts.append(protected)
        replacement_maps.append(replacements)

    translated: list[str] = []
    for start in range(0, len(protected_texts), batch_size):
        batch = protected_texts[start : start + batch_size]
        translated.extend(deepl_translate_batch(batch, api_key, "EN", "FA"))

    return [
        apply_fa_fixups(restore_terms(text, replacements))
        for text, replacements in zip(translated, replacement_maps, strict=True)
    ]


def plan_translations(markdown: str) -> tuple[list[str], list[tuple[int, str, str]]]:
    texts: list[str] = []
    actions: list[tuple[int, str, str]] = []
    lines = markdown.splitlines()

    for index, line in enumerate(lines):
        if line.startswith("# "):
            actions.append((index, "heading1", line[2:]))
            texts.append(line[2:])
        elif line == "## Category Index":
            actions.append((index, "literal", "## فهرست دسته‌ها"))
        elif line.startswith("## "):
            heading = line[3:]
            if heading in CATEGORY_ANCHORS:
                actions.append((index, "category", heading))
                texts.append(heading)
            else:
                actions.append((index, "heading2", heading))
                texts.append(heading)
        elif line.startswith("- ["):
            match = re.match(r"- \[([^\]]+)\]\((#[^)]+)\)", line)
            if not match:
                continue
            actions.append((index, "link", match.group(2)))
            texts.append(match.group(1))
        elif line.startswith("1. "):
            actions.append((index, "note", line[3:]))
            texts.append(line[3:])
        elif line.startswith("    > Keywords: "):
            actions.append((index, "keywords", line.removeprefix("    > Keywords: ")))
        elif line.startswith("    > Questions: "):
            actions.append((index, "questions", line.removeprefix("    > Questions: ")))

    return texts, actions


def apply_translations(
    markdown: str, actions: list[tuple[int, str, str]], translations: list[str]
) -> str:
    lines = markdown.splitlines()
    translated_iter = iter(translations)
    output_lines: list[str] = []

    action_by_line = {index: (kind, value) for index, kind, value in actions}
    for index, line in enumerate(lines):
        action = action_by_line.get(index)
        if action is None:
            output_lines.append(line)
            continue

        kind, value = action
        if kind == "literal":
            output_lines.append(value)
        elif kind == "heading1":
            output_lines.append(f"# {next(translated_iter)}")
        elif kind == "heading2":
            output_lines.append(f"## {next(translated_iter)}")
        elif kind == "category":
            anchor = CATEGORY_ANCHORS[value]
            translated = next(translated_iter)
            output_lines.append(f'<a id="{anchor}"></a>')
            output_lines.append(f"## {FA_CATEGORY_OVERRIDES.get(value) or translated}")
        elif kind == "link":
            translated = next(translated_iter)
            english_label = next(
                (
                    category
                    for category, anchor in CATEGORY_ANCHORS.items()
                    if value == f"#{anchor}"
                ),
                "",
            )
            output_lines.append(
                f"- [{FA_CATEGORY_OVERRIDES.get(english_label) or translated}]({value})"
            )
        elif kind == "note":
            output_lines.append(f"1. {next(translated_iter)}")
        elif kind == "keywords":
            output_lines.append(f"    > کلیدواژه‌ها: {value}")
        elif kind == "questions":
            output_lines.append(f"    > پرسش‌ها: {value}")
        else:
            output_lines.append(line)

    return "\n".join(output_lines).rstrip() + "\n"


def translate_notebook(
    markdown: str, api_key: str, pack_markdown: str | None = None
) -> str:
    protected_terms = collect_protected_terms(markdown, pack_markdown)
    texts, actions = plan_translations(markdown)
    translations = translate_texts(texts, api_key, protected_terms)
    return apply_translations(markdown, actions, translations)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Translate the generated English LiD notebook to Persian with DeepL."
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=Path("dist/berlin_notebook_en.md"),
        type=Path,
        help="English notebook Markdown input.",
    )
    parser.add_argument(
        "--output",
        default=Path("dist/berlin_notebook_fa.md"),
        type=Path,
        help="Persian notebook Markdown output.",
    )
    parser.add_argument(
        "--pack",
        default=Path("dist/berlin_ai_pack.md"),
        type=Path,
        help="Verified pack used only to protect exact German answer text.",
    )
    args = parser.parse_args()

    api_key = load_deepl_api_key()
    if not api_key:
        raise DeepLError("DEEPL_API_KEY or deepl_api_key is required")

    markdown = args.input.read_text(encoding="utf-8")
    pack_markdown = args.pack.read_text(encoding="utf-8") if args.pack.exists() else None
    translated = translate_notebook(markdown, api_key, pack_markdown)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(translated, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
