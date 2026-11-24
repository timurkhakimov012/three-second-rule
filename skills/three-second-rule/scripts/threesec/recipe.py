from __future__ import annotations

from pathlib import Path
from typing import Any

from .common import TsrError, read_json

BEAT_KINDS = ("hook", "setup", "turn", "proof", "payoff", "ask", "loop")
DEFAULT_TOLERANCE = {"length_pct": 10, "cut_s": 0.25, "cuts_per_10s": 1.0, "words_per_minute_pct": 15}

TEMPLATE: dict[str, Any] = {
    "schema": "tsr/recipe@1",
    "id": "short-kebab-id",
    "name": "Human name of the format",
    "container": {"hook": "what the first 3 s do", "structure": "the beats in words", "look": "camera, text, setting",
                  "length": "e.g. 20-25 s"},
    "length_s": 22.0,
    "cuts_per_10s": 3.0,
    "words_per_minute": None,
    "beats": [
        {"at": 0.0, "what": "hook", "text": "the result on frame 0, the stake as text", "cut": False},
        {"at": 2.2, "what": "turn", "text": "the first step, on a hard cut", "cut": True},
        {"at": 18.0, "what": "payoff", "text": "the result again, now explained", "cut": True},
    ],
    "hook_pattern": "e.g. Result first: the finished thing, then 'here is how'",
    "text_style": "e.g. 4 words, white on black box, upper third",
    "sound": "e.g. voice over a low beat, beat drop on the turn",
    "ask": "e.g. none, or 'comment SETUP'",
    "evidence": {"from_posts": ["post ids the beats were seen on"], "measured": "videos/<id>/probe.json"},
    "do_not_copy": ["the creator's face, voice, footage, catchphrases"],
    "tolerance": DEFAULT_TOLERANCE,
}


def validate(recipe: dict) -> list[str]:
    problems = []
    if recipe.get("schema") != "tsr/recipe@1":
        problems.append("schema must be tsr/recipe@1")
    length = recipe.get("length_s")
    if not isinstance(length, (int, float)) or length <= 0:
        problems.append("length_s must be a positive number")
    pace = recipe.get("cuts_per_10s")
    if pace is not None and (not isinstance(pace, (int, float)) or pace < 0):
        problems.append("cuts_per_10s must be a number or null")
    beats = recipe.get("beats")
    if not isinstance(beats, list) or not beats:
        problems.append("beats must be a non-empty list")
        beats = []
    previous = -1.0
    for number, beat in enumerate(beats, 1):
        at = beat.get("at") if isinstance(beat, dict) else None
        if not isinstance(at, (int, float)) or at < 0:
            problems.append(f"beat {number}: at must be seconds")
            continue
        if at < previous:
            problems.append(f"beat {number}: beats must be in time order")
        if isinstance(length, (int, float)) and at > length:
            problems.append(f"beat {number}: at {at} is after the end ({length} s)")
        if beat.get("what") not in BEAT_KINDS:
            problems.append(f"beat {number}: what must be one of {', '.join(BEAT_KINDS)}")
        previous = at
    if not recipe.get("do_not_copy"):
        problems.append("do_not_copy must name what is the creator's own (face, voice, footage, words)")
    return problems


def load_recipe(path: Path) -> dict:
    recipe = read_json(Path(path).expanduser())
    problems = validate(recipe)
    if problems:
        raise TsrError("recipe is not valid: " + "; ".join(problems))
    recipe.setdefault("tolerance", {})
    for key, value in DEFAULT_TOLERANCE.items():
        recipe["tolerance"].setdefault(key, value)
    return recipe
