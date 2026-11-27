from __future__ import annotations

from typing import Any, Callable, Optional

from . import lang
from .common import load_data
from .sheets import FIRST_STEP, platforms

PASS, WARN, FAIL = "pass", "warn", "fail"
NOT_MEASURED, NOT_APPLICABLE = "not_measured", "not_applicable"
DECIDED = (PASS, WARN, FAIL)
SYMBOLS = {PASS: "PASS", WARN: "WARN", FAIL: "FAIL", NOT_MEASURED: "----", NOT_APPLICABLE: "n/a "}
FRAME_KINDS = ("face", "person", "text", "product", "action", "scene", "graphic", "blank")

NOTES_TEMPLATE = {
    "looked": False,
    "frame0": {"kind": None, "what": None},
    "frame0_small_ok": None,
    "hook_text": None,
    "hook_text_tile": None,
    "topic_clear_tile": None,
    "visual_change_tile": None,
    "muted_ok": None,
    "muted_why": None,
    "layers_agree": None,
    "layers_why": None,
    "safe_zone_ok": None,
    "safe_zone_issue": None,
    "speaking": None,
    "captions": None,
    "payoff_delivered": None,
    "payoff_why": None,
    "ending_lands": None,
    "ending_what": None,
}

NOTES_HELP = {
    "looked": "true only after you opened first-3s.jpg, shots.jpg and safe-zones.jpg",
    "frame0": "first-3s tile 1. kind: one of " + ", ".join(FRAME_KINDS) + "; what: one plain sentence",
    "frame0_small_ok": "first-3s bottom row: false if the subject or the text of frame 0 is lost at profile-grid size or blurred",
    "hook_text": "the words on screen in the first 3 s, verbatim (not the subtitles of the speech); null if none",
    "hook_text_tile": "first-3s tile number (1-12) where the hook text is first readable; null if none",
    "topic_clear_tile": "first-3s tile by which a stranger knows what the video is about; null if not by tile 12",
    "visual_change_tile": "first-3s tile of a zoom, text pop or new object (cuts are measured already); null if none",
    "muted_ok": "true if the picture and the text alone state the promise with the sound off",
    "layers_agree": "true if picture, voice and on-screen text point at the same promise",
    "safe_zone_ok": "false if text or a face touches a red area of safe-zones.jpg; amber only: true, and say it in safe_zone_issue",
    "speaking": "true if someone speaks in the video",
    "captions": "true if the speech is captioned on screen; null if nobody speaks",
    "payoff_delivered": "true if the video delivers what the hook promised (shots.jpg); null if you cannot tell",
    "ending_lands": "false if the video trails off; look at the end tile of shots.jpg",
}


def config() -> dict:
    return load_data("checks.json")


def check_index(conf: dict) -> dict:
    return {c["id"]: c for c in conf["checks"]}


def validate_notes(notes: Optional[dict]) -> tuple[Optional[dict], list[str]]:
    if not notes:
        return None, ["no notes.json yet: the checks that need eyes are not checked"]
    problems = []
    if notes.get("looked") is not True:
        return None, ["notes.json says looked is not true: the checks that need eyes are not checked"]
    clean: dict[str, Any] = {"looked": True}
    frame0 = notes.get("frame0") or {}
    kind = frame0.get("kind") if isinstance(frame0, dict) else None
    if kind is not None and kind not in FRAME_KINDS:
        problems.append(f"frame0.kind '{kind}' is not one of {', '.join(FRAME_KINDS)}")
        kind = None
    clean["frame0"] = {"kind": kind, "what": frame0.get("what") if isinstance(frame0, dict) else None}
    for key in ("hook_text_tile", "topic_clear_tile", "visual_change_tile"):
        value = notes.get(key)
        if value is None:
            clean[key] = None
        elif isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 12:
            problems.append(f"{key} must be a tile number from 1 to 12 or null")
            clean[key] = None
        else:
            clean[key] = value
    for key in ("frame0_small_ok", "muted_ok", "layers_agree", "safe_zone_ok", "speaking", "captions", "payoff_delivered", "ending_lands"):
        value = notes.get(key)
        if value is not None and not isinstance(value, bool):
            problems.append(f"{key} must be true, false or null")
            value = None
        clean[key] = value
    for key in ("hook_text", "muted_why", "layers_why", "safe_zone_issue", "payoff_why", "ending_what"):
        value = notes.get(key)
        clean[key] = value.strip() if isinstance(value, str) and value.strip() else None
    if clean["hook_text"] and clean["hook_text_tile"] is None:
        problems.append("hook_text is given without hook_text_tile")
    return clean, problems


