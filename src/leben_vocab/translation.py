from collections.abc import Mapping
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

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


class JsonTranslationCache(TranslationCache):
    def __init__(self, path: Path) -> None:
        self.path = path
        super().__init__(_values=self._load())

    def set(
        self,
        word: str,
        kind: str,
        target_language: str,
        provider_name: str,
        translation: str,
    ) -> None:
        super().set(word, kind, target_language, provider_name, translation)
        self._save()

    def _load(self) -> dict[tuple[str, str, str, str], str]:
        if not self.path.exists():
            return {}
        raw_values = json.loads(self.path.read_text(encoding="utf-8"))
        return {tuple(key.split("\t")): value for key, value in raw_values.items()}

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        raw_values = {
            "\t".join(key): value for key, value in sorted(self._values.items())
        }
        self.path.write_text(
            json.dumps(raw_values, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )


@dataclass
class TranslationRouter:
    deepl_provider: TranslationProvider
    fallback_provider: TranslationProvider
    cache: TranslationCache = field(default_factory=TranslationCache)

    def translate_item(
        self, item: VocabularyItem, target_language: str
    ) -> VocabularyItem:
        providers = self._providers_for(target_language)
        for provider in providers:
            cached = self.cache.get(
                item.word, item.kind, target_language, provider.name
            )
            if cached is not None:
                return item.with_translation(cached)

        errors: list[str] = []
        for provider in providers:
            try:
                translation = provider.translate(item.word, target_language)
            except TranslationUnavailableError as error:
                errors.append(f"{provider.name}: {error}")
                continue
            if not translation:
                errors.append(f"{provider.name}: empty response")
                continue

            self.cache.set(
                item.word,
                item.kind,
                target_language,
                provider.name,
                translation,
            )
            return item.with_translation(translation)

        detail = "; ".join(errors)
        if detail:
            detail = f" ({detail})"
        raise TranslationUnavailableError(
            f"Translation unavailable for {item.word!r}{detail}"
        )

    def translate_items(
        self, items: list[VocabularyItem], target_language: str
    ) -> list[VocabularyItem]:
        return [self.translate_item(item, target_language) for item in items]

    def _providers_for(self, target_language: str) -> list[TranslationProvider]:
        if target_language == "en":
            return [self.deepl_provider, self.fallback_provider]
        return [self.fallback_provider]


def load_deepl_api_key(env: Mapping[str, str] | None = None) -> str | None:
    values = env or {**_load_dotenv_values(Path(".env")), **os.environ}
    return values.get("DEEPL_API_KEY") or values.get("deepl_api_key")


def build_production_translation_router() -> TranslationRouter:
    return TranslationRouter(
        deepl_provider=DeepLTranslationProvider(load_deepl_api_key()),
        fallback_provider=FallbackTranslationProvider(),
        cache=JsonTranslationCache(Path("data/translation-cache.json")),
    )


class DeepLTranslationProvider:
    name = "deepl"

    def __init__(self, api_key: str | None) -> None:
        self.api_key = api_key

    def translate(self, word: str, target_language: str) -> str | None:
        if not self.api_key:
            raise TranslationUnavailableError(
                "DEEPL_API_KEY or deepl_api_key is required for English exports"
            )

        request = Request(
            "https://api-free.deepl.com/v2/translate",
            data=json.dumps(
                {
                    "text": [word],
                    "source_lang": "DE",
                    "target_lang": _deepl_target_language(target_language),
                }
            ).encode("utf-8"),
            headers={
                "Authorization": f"DeepL-Auth-Key {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=30) as response:
                payload = json.load(response)
        except HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise TranslationUnavailableError(
                f"DeepL translation failed for {word!r}: HTTP {error.code} {detail}"
            ) from error
        except URLError as error:
            raise TranslationUnavailableError(
                f"DeepL translation failed for {word!r}: {error.reason}"
            ) from error

        translations = payload.get("translations") or []
        if not translations:
            return None
        return translations[0].get("text")


class FallbackTranslationProvider:
    name = "fallback"

    def translate(self, word: str, target_language: str) -> str | None:
        try:
            from deep_translator import GoogleTranslator

            return GoogleTranslator(source="de", target=target_language).translate(word)
        except Exception as error:
            raise TranslationUnavailableError(
                f"Fallback translation failed for {word!r}: {error}"
            ) from error


class FixtureTranslationProvider:
    name = "fixture"
    _translations = {
        ("demokratie", "en"): "democracy",
        ("wahl", "en"): "election",
    }

    def translate(self, word: str, target_language: str) -> str | None:
        return self._translations.get((word, target_language), f"{word}-{target_language}")


def _deepl_target_language(target_language: str) -> str:
    if target_language.lower() == "en":
        return "EN-US"
    return target_language.upper()


def _load_dotenv_values(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values
