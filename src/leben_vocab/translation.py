from collections.abc import Mapping
from dataclasses import dataclass, field
import os
from typing import Protocol

from leben_vocab.vocabulary import VocabularyItem


class TranslationProvider(Protocol):
    name: str

    def translate(self, word: str, target_language: str) -> str | None:
        ...


class TranslationUnavailableError(RuntimeError):
    pass


@dataclass
class TranslationCache:
    _values: dict[tuple[str, str, str, str], str] = field(default_factory=dict)

    def get(
        self, word: str, kind: str, target_language: str, provider_name: str
    ) -> str | None:
        return self._values.get((word, kind, target_language, provider_name))

    def set(
        self,
        word: str,
        kind: str,
        target_language: str,
        provider_name: str,
        translation: str,
    ) -> None:
        self._values[(word, kind, target_language, provider_name)] = translation


@dataclass
class TranslationRouter:
    deepl_provider: TranslationProvider
    fallback_provider: TranslationProvider
    cache: TranslationCache = field(default_factory=TranslationCache)

    def translate_item(
        self, item: VocabularyItem, target_language: str
    ) -> VocabularyItem:
        provider = self._provider_for(target_language)
        cached = self.cache.get(
            item.word, item.kind, target_language, provider.name
        )
        if cached is not None:
            return item.with_translation(cached)

        translation = provider.translate(item.word, target_language)
        if not translation:
            raise TranslationUnavailableError(
                f"Translation unavailable for {item.word!r} via {provider.name}"
            )

        self.cache.set(
            item.word,
            item.kind,
            target_language,
            provider.name,
            translation,
        )
        return item.with_translation(translation)

    def translate_items(
        self, items: list[VocabularyItem], target_language: str
    ) -> list[VocabularyItem]:
        return [self.translate_item(item, target_language) for item in items]

    def _provider_for(self, target_language: str) -> TranslationProvider:
        if target_language == "en":
            return self.deepl_provider
        return self.fallback_provider


def load_deepl_api_key(env: Mapping[str, str] | None = None) -> str | None:
    values = env or os.environ
    return values.get("DEEPL_API_KEY") or values.get("deepl_api_key")


class FixtureTranslationProvider:
    name = "fixture"
    _translations = {
        ("demokratie", "en"): "democracy",
        ("wahl", "en"): "election",
    }

    def translate(self, word: str, target_language: str) -> str | None:
        return self._translations.get((word, target_language), f"{word}-{target_language}")