def tile_time(tile: Optional[int]) -> Optional[float]:
    return None if tile is None else round((tile - 1) * FIRST_STEP, 2)


def result(status: str, value: Any = None, expected: Any = None, detail: str = "") -> dict:
    return {"status": status, "value": value, "expected": expected, "detail": detail}


def unseen(notes: Optional[dict] = None, key: str = "") -> dict:
    if notes and key:
        return result(NOT_MEASURED, detail=f"notes.json leaves {key} null: it could not be told from the sheets")
    return result(NOT_MEASURED, detail="needs notes.json from looking at the sheets")


def opening_frame(c: dict, x: dict) -> dict:
    probe, notes = x["probe"], x["notes"]
    black = probe.get("black_at_start") or 0.0
    flat = ((probe.get("motion") or {}).get("frame0") or {}).get("flat")
    if black > c["max_black_s"]:
        return result(FAIL, f"black for {black:.2f} s", f"<= {c['max_black_s']} s", "MEASURED probe.json#black_at_start")
    if notes and (notes["frame0"] or {}).get("kind") == "blank":
        return result(FAIL, "blank first frame", "something on frame 0", "SEEN first-3s tile 1")
    if flat and not notes:
        return result(WARN, "frame 0 is nearly uniform: little to see at thumbnail size", "something on frame 0", "MEASURED probe.json#motion.frame0")
    if notes:
        what = (notes["frame0"] or {}).get("what") or (notes["frame0"] or {}).get("kind") or "seen"
        if notes.get("frame0_small_ok") is False:
            return result(WARN, f"{what}; lost at grid size", "reads at thumbnail size", "SEEN first-3s grid and blur tiles")
        return result(PASS, what, "something on frame 0", "SEEN first-3s tile 1")
    return result(PASS, "not black, not flat", "something on frame 0", "MEASURED only; look at tile 1 to confirm")


def with_better_start(outcome: dict, c: dict, probe: dict, change: float) -> dict:
    best = (probe.get("motion") or {}).get("most_active")
    if not best or best["change"] < max(c["min_change"], change * c["best_start_ratio"]):
        return outcome
    outcome["hint"] = (f"the most active half-second is {best['start']:.2f}-{best['end']:.2f} s "
                       f"(change {best['change']:.3f}): open there, or move that moment to the start")
    outcome["detail"] += "; MEASURED probe.json#motion.most_active"
    return outcome


def early_motion(c: dict, x: dict) -> dict:
    probe = x["probe"]
    change = (probe.get("motion") or {}).get("first_half_second")
    first_cut = probe.get("first_cut")
    frozen = probe.get("frozen_at_start") or 0.0
    if change is None:
        return result(NOT_MEASURED, detail="no frames could be read in the first 0.5 s")
    if first_cut is not None and first_cut <= 0.5:
        return result(PASS, f"a cut at {first_cut:.2f} s", "movement by 0.5 s", "MEASURED probe.json#first_cut")
    if change >= c["min_change"]:
        return result(PASS, f"frame change {change:.3f}", f">= {c['min_change']}", "MEASURED probe.json#motion")
    if frozen >= c["frozen_fail_s"] or change < c["min_change"] / 4:
        return with_better_start(result(FAIL, f"still for {max(frozen, 0.5):.2f} s (change {change:.3f})",
                                        "movement by 0.5 s", "MEASURED probe.json#frozen_at_start, #motion"), c, probe, change)
    return with_better_start(result(WARN, f"barely moves (change {change:.3f})", f">= {c['min_change']}",
                                    "MEASURED probe.json#motion"), c, probe, change)


