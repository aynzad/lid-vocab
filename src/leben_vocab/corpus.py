from dataclasses import dataclass


@dataclass(frozen=True)
class AnswerOption:
    id: str
    text: str
    is_image_only: bool = False


@dataclass(frozen=True)
class Question:
    id: str
    state: str | None
    text: str
    options: tuple[AnswerOption, ...]


class FixtureCorpusProvider:
    def load_questions(self, state: str) -> list[Question]:
        state_code = _state_code(state)
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
                id=f"{state_code}-1",
                state=state,
                text="Berlin hat ein Parlament.",
                options=(
                    AnswerOption(id="a", text="Wahl"),
                    AnswerOption(id="b", text="See"),
                ),
            ),
        ]


def _state_code(state: str) -> str:
    return {
        "Bayern": "BY",
        "Berlin": "BE",
    }.get(state, state[:2].upper())
