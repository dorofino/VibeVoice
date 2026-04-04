import json

from desktop.config import HOTWORDS_FILE


class Hotwords:
    def __init__(self):
        self._words: list[str] = []
        self.load()

    def load(self):
        try:
            if HOTWORDS_FILE.exists():
                with open(HOTWORDS_FILE) as f:
                    self._words = json.load(f)
        except Exception:
            self._words = []

    def save(self):
        HOTWORDS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(HOTWORDS_FILE, "w") as f:
            json.dump(self._words, f, indent=2)

    @property
    def words(self) -> list[str]:
        return list(self._words)

    def add(self, word: str):
        word = word.strip()
        if word and word not in self._words:
            self._words.append(word)
            self.save()

    def remove(self, word: str):
        if word in self._words:
            self._words.remove(word)
            self.save()

    def clear(self):
        self._words = []
        self.save()