def first_word(c: dict, x: dict) -> dict:
    probe, speech = x["probe"], x["speech"]
    if not probe.get("has_audio"):
        return result(NOT_APPLICABLE, detail="the video has no audio track")
    if not speech or not speech.get("words"):
        notes = x["notes"]
        if notes and notes.get("speaking") is False:
            return result(NOT_APPLICABLE, detail="nobody speaks (notes.json)")
        reason = (speech or {}).get("not_measured") or "no words were found"
        return result(NOT_MEASURED, detail=reason)
    seconds = speech["first_word_s"]
    precision = " (from the subtitle cue, about +-0.3 s)" if speech.get("granularity") == "cue" else ""
    detail = f"MEASURED speech.json#first_word_s via {speech.get('source')}{precision}"
    if seconds <= c["pass_s"]:
        return result(PASS, f"{seconds:.2f} s", f"<= {c['pass_s']} s", detail)
    if seconds <= c["warn_s"]:
        return result(WARN, f"{seconds:.2f} s", f"<= {c['pass_s']} s", detail)
    return result(FAIL, f"{seconds:.2f} s", f"<= {c['pass_s']} s", detail)


def hook_text(c: dict, x: dict) -> dict:
    notes = x["notes"]
    if not notes:
        return unseen()
    text, tile = notes.get("hook_text"), notes.get("hook_text_tile")
    expected = f"{c['min_words']}-{c['max_words']} words by {c['pass_s']} s"
    if not text or tile is None:
        status = WARN if notes.get("muted_ok") else FAIL
        detail = "SEEN: no text on screen in the first 3 s"
        if status == WARN:
            detail += "; the picture carries the promise on its own (H7)"
        return result(status, "no text hook", expected, detail)
    seconds = tile_time(tile)
    count = len(lang.tokens(text))
    value = f"'{text}' ({count} words) at {seconds:.2f} s"
    detail = f"SEEN first-3s tile {tile}"
    if seconds > c["warn_s"] or count > c["warn_words"]:
        return result(FAIL, value, expected, detail)
    if seconds > c["pass_s"] or count > c["max_words"] or count < c["min_words"]:
        return result(WARN, value, expected, detail)
    return result(PASS, value, expected, detail)


def topic_clear(c: dict, x: dict) -> dict:
    notes = x["notes"]
    if not notes:
        return unseen()
    tile = notes.get("topic_clear_tile")
    if tile is None:
        return result(FAIL, "not clear by 3 s", "clear by 3 s", "SEEN first-3s tiles 1-12")
    return result(PASS, f"clear at {tile_time(tile):.2f} s", "clear by 3 s", f"SEEN first-3s tile {tile}")


def visual_change(c: dict, x: dict) -> dict:
    probe, notes = x["probe"], x["notes"]
    window = c["window_s"]
    cuts = [t for t in probe.get("cuts") or [] if t <= window]
    if cuts:
        return result(PASS, f"cut at {cuts[0]:.2f} s", f"a change by {window:.0f} s", "MEASURED probe.json#cuts")
    if notes and notes.get("visual_change_tile"):
        tile = notes["visual_change_tile"]
        return result(PASS, f"change at {tile_time(tile):.2f} s", f"a change by {window:.0f} s", f"SEEN first-3s tile {tile}")
    moving = (probe.get("motion") or {}).get("first_three_seconds") or 0.0
    if moving >= c["min_motion"]:
        detail = "MEASURED: the picture moves but no cut; " + ("SEEN: no zoom or pop either" if notes else "look for a zoom or text pop")
        return result(WARN, f"motion {moving:.3f}, no cut", f"a change by {window:.0f} s", detail)
    if not notes:
        return result(WARN, "no cut and little motion", f"a change by {window:.0f} s", "MEASURED; look at the sheet to confirm")
    return result(FAIL, "no cut, zoom or pop", f"a change by {window:.0f} s", "MEASURED probe.json#cuts + SEEN tiles 1-12")


