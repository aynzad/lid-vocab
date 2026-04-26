from dataclasses import dataclass
from pathlib import Path

from leben_vocab.vocabulary import VocabularyItem


DEFAULT_BLACKLIST_PATH = Path("data/vocabulary-blacklist.txt")


@dataclass(frozen=True)
class VocabularyBlacklist:
    words: frozenset[str]
    source_path: Path | None = None

    @classmethod
    def from_path(cls, path: Path = DEFAULT_BLACKLIST_PATH) -> "VocabularyBlacklist":
        if not path.exists():
            return cls(frozenset(), source_path=path)
        return cls(_parse_blacklist(path.read_text(encoding="utf-8")), source_path=path)

    def contains(self, item: VocabularyItem) -> bool:
        return item.word.lower() in self.words


def filter_blacklisted_items(
    items: list[VocabularyItem], blacklist: VocabularyBlacklist
) -> list[VocabularyItem]:
    return [item for item in items if not blacklist.contains(item)]


def _parse_blacklist(content: str) -> frozenset[str]:
    words: set[str] = set()
    for raw_line in content.splitlines():
        line = raw_line.split("#", 1)[0].strip().lower()
        if line:
            words.add(line)
    return frozenset(words)
