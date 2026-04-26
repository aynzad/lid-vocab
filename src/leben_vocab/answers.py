from dataclasses import dataclass


@dataclass(frozen=True)
class AnswerKey:
    question_id: str
    correct_option_id: str


class FixtureAnswerProvider:
    def load_answer_keys(self) -> list[AnswerKey]:
        return [
            AnswerKey(question_id="1", correct_option_id="a"),
            AnswerKey(question_id="BE-1", correct_option_id="a"),
        ]