def works_muted(c: dict, x: dict) -> dict:
    notes = x["notes"]
    if not notes or notes.get("muted_ok") is None:
        return unseen(notes, "muted_ok")
    why = notes.get("muted_why") or ""
    return result(PASS if notes["muted_ok"] else FAIL, why or ("yes" if notes["muted_ok"] else "no"), "understood muted",
                  "SEEN first-3s tiles 1-12")


def repeat_share(text: str, spoken: str) -> float:
    shown, heard = lang.tokens(text), lang.tokens(spoken)
    if not shown or not heard:
        return 0.0
    longest = 0
    previous = [0] * (len(heard) + 1)
    for shown_token in shown:
        current = [0] * (len(heard) + 1)
        for index, heard_token in enumerate(heard, 1):
            if shown_token == heard_token:
                current[index] = previous[index - 1] + 1
                longest = max(longest, current[index])
        previous = current
    return longest / len(shown)


def layers_agree(c: dict, x: dict) -> dict:
    notes, speech = x["notes"], x["speech"] or {}
    if not notes or notes.get("layers_agree") is None:
        return unseen(notes, "layers_agree")
    why = notes.get("layers_why") or ""
    if not notes["layers_agree"]:
        return result(FAIL, why or "the layers pull apart", "one promise in all three", "SEEN")
    text, spoken = notes.get("hook_text"), speech.get("first_3s_text") or ""
    if text and spoken and len(lang.tokens(text)) >= c["repeat_min_words"]:
        share = repeat_share(text, spoken)
        if share >= c["repeat_overlap"]:
            return result(WARN, f"text repeats the voice ({share:.0%} of its words)", "text compresses the voice",
                          "SEEN hook_text + MEASURED speech.json#first_3s_text")
    return result(PASS, why or "agree", "one promise in all three", "SEEN")


def opener(c: dict, x: dict) -> dict:
    speech, notes = x["speech"] or {}, x["notes"] or {}
    spoken = speech.get("first_3s_text") or ""
    shown = notes.get("hook_text") or ""
    if not spoken and not shown:
        return result(NOT_MEASURED, detail="no words in the first 3 s were read (no transcript, no hook text)")
    both = f"{spoken} | {shown}"
    language = lang.get(speech.get("language") or x.get("language")) or lang.get(lang.guess(both, short=True)) \
        or lang.matching(both)
    if language is None:
        return result(NOT_MEASURED, detail=f"language not covered (covered: {', '.join(lang.languages())})")
    bad = lang.found(both, language["welcome"]) + lang.found(both, language["subscribe"])
    if bad:
        return result(FAIL, "opens with: " + ", ".join(f"'{b}'" for b in bad), "no greeting, no early ask",
                      "MEASURED speech.json#first_3s_text against data/lang/" + language["code"] + ".json")
    weak = [f for f in language["filler_openers"] if lang.starts_with(spoken, f)]
    weak += lang.found(both, language["vague_teases"])
    if weak:
        return result(WARN, "opens with: " + ", ".join(f"'{w}'" for w in weak), "no filler, no vague tease",
                      "MEASURED against data/lang/" + language["code"] + ".json")
    return result(PASS, "no dead opener found", "no greeting, filler or vague tease",
                  "MEASURED against data/lang/" + language["code"] + ".json")


def dead_air(c: dict, x: dict) -> dict:
    probe = x["probe"]
    audio = probe.get("audio")
    if not audio:
        return result(NOT_APPLICABLE, detail="the video has no audio track")
    duration = probe["duration"]
    stretches = []
    for start, end in audio.get("silences") or []:
        inner_start, inner_end = max(start, c["edge_s"]), min(end, duration - c["edge_s"])
        if inner_end - inner_start >= c["warn_s"]:
            stretches.append((round(inner_start, 2), round(inner_end, 2)))
    if not stretches:
        return result(PASS, "none", f"no silence >= {c['warn_s']} s", "MEASURED probe.json#audio.silences")
    longest = max(e - s for s, e in stretches)
    value = ", ".join(f"{s:.2f}-{e:.2f} s" for s, e in stretches)
    status = FAIL if longest >= c["fail_s"] else WARN
    return result(status, value, f"no silence >= {c['warn_s']} s", "MEASURED probe.json#audio.silences")


