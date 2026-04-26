from dataclasses import dataclass


@dataclass(frozen=True)
class AnswerOption:
    id: str
    text: str


@dataclass(frozen=True)
class Question:
    id: str
    state: str | None
    text: str
    options: tuple[AnswerOption, ...]


class FixtureCorpusProvider:
    def load_questions(self, state: str) -> list[Question]:
        return [
            Question(
                id="1",
                state=None,
                text="Deutschland ist eine Demokratie.",
                options=(
                    AnswerOption(id="a", text="Demokratie"),
                    AnswerOption(id="b", text="Monarchie"),
                ),
            ),
            Question(
                id="BE-1",
                state=state,
                text="Berlin hat ein Parlament.",
                options=(
                    AnswerOption(id="a", text="Wahl"),
                    AnswerOption(id="b", text="See"),
                ),
            ),
        ]
