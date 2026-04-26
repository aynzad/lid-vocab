class FixtureTranslationProvider:
    _translations = {
        ("demokratie", "en"): "democracy",
        ("wahl", "en"): "election",
    }

    def translate(self, word: str, target_language: str) -> str:
        return self._translations.get((word, target_language), f"{word}-{target_language}")