def long_shot(c: dict, x: dict) -> dict:
    probe = x["probe"]
    shot = probe.get("longest_shot")
    if not shot:
        return result(NOT_MEASURED, detail="no shots measured")
    expected = f"<= {c['warn_s']:.0f} s without a cut"
    stretch = probe.get("longest_unchanged")
    if stretch and stretch["length"] < shot["length"]:
        value = f"{stretch['length']:.1f} s ({stretch['start']:.1f}-{stretch['end']:.1f} s) counting cuts in one half of the frame"
        status = WARN if stretch["length"] > c["warn_s"] else PASS
        return result(status, value, expected, "MEASURED probe.json#longest_unchanged (split screen: #region_cuts)")
    value = f"shot {shot['n']}: {shot['length']:.1f} s ({shot['start']:.1f}-{shot['end']:.1f} s)"
    status = WARN if shot["length"] > c["warn_s"] else PASS
    return result(status, value, expected, "MEASURED probe.json#longest_shot")


def payoff(c: dict, x: dict) -> dict:
    notes = x["notes"]
    if not notes or notes.get("payoff_delivered") is None:
        return unseen(notes, "payoff_delivered")
    why = notes.get("payoff_why") or ""
    return result(PASS if notes["payoff_delivered"] else FAIL, why or str(notes["payoff_delivered"]).lower(),
                  "the promise is shown", "INFERRED from shots.jpg")


def asks(c: dict, x: dict) -> dict:
    speech = x["speech"] or {}
    transcript = speech.get("transcript") or ""
    if not transcript:
        return result(NOT_MEASURED, detail="no transcript")
    language = lang.get(speech.get("language") or x.get("language"))
    if language is None:
        return result(NOT_MEASURED, detail="language not covered")
    kinds = lang.asks(transcript, language)
    if not kinds:
        return result(PASS, "no spoken ask", f"at most {c['max_kinds']} kind", "MEASURED speech.json#transcript")
    value = ", ".join(f"{k} ({', '.join(v)})" for k, v in kinds.items())
    status = PASS if len(kinds) <= c["max_kinds"] else WARN
    return result(status, value, f"at most {c['max_kinds']} kind", "MEASURED speech.json#transcript")


def ending(c: dict, x: dict) -> dict:
    notes = x["notes"]
    if not notes or notes.get("ending_lands") is None:
        return unseen(notes, "ending_lands")
    what = notes.get("ending_what") or ""
    return result(PASS if notes["ending_lands"] else WARN, what or str(notes["ending_lands"]).lower(),
                  "ends on a result, a turn or a loop", "SEEN shots.jpg end tile")


def format_check(c: dict, x: dict) -> dict:
    probe = x["probe"]
    value = f"{probe['width']}x{probe['height']} ({probe.get('aspect')})"
    if probe.get("aspect") != "9:16":
        return result(FAIL, value, "9:16", "MEASURED probe.json#aspect")
    if probe["height"] < c["min_height"]:
        return result(WARN, value, f"9:16, at least {c['min_height']} px high", "MEASURED probe.json#height")
    return result(PASS, value, "9:16", "MEASURED probe.json#aspect")


def safe_zone(c: dict, x: dict) -> dict:
    notes, drawn = x["notes"], x.get("safe_zone_sheet") or {}
    if drawn.get("skipped"):
        return result(NOT_APPLICABLE, detail=drawn["skipped"])
    if not notes or notes.get("safe_zone_ok") is None:
        return unseen(notes, "safe_zone_ok")
    issue = notes.get("safe_zone_issue") or ""
    names = ", ".join(drawn.get("platforms") or [])
    return result(PASS if notes["safe_zone_ok"] else FAIL, issue or ("inside" if notes["safe_zone_ok"] else "outside"),
                  f"inside the safe zone ({names})", "SEEN safe-zones.jpg")


