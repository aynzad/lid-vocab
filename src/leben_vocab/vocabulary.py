from dataclasses import dataclass, field, replace
import re
from typing import Any

from leben_vocab.answers import AnswerKey
from leben_vocab.corpus import Question


@dataclass(frozen=True)
class VocabularyItem:
    word: str
    kind: str
    display: str
    translation: str
    example: str | None
    example_source: str
    question_id: str
    count: int

    def __post_init__(self) -> None:
        if self.example is None:
            object.__setattr__(self, "example", "")

    def with_translation(self, translation: str) -> "VocabularyItem":
        return replace(self, translation=translation)


@dataclass(frozen=True)
class NormalizedToken:
    word: str
    kind: str
    display: str


@dataclass(frozen=True)
class AnalyzedToken:
    text: str
    lemma: str
    pos: str


class SpacyGermanAnalyzer:
    def __init__(self, model: Any | None = None) -> None:
        self._model = model or self._load_model()

    def analyze(self, token: str) -> AnalyzedToken | None:
        if self._model is None:
            return None
        document = self._model(token)
        if not document:
            return None
        parsed = document[0]
        if not getattr(parsed, "is_alpha", True):
            return None
        return AnalyzedToken(
            text=getattr(parsed, "text", token),
            lemma=(getattr(parsed, "lemma_", "") or token).lower(),
            pos=getattr(parsed, "pos_", ""),
        )

    def analyze_text(self, text: str) -> list[AnalyzedToken] | None:
        if self._model is None:
            return None
        return [
            AnalyzedToken(
                text=getattr(token, "text", ""),
                lemma=(getattr(token, "lemma_", "") or getattr(token, "text", "")).lower(),
                pos=getattr(token, "pos_", ""),
            )
            for token in self._model(text)
            if getattr(token, "is_alpha", True)
        ]

    @staticmethod
    def _load_model() -> Any | None:
        try:
            import spacy
        except ImportError:
            return None

        for model_name in ("de_core_news_lg", "de_core_news_md", "de_core_news_sm"):
            try:
                return spacy.load(model_name)
            except OSError:
                continue
        return None


@dataclass(frozen=True)
class NounForm:
    lemma: str
    article: str | None
    plural: str | None


class GermanNounLookup:
    def __init__(self, nouns: Any | None = None) -> None:
        self._nouns = nouns if nouns is not None else self._load_nouns()

    def lookup(self, token: str) -> NounForm | None:
        if self._nouns is None:
            return None
        if isinstance(self._nouns, dict):
            entry = self._nouns.get(token.lower()) or self._nouns.get(token)
            return _noun_form_from_mapping(entry) if entry else None

        for candidate in _noun_candidates(token):
            try:
                entries = self._nouns[candidate]
            except (KeyError, TypeError):
                continue
            if entries:
                return _noun_form_from_german_nouns_entry(
                    _best_german_nouns_entry(entries)
                )
        return None

    def compound_parts(self, token: str) -> list[str]:
        if self._nouns is None or isinstance(self._nouns, dict):
            return []
        parse_compound = getattr(self._nouns, "parse_compound", None)
        if parse_compound is None:
            return []
        try:
            parts = parse_compound(token)
        except (KeyError, TypeError):
            return []
        if len(parts) < 2:
            return []
        return parts

    @staticmethod
    def _load_nouns() -> Any | None:
        try:
            from german_nouns.lookup import Nouns
        except ImportError:
            return None
        return Nouns()


@dataclass
class GermanVocabularyNormalizer:
    analyzer: SpacyGermanAnalyzer | None = None
    noun_lookup: GermanNounLookup | None = None
    verb_lemmas: dict[str, str] = field(default_factory=dict)
    noun_forms: dict[str, tuple[str | None, str, str | None]] = field(
        default_factory=lambda: {
            "demokratie": (None, "Demokratie", None),
            "wahl": (None, "Wahl", None),
        }
    )
    include_unknown: bool = False
    _cache: dict[tuple[str, str | None, str | None], tuple[str, str, str] | None] = field(default_factory=dict)

    def normalize(self, token: str) -> tuple[str, str, str] | None:
        analyzed = self.analyzer.analyze(token) if self.analyzer else None
        return self._normalize_token(token, analyzed)

    def normalize_text(self, text: str) -> list[tuple[str, str, str]]:
        analyzed_tokens = self.analyzer.analyze_text(text) if self.analyzer else None
        tokens = analyzed_tokens or [
            AnalyzedToken(text=token, lemma="", pos="") for token in _tokens(text)
        ]
        normalizations: list[tuple[str, str, str]] = []
        for token in tokens:
            normalized = self._normalize_token(token.text, token)
            if normalized is None:
                continue
            normalizations.append(normalized)
            if (
                normalized[1] == "noun"
                and normalized[0] == token.text.lower()
                and len(token.text) >= 10
            ):
                normalizations.extend(
                    self._compound_part_normalizations(token.text, normalized[0])
                )
        return normalizations

    def _normalize_token(
        self, token: str, analyzed: AnalyzedToken | None
    ) -> tuple[str, str, str] | None:
        cache_key = (
            token,
            analyzed.lemma if analyzed and analyzed.lemma else None,
            analyzed.pos if analyzed and analyzed.pos else None,
        )
        if cache_key in self._cache:
            return self._cache[cache_key]
        normalized = token.lower()
        if analyzed and analyzed.pos in {"VERB", "AUX"}:
            return self._remember(cache_key, (analyzed.lemma, "verb", analyzed.lemma))

        verb = self.verb_lemmas.get(normalized)
        if verb is not None:
            return self._remember(cache_key, (verb, "verb", verb))

        noun = self.noun_lookup.lookup(token) if self.noun_lookup else None
        if noun is not None:
            return self._remember(
                cache_key,
                (
                    noun.lemma.lower(),
                    "noun",
                    _format_noun_display(noun.article, noun.lemma, noun.plural),
                ),
            )

        noun_form = self.noun_forms.get(normalized)
        if noun_form is not None:
            article, display, plural = noun_form
            return self._remember(
                cache_key,
                (normalized, "noun", _format_noun_display(article, display, plural)),
            )

        if self.include_unknown and len(normalized) > 2 and normalized not in STOPWORDS:
            lemma = analyzed.lemma if analyzed and analyzed.lemma else normalized
            return self._remember(cache_key, (lemma, "word", token))

        return self._remember(cache_key, None)

    def _compound_part_normalizations(
        self, token: str, normalized_word: str
    ) -> list[tuple[str, str, str]]:
        if self.noun_lookup is None:
            return []
        normalizations: list[tuple[str, str, str]] = []
        for part in self.noun_lookup.compound_parts(token):
            normalized = self.normalize(part)
            if normalized is not None and normalized[0] != normalized_word:
                normalizations.append(normalized)
        return normalizations

    def _remember(
        self,
        cache_key: tuple[str, str | None, str | None],
        normalized: tuple[str, str, str] | None,
    ) -> tuple[str, str, str] | None:
        self._cache[cache_key] = normalized
        return normalized


