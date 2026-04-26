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


def _merge_group(target: str, group: list[VocabularyItem]) -> VocabularyItem:
    base = next((item for item in group if item.word == target), group[0])
    return replace(base, count=sum(item.count for item in group))
