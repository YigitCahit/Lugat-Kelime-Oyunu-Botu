from __future__ import annotations

import re
from typing import Optional

_ALLOWED_WORD_RE = re.compile(r"^[a-zc\u00e7g\u011fi\u0131jklmno\u00f6prs\u015ftu\u00fcvyz]+$")
_TR_LOWER_TABLE = str.maketrans({"I": "\u0131", "\u0130": "i"})


def to_turkish_lower(text: str) -> str:
    """Converts text to lowercase with Turkish I/i rules."""
    return text.translate(_TR_LOWER_TABLE).lower()


def normalize_word(raw_text: str, min_length: int = 2) -> Optional[str]:
    """Normalizes user input and returns a valid one-word token or None."""
    word = to_turkish_lower(raw_text.strip())

    if not word:
        return None
    if len(word.split()) != 1:
        return None
    if len(word) < min_length:
        return None
    if not _ALLOWED_WORD_RE.fullmatch(word):
        return None

    return word
