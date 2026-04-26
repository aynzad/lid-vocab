from dataclasses import dataclass, field, replace
import re

from leben_vocab.answers import AnswerKey
from leben_vocab.corpus import Question


@dataclass(frozen=True)
class VocabularyItem:
    word: str
    kind: str
    display: str
    translation: str
    example: str
    example_source: str
    question_id: str
    count: int

    def with_translation(self, translation: str) -> "VocabularyItem":
        return replace(self, translation=translation)


@dataclass(frozen=True)
class GermanVocabularyNormalizer:
    verb_lemmas: dict[str, str] = field(default_factory=dict)
    noun_forms: dict[str, tuple[str | None, str, str | None]] = field(
        default_factory=lambda: {
            "demokratie": (None, "Demokratie", None),
            "wahl": (None, "Wahl", None),
        }
    )

    def normalize(self, token: str) -> tuple[str, str, str] | None:
        normalized = token.lower()
        verb = self.verb_lemmas.get(normalized)
        if verb is not None:
            return verb, "verb", verb

        noun = self.noun_forms.get(normalized)
        if noun is not None:
            article, display, plural = noun
            return normalized, "noun", _format_noun_display(article, display, plural)

        return None


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
            for token in _tokens(text):
                normalized = normalizer.normalize(token)
                if normalized is None:
                    continue
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
