from __future__ import annotations

import re
from functools import lru_cache
from typing import Optional

from .common import DATA_DIR, read_json

WORD = re.compile(r"[\w']+(?:-[\w']+)*", re.UNICODE)
MIN_STOPWORD_HITS = 3


@lru_cache(maxsize=None)
def languages() -> dict:
    found = {}
    for path in sorted((DATA_DIR / "lang").glob("*.json")):
        body = read_json(path)
        found[body["code"]] = body
    return found


def get(code: Optional[str]) -> Optional[dict]:
    if not code:
        return None
    return languages().get(code.split("-")[0].split("_")[0].lower())


def normalize(text: str) -> str:
    lowered = text.lower().replace("’", "'").replace("`", "'")
    return " ".join(WORD.findall(lowered))


def tokens(text: str) -> list[str]:
    return normalize(text).split()


def contains(text: str, phrase: str) -> bool:
    haystack = f" {normalize(text)} "
    needle = normalize(phrase)
    return bool(needle) and f" {needle} " in haystack


def starts_with(text: str, phrase: str) -> bool:
    needle = normalize(phrase)
    return bool(needle) and (normalize(text) + " ").startswith(needle + " ")


def found(text: str, phrases: list[str]) -> list[str]:
    return [p for p in phrases if contains(text, p)]


def guess(text: str) -> Optional[str]:
    words = set(tokens(text))
    if not words:
        return None
    scores = {code: len(words & set(body["stopwords"])) for code, body in languages().items()}
    best = max(scores, key=scores.get)
    ranked = sorted(scores.values(), reverse=True)
    if scores[best] < MIN_STOPWORD_HITS or (len(ranked) > 1 and ranked[0] == ranked[1]):
        return None
    return best


def asks(text: str, language: dict) -> dict[str, list[str]]:
    result = {}
    for kind, phrases in language.get("asks", {}).items():
        hits = found(text, phrases)
        if hits:
            result[kind] = hits
    return result
