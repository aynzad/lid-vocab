from dataclasses import dataclass, replace

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


def extract_vocabulary(
    questions: list[Question], answer_keys: list[AnswerKey]
) -> list[VocabularyItem]:
    correct_options = {
        answer.question_id: answer.correct_option_id for answer in answer_keys
    }
    counts: dict[str, VocabularyItem] = {}

    for question in questions:
        correct_option_id = correct_options[question.id]
        correct_option = next(
            option for option in question.options if option.id == correct_option_id
        )
        fixture_words = _fixture_words(question.text, correct_option.text)
        for word in fixture_words:
            existing = counts.get(word)
            if existing is None:
                counts[word] = VocabularyItem(
                    word=word,
                    kind="noun",
                    display=word.capitalize(),
                    translation="",
                    example=question.text,
                    example_source="fixture",
                    question_id=question.id,
                    count=1,
                )
            else:
                counts[word] = replace(existing, count=existing.count + 1)

    return list(counts.values())


def _fixture_words(question_text: str, correct_answer_text: str) -> list[str]:
    texts = [question_text.lower(), correct_answer_text.lower()]
    words: list[str] = []
    for text in texts:
        if "demokratie" in text:
            words.append("demokratie")
        if "wahl" in text:
            words.append("wahl")
    return words