def loudness(c: dict, x: dict) -> dict:
    audio = x["probe"].get("audio")
    if not audio:
        return result(NOT_APPLICABLE, detail="the video has no audio track")
    value = audio.get("integrated_lufs")
    if value is None:
        return result(NOT_MEASURED, detail="loudness could not be measured (silent track?)")
    target = load_data("platforms.json")["loudness_target_lufs"]
    off = abs(value - target)
    status = PASS if off <= c["warn_lu"] else WARN if off <= c["fail_lu"] else FAIL
    return result(status, f"{value:.1f} LUFS", f"{target} +- {c['warn_lu']} LUFS", "MEASURED probe.json#audio.integrated_lufs")


def captions(c: dict, x: dict) -> dict:
    notes, speech = x["notes"], x["speech"] or {}
    has_words = bool(speech.get("words"))
    if notes and notes.get("speaking") is False and not has_words:
        return result(NOT_APPLICABLE, detail="nobody speaks")
    if not notes or notes.get("captions") is None:
        return unseen(notes, "captions")
    if not has_words and not notes.get("speaking"):
        return result(NOT_APPLICABLE, detail="nobody speaks")
    return result(PASS if notes["captions"] else FAIL, "captioned" if notes["captions"] else "no captions",
                  "speech captioned", "SEEN first-3s and shots sheets")


def length(c: dict, x: dict) -> dict:
    duration = x["probe"]["duration"]
    chosen = x.get("platforms") or []
    known = platforms(chosen or None)
    over = {k: v["max_seconds"] for k, v in known.items() if duration > v["max_seconds"]}
    if not over:
        return result(PASS, f"{duration:.1f} s", "within the limit", "MEASURED probe.json#duration")
    names = ", ".join(f"{known[k]['name']} ({v} s)" for k, v in over.items())
    status = FAIL if chosen else WARN
    return result(status, f"{duration:.1f} s", f"over the limit of {names}", "MEASURED probe.json#duration")


def recipe_length(c: dict, x: dict) -> dict:
    recipe = x.get("recipe")
    if not recipe:
        return result(NOT_APPLICABLE)
    target = recipe["length_s"]
    tolerance = recipe.get("tolerance", {}).get("length_pct", 10)
    duration = x["probe"]["duration"]
    off = abs(duration - target) / target * 100
    return result(PASS if off <= tolerance else FAIL, f"{duration:.1f} s", f"{target:.1f} s +- {tolerance}%",
                  "MEASURED probe.json#duration against recipe.json#length_s")


def recipe_pace(c: dict, x: dict) -> dict:
    recipe = x.get("recipe")
    if not recipe or recipe.get("cuts_per_10s") is None:
        return result(NOT_APPLICABLE)
    target = recipe["cuts_per_10s"]
    tolerance = recipe.get("tolerance", {}).get("cuts_per_10s", 1.0)
    actual = x["probe"]["cuts_per_10s"]
    return result(PASS if abs(actual - target) <= tolerance else FAIL, f"{actual:.1f} per 10 s",
                  f"{target:.1f} +- {tolerance}", "MEASURED probe.json#cuts_per_10s against recipe.json")


def recipe_beats(c: dict, x: dict) -> dict:
    recipe = x.get("recipe")
    beats = [b for b in (recipe or {}).get("beats", []) if b.get("cut")]
    if not beats:
        return result(NOT_APPLICABLE)
    tolerance = recipe.get("tolerance", {}).get("cut_s", 0.25)
    cuts = x["probe"].get("cuts") or []
    missed = []
    for beat in beats:
        nearest = min((abs(cut - beat["at"]) for cut in cuts), default=None)
        if nearest is None or nearest > tolerance:
            missed.append(f"{beat.get('what', 'beat')} at {beat['at']:.2f} s")
    if missed:
        return result(FAIL, "missed: " + "; ".join(missed), f"a cut within {tolerance} s of each", "MEASURED probe.json#cuts")
    return result(PASS, f"{len(beats)} of {len(beats)} on time", f"within {tolerance} s", "MEASURED probe.json#cuts")


