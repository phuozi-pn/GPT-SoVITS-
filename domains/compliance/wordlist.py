"""Load and match sensitive words from a configurable wordlist file."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path


def _default_wordlist_path() -> Path:
    return Path(__file__).resolve().parents[2] / "infra" / "compliance" / "sensitive_words.txt"


@lru_cache
def load_sensitive_words(path: str | None = None) -> frozenset[str]:
    wordlist = Path(path) if path else _default_wordlist_path()
    if not wordlist.is_file():
        return frozenset({"测试敏感词"})
    words: set[str] = set()
    for line in wordlist.read_text(encoding="utf-8").splitlines():
        word = line.strip()
        if not word or word.startswith("#"):
            continue
        words.add(word)
    return frozenset(words)


def find_sensitive_word(text: str, *, path: str | None = None) -> str | None:
    for word in load_sensitive_words(path):
        if word and word in text:
            return word
    return None


def reload_wordlist(path: str | None = None) -> frozenset[str]:
    load_sensitive_words.cache_clear()
    return load_sensitive_words(path)