def extract_vocabulary(
    questions: list[Question],
    answer_keys: list[AnswerKey],
    normalizer: GermanVocabularyNormalizer | None = None,
) -> list[VocabularyItem]:
    normalizer = normalizer or GermanVocabularyNormalizer()
    correct_options = {
        answer.question_id: answer.correct_option_id for answer in answer_keys
    }
    counts: dict[str, VocabularyItem] = {}

    for question in questions:
        correct_option_id = correct_options[question.id]
        correct_option = next(
            option for option in question.options if option.id == correct_option_id
        )
        sources = [(question.text, "question")]
        if correct_option.text and not correct_option.is_image_only:
            sources.append((correct_option.text, "answer"))

        for text, source in sources:
            for normalized in normalizer.normalize_text(text):
                word, kind, display = normalized
                counts[word] = _record_item(
                    existing=counts.get(word),
                    word=word,
                    kind=kind,
                    display=display,
                    example=text,
                    example_source=source,
                    question_id=question.id,
                )

    return list(counts.values())


def _record_item(
    existing: VocabularyItem | None,
    word: str,
    kind: str,
    display: str,
    example: str,
    example_source: str,
    question_id: str,
) -> VocabularyItem:
    if existing is None:
        return VocabularyItem(
            word=word,
            kind=kind,
            display=display,
            translation="",
            example=example,
            example_source=example_source,
            question_id=question_id,
            count=1,
        )
    return replace(existing, count=existing.count + 1)


def _tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-zÄÖÜäöüß]+", text)


def _format_noun_display(
    article: str | None, display: str, plural: str | None
) -> str:
    if article and plural:
        return f"{article} {display}, {plural}"
    if article:
        return f"{article} {display}"
    return display


def _noun_form_from_mapping(entry: Any) -> NounForm:
    if isinstance(entry, NounForm):
        return entry
    if isinstance(entry, tuple):
        article, lemma, plural = entry
        return NounForm(lemma=lemma, article=article, plural=plural)
    return NounForm(
        lemma=entry["lemma"],
        article=entry.get("article"),
        plural=entry.get("plural"),
    )


def _noun_form_from_german_nouns_entry(entry: dict[str, Any]) -> NounForm:
    genus_to_article = {"m": "der", "f": "die", "n": "das"}
    flexion = entry.get("flexion", {})
    lemma = entry.get("lemma") or flexion.get("nominativ singular")
    return NounForm(
        lemma=lemma,
        article=genus_to_article.get(entry.get("genus")),
        plural=flexion.get("nominativ plural"),
    )


def _best_german_nouns_entry(entries: list[dict[str, Any]]) -> dict[str, Any]:
    def score(entry: dict[str, Any]) -> tuple[int, int]:
        flexion = entry.get("flexion", {})
        return (
            int(bool(entry.get("genus"))) + int(bool(flexion.get("nominativ singular"))),
            int(bool(flexion.get("nominativ plural"))),
        )

    return max(entries, key=score)


def _noun_candidates(token: str) -> list[str]:
    stripped = token.strip()
    return list(
        dict.fromkeys(
            [
                stripped,
                stripped.capitalize(),
                stripped.title(),
            ]
        )
    )


STOPWORDS = {
    "aber",
    "alle",
    "als",
    "am",
    "an",
    "auch",
    "auf",
    "aus",
    "bei",
    "bis",
    "das",
    "den",
    "der",
    "des",
    "die",
    "dies",
    "diese",
    "diesem",
    "diesen",
    "dieser",
    "dieses",
    "ein",
    "eine",
    "einem",
    "einen",
    "einer",
    "eines",
    "er",
    "für",
    "hat",
    "hier",
    "ich",
    "im",
    "in",
    "ist",
    "man",
    "mit",
    "nicht",
    "oder",
    "sich",
    "sie",
    "sind",
    "und",
    "von",
    "vor",
    "was",
    "weil",
    "wer",
    "wie",
    "wo",
    "zu",
    "zum",
    "zur",
}