FUNCTIONS: dict[str, Callable[[dict, dict], dict]] = {
    "opening_frame": opening_frame, "early_motion": early_motion, "first_word": first_word,
    "hook_text": hook_text, "topic_clear": topic_clear, "visual_change": visual_change,
    "works_muted": works_muted, "layers_agree": layers_agree, "opener": opener,
    "dead_air": dead_air, "long_shot": long_shot, "payoff": payoff, "asks": asks, "ending": ending,
    "format": format_check, "safe_zone": safe_zone, "loudness": loudness, "captions": captions, "length": length,
    "recipe_length": recipe_length, "recipe_pace": recipe_pace, "recipe_beats": recipe_beats,
}


def evaluate(probe: dict, speech: Optional[dict], notes: Optional[dict], sheets: Optional[dict] = None,
             chosen_platforms: Optional[list[str]] = None, recipe: Optional[dict] = None,
             language: Optional[str] = None) -> dict:
    conf = config()
    clean, problems = validate_notes(notes)
    context = {
        "probe": probe, "speech": speech, "notes": clean, "recipe": recipe, "language": language,
        "platforms": chosen_platforms or [], "safe_zone_sheet": (sheets or {}).get("safe_zones"),
    }
    results = []
    for item in conf["checks"]:
        outcome = FUNCTIONS[item["key"]](item, context)
        if item["section"] == "recipe" and outcome["status"] == NOT_APPLICABLE and not recipe:
            continue
        entry = {"id": item["id"], "section": item["section"], "title": item["title"], **outcome,
                 "source": item["source"]}
        if outcome["status"] in (FAIL, WARN):
            entry["why"] = item["why"]
            entry["fix"] = item["fix"] + (f" Measured: {outcome['hint']}." if outcome.get("hint") else "")
        results.append(entry)
    return {"schema": "tsr/checks@1", "checks": results, "summary": summarize(results), "notes_problems": problems,
            "looked": clean is not None}


def summarize(results: list[dict]) -> dict:
    counts = {status: sum(1 for r in results if r["status"] == status) for status in SYMBOLS}
    decided = sum(counts[s] for s in DECIDED)
    return {"passed": counts[PASS], "warned": counts[WARN], "failed": counts[FAIL], "decided": decided,
            "not_measured": counts[NOT_MEASURED], "not_applicable": counts[NOT_APPLICABLE],
            "line": f"{counts[PASS]} of {decided} passed, {counts[WARN]} warning(s), {counts[FAIL]} failed"
                    + (f", {counts[NOT_MEASURED]} not measured" if counts[NOT_MEASURED] else "")}


def text_table(outcome: dict) -> str:
    conf = config()
    lines = [outcome["summary"]["line"]]
    for section, title in conf["sections"].items():
        rows = [r for r in outcome["checks"] if r["section"] == section]
        if not rows:
            continue
        lines.append(f"\n{title}")
        for row in rows:
            value = f"  {row['value']}" if row.get("value") not in (None, "") else ""
            lines.append(f"  {SYMBOLS[row['status']]} {row['id']:3} {row['title']}{value}")
            if row["status"] in (NOT_MEASURED, NOT_APPLICABLE) and row.get("detail"):
                lines.append(f"            {row['detail']}")
    fixes = [r for r in outcome["checks"] if r["status"] in (FAIL, WARN)]
    if fixes:
        lines.append("\nFix first")
        ordered = sorted(fixes, key=lambda r: (r["status"] != FAIL, list(conf["sections"]).index(r["section"])))
        for number, row in enumerate(ordered, 1):
            lines.append(f"  {number}. [{row['id']}] {row['fix']}")
    for problem in outcome.get("notes_problems") or []:
        lines.append(f"\nnote: {problem}")
    return "\n".join(lines)
