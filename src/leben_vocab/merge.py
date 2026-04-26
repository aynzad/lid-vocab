from collections import defaultdict
from dataclasses import replace
from typing import Protocol

from leben_vocab.vocabulary import VocabularyItem


class CompoundPartLookup(Protocol):
    def compound_parts(self, token: str) -> list[str]:
        ...


def merge_related_items(
    items: list[VocabularyItem],
    compound_lookup: CompoundPartLookup | None = None,
) -> list[VocabularyItem]:
    by_word = {item.word: item for item in items}
    groups: dict[str, list[VocabularyItem]] = defaultdict(list)

    for item in items:
        groups[_merge_target(item, by_word, compound_lookup)].append(item)

    return [_merge_group(target, group) for target, group in groups.items()]


def _merge_target(
    item: VocabularyItem,
    by_word: dict[str, VocabularyItem],
    compound_lookup: CompoundPartLookup | None,
) -> str:
    return (
        _gender_pair_target(item, by_word)
        or _inflected_word_target(item, by_word)
        or _compound_target(item, by_word, compound_lookup)
        or item.word
    )


def _gender_pair_target(
    item: VocabularyItem, by_word: dict[str, VocabularyItem]
) -> str | None:
    if item.kind != "noun" or not item.word.endswith("in"):
        return None
    base_word = item.word.removesuffix("in")
    base = by_word.get(base_word)
    if base is None or base.kind != item.kind:
        return None
    return base.word


def _inflected_word_target(
    item: VocabularyItem, by_word: dict[str, VocabularyItem]
) -> str | None:
    if item.kind != "word":
        return None
    for suffix in ("en", "er", "es", "em", "e"):
        if not item.word.endswith(suffix):
            continue
        base_word = item.word[: -len(suffix)]
        base = by_word.get(base_word)
        if base is not None and base.kind == item.kind:
            return base.word
    return None


def _compound_target(
    item: VocabularyItem,
    by_word: dict[str, VocabularyItem],
    compound_lookup: CompoundPartLookup | None,
) -> str | None:
    if compound_lookup is None or item.kind != "noun" or len(item.word) < 10:
        return None

    candidates = [
        by_word[part.lower()]
        for part in compound_lookup.compound_parts(_display_head(item.display))
        if part.lower() in by_word and part.lower() != item.word
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda candidate: (-candidate.count, candidate.word))
    return candidates[0].word


def _display_head(display: str) -> str:
    head = display.split(",", 1)[0].strip()
    for article in ("der ", "die ", "das "):
        if head.startswith(article):
            return head[len(article) :]
    return head


def _merge_group(target: str, group: list[VocabularyItem]) -> VocabularyItem:
    base = next((item for item in group if item.word == target), group[0])
    return replace(base, count=sum(item.count for item in group))
