import pytest

from leben_vocab.translation import (
    TranslationCache,
    TranslationRouter,
    TranslationUnavailableError,
    load_deepl_api_key,
)
from leben_vocab.vocabulary import VocabularyItem
from leben_vocab.export import export_fixture_vocabulary


class RecordingProvider:
    def __init__(self, name, translations):
        self.name = name
        self.translations = translations
        self.calls = []

    def translate(self, word, target_language):
        self.calls.append((word, target_language))
        return self.translations.get((word, target_language))


def item(word="demokratie", kind="noun"):
    return VocabularyItem(
        word=word,
        kind=kind,
        display=word,
        translation="",
        example="example",
        example_source="question",
        question_id="1",
        count=1,
    )


def test_deepl_api_key_loads_from_env_with_uppercase_precedence():
    assert load_deepl_api_key({"deepl_api_key": "lower"}) == "lower"
    assert (
        load_deepl_api_key(
            {"DEEPL_API_KEY": "upper", "deepl_api_key": "lower"}
        )
        == "upper"
    )


def test_translation_router_sends_english_to_deepl_and_farsi_to_fallback():
    deepl = RecordingProvider("deepl", {("demokratie", "en"): "democracy"})
    fallback = RecordingProvider("fallback", {("demokratie", "fa"): "دموکراسی"})
    router = TranslationRouter(deepl_provider=deepl, fallback_provider=fallback)

    assert router.translate_item(item(), "en").translation == "democracy"
    assert router.translate_item(item(), "fa").translation == "دموکراسی"

    assert deepl.calls == [("demokratie", "en")]
    assert fallback.calls == [("demokratie", "fa")]


def test_translation_router_sends_other_non_english_languages_to_fallback():
    deepl = RecordingProvider("deepl", {})
    fallback = RecordingProvider("fallback", {("wahl", "tr"): "seçim"})
    router = TranslationRouter(deepl_provider=deepl, fallback_provider=fallback)

    translated = router.translate_item(item(word="wahl"), "tr")

    assert translated.translation == "seçim"
    assert deepl.calls == []
    assert fallback.calls == [("wahl", "tr")]


def test_translation_cache_key_includes_word_type_language_and_provider():
    cache = TranslationCache()

    cache.set("wahl", "noun", "en", "deepl", "election")

    assert cache.get("wahl", "noun", "en", "deepl") == "election"
    assert cache.get("wahl", "verb", "en", "deepl") is None
    assert cache.get("wahl", "noun", "fa", "deepl") is None
    assert cache.get("wahl", "noun", "en", "fallback") is None


def test_cached_translation_prevents_duplicate_provider_calls():
    deepl = RecordingProvider("deepl", {("demokratie", "en"): "democracy"})
    router = TranslationRouter(
        deepl_provider=deepl,
        fallback_provider=RecordingProvider("fallback", {}),
    )

    router.translate_item(item(), "en")
    router.translate_item(item(), "en")

    assert deepl.calls == [("demokratie", "en")]


def test_uncached_unavailable_translation_fails_export():
    router = TranslationRouter(
        deepl_provider=RecordingProvider("deepl", {}),
        fallback_provider=RecordingProvider("fallback", {}),
    )

    with pytest.raises(TranslationUnavailableError, match="demokratie"):
        router.translate_item(item(), "en")


def test_export_fails_when_required_translation_is_unavailable(tmp_path):
    router = TranslationRouter(
        deepl_provider=RecordingProvider("deepl", {}),
        fallback_provider=RecordingProvider("fallback", {}),
    )

    with pytest.raises(TranslationUnavailableError, match="demokratie"):
        export_fixture_vocabulary(
            state="Berlin",
            target_language="en",
            output_path=tmp_path / "words_en.csv",
            translation_provider=router,
        )
