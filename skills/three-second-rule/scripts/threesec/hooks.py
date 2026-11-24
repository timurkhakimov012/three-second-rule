from __future__ import annotations

from typing import Optional

from . import lang
from .checks import FAIL, PASS, WARN, repeat_share
from .common import load_data

HOOK_WINDOW = 3.0
SPEAK_WARN = 3.5
TEXT_MIN, TEXT_MAX, TEXT_WARN = 3, 7, 10
BATCH_MIN, BATCH_MAX = 6, 10
MIN_ARCHETYPES = 3
REPEAT_OVERLAP, REPEAT_MIN_WORDS = 0.8, 4


def archetype_ids() -> dict:
    return {a["id"]: a for a in load_data("archetypes.json")["archetypes"]}


def finding(status: str, check: str, message: str) -> dict:
    return {"status": status, "check": check, "message": message}


def check_hook(hook: dict, language: Optional[dict], known: dict) -> dict:
    found = []
    archetype = hook.get("archetype")
    if archetype not in known:
        found.append(finding(WARN, "archetype", f"unknown archetype '{archetype}'"))
    visual = (hook.get("visual") or "").strip()
    spoken = (hook.get("spoken") or "").strip()
    shown = (hook.get("on_screen") or "").strip()
    if not visual:
        found.append(finding(FAIL, "visual", "no first frame described: a hook is a picture first"))
    if not shown:
        found.append(finding(FAIL, "on_screen", "no on-screen text: muted viewers get nothing"))
    else:
        count = len(lang.tokens(shown))
        if count > TEXT_WARN:
            found.append(finding(FAIL, "on_screen", f"{count} words on screen, keep {TEXT_MIN}-{TEXT_MAX}"))
        elif count > TEXT_MAX or count < TEXT_MIN:
            found.append(finding(WARN, "on_screen", f"{count} words on screen, aim for {TEXT_MIN}-{TEXT_MAX}"))
    speak_seconds = None
    if not spoken:
        found.append(finding(WARN, "spoken", "no voice line: fine for a silent edit, say so in the risk"))
    elif language:
        speak_seconds = round(len(lang.tokens(spoken)) / language["hook_words_per_second"], 1)
        if speak_seconds > SPEAK_WARN:
            found.append(finding(FAIL, "spoken", f"about {speak_seconds} s to say, it must land by {HOOK_WINDOW:.0f} s"))
        elif speak_seconds > HOOK_WINDOW:
            found.append(finding(WARN, "spoken", f"about {speak_seconds} s to say, tight for the 3 s window"))
    if spoken and shown and len(lang.tokens(shown)) >= REPEAT_MIN_WORDS and repeat_share(shown, spoken) >= REPEAT_OVERLAP:
        found.append(finding(WARN, "layers", "the text repeats the voice; compress it to the stake"))
    if language:
        both = f"{spoken} | {shown}"
        for phrase in lang.found(both, language["welcome"]) + lang.found(both, language["subscribe"]):
            found.append(finding(FAIL, "opener", f"'{phrase}' is a dead opener"))
        for phrase in language["filler_openers"]:
            if lang.starts_with(spoken, phrase) or lang.starts_with(shown, phrase):
                found.append(finding(FAIL, "opener", f"starts with filler '{phrase}'"))
        for phrase in lang.found(both, language["vague_teases"]):
            found.append(finding(FAIL, "opener", f"'{phrase}' is a vague tease: name the category of the answer"))
    status = FAIL if any(f["status"] == FAIL for f in found) else WARN if found else PASS
    return {"archetype": archetype, "status": status, "speak_seconds": speak_seconds, "findings": found}


def check_batch(batch: dict) -> dict:
    hooks = batch.get("hooks") or []
    code = batch.get("language") or lang.guess(" ".join(
        f"{h.get('spoken', '')} {h.get('on_screen', '')}" for h in hooks))
    language = lang.get(code)
    known = archetype_ids()
    results = [check_hook(h, language, known) for h in hooks]
    batch_findings = []
    if not BATCH_MIN <= len(hooks) <= BATCH_MAX:
        batch_findings.append(finding(WARN, "batch", f"{len(hooks)} hooks, aim for {BATCH_MIN}-{BATCH_MAX}"))
    used = {h.get("archetype") for h in hooks if h.get("archetype") in known}
    if len(hooks) >= MIN_ARCHETYPES and len(used) < MIN_ARCHETYPES:
        batch_findings.append(finding(FAIL, "batch", f"{len(used)} archetypes, use at least {MIN_ARCHETYPES}"))
    if language is None:
        batch_findings.append(finding(WARN, "language", "language not covered: word checks skipped"))
    passed = sum(1 for r in results if r["status"] != FAIL)
    status = FAIL if any(f["status"] == FAIL for f in batch_findings) or passed < len(results) else PASS
    return {"schema": "tsr/hook-check@1", "language": code, "status": status, "hooks": results,
            "batch": batch_findings, "summary": f"{passed} of {len(results)} hooks pass"}


def text_report(outcome: dict) -> str:
    lines = [outcome["summary"] + (f" (language {outcome['language']})" if outcome["language"] else "")]
    for number, hook in enumerate(outcome["hooks"], 1):
        speak = f", ~{hook['speak_seconds']} s to say" if hook["speak_seconds"] is not None else ""
        lines.append(f"  {hook['status'].upper():4} hook {number} [{hook['archetype']}]{speak}")
        for item in hook["findings"]:
            lines.append(f"         {item['status']}: {item['message']}")
    for item in outcome["batch"]:
        lines.append(f"  batch {item['status']}: {item['message']}")
    if outcome["status"] == FAIL:
        lines.append("Rewrite every failing hook and check again; never hand over a failing hook.")
    return "\n".join(lines)
