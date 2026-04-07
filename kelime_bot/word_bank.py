from __future__ import annotations

import random
from pathlib import Path

from .text_utils import normalize_word


class WordBank:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.words: set[str] = set()
        self._random_words: tuple[str, ...] = ()

    def load(self) -> None:
        if not self.directory.exists():
            raise FileNotFoundError(f"Kelime listesi klasoru bulunamadi: {self.directory}")

        files = sorted(self.directory.glob("*.list")) + sorted(self.directory.glob("*.txt"))
        if not files:
            raise FileNotFoundError(
                f"Kelime listesi dosyasi bulunamadi: {self.directory}"
            )

        loaded_words: set[str] = set()

        for file_path in files:
            with file_path.open("r", encoding="utf-8", errors="ignore") as file:
                for line in file:
                    word = normalize_word(line)
                    if word:
                        loaded_words.add(word)

        if not loaded_words:
            raise ValueError("Kelime listelerinden gecerli kelime okunamadi.")

        self.words = loaded_words
        self._random_words = tuple(loaded_words)

    def contains(self, word: str) -> bool:
        return word in self.words

    def random_word(self) -> str:
        if not self._random_words:
            raise ValueError("Kelime bankasi henuz yuklenmedi.")
        return random.choice(self._random_words)

    @property
    def size(self) -> int:
        return len(self.words)
