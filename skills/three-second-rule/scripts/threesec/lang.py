from __future__ import annotations

import re
from functools import lru_cache
from typing import Optional

from .common import DATA_DIR, read_json

WORD = re.compile(r"[\w']+(?:-[\w']+)*", re.UNICODE)
MIN_STOPWORD_HITS = 3
SHORT_TEXT_WORDS = 12


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


def guess(text: str, short: bool = False) -> Optional[str]:
    words = set(tokens(text))
    if not words:
        return None
    scores = {code: len(words & set(body["stopwords"])) for code, body in languages().items()}
    best = max(scores, key=scores.get)
    ranked = sorted(scores.values(), reverse=True)
    needed = 1 if short and len(tokens(text)) <= SHORT_TEXT_WORDS else MIN_STOPWORD_HITS
    if scores[best] < needed or (len(ranked) > 1 and ranked[0] == ranked[1]):
        return None
    return best


def matching(text: str) -> Optional[dict]:
    hits = []
    for body in languages().values():
        phrases = body["welcome"] + body["subscribe"] + body["vague_teases"]
        if found(text, phrases) or any(starts_with(text, f) for f in body["filler_openers"]):
            hits.append(body)
    return hits[0] if len(hits) == 1 else None


def asks(text: str, language: dict) -> dict[str, list[str]]:
    result = {}
    for kind, phrases in language.get("asks", {}).items():
        hits = found(text, phrases)
        if hits:
            result[kind] = hits
    return result
