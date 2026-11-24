from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from . import checks, probe as probe_mod, sheets as sheets_mod, speech as speech_mod
from .common import (
    VERSION, TsrError, file_hash, iso, now, read_json, read_json_or, run_path, runs_dir, slug, write_json,
)
from .recipe import load_recipe

SHEET_FILES = ("first-3s.jpg", "shots.jpg", "safe-zones.jpg")


def run_id(video: Path) -> str:
    return f"check-{slug(video.stem, 32)}-{file_hash(video)[:8]}"


def measure_into(video: Path, folder: Path, chosen_platforms: Optional[list[str]] = None,
                 allow_whisper: bool = False, language: Optional[str] = None,
                 subtitles: Optional[Path] = None, fresh: bool = False) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    probe_path = folder / "probe.json"
    measured = None if fresh else read_json_or(probe_path, None)
    if not measured or measured.get("video", {}).get("hash") != file_hash(video)[:16]:
        measured = probe_mod.measure(video)
        write_json(probe_path, measured)
        fresh = True
    speech_path = folder / "speech.json"
    spoken = None if fresh else read_json_or(speech_path, None)
    wants_more = spoken is not None and spoken.get("not_measured") and (allow_whisper or subtitles)
    if spoken is None or wants_more or subtitles is not None:
        spoken = speech_mod.analyze(video, measured, folder, subtitles=subtitles, allow_whisper=allow_whisper,
                                    language=language)
        write_json(speech_path, spoken)
    sheets_path = folder / "sheets.json"
    drawn = None if fresh else read_json_or(sheets_path, None)
    missing = any(not (folder / name).is_file() for name in SHEET_FILES[:2])
    if drawn is None or missing or (drawn.get("safe_zones") or {}).get("platforms") != (
            chosen_platforms or list(sheets_mod.platforms())):
        drawn = sheets_mod.draw_all(video, measured, folder, chosen_platforms)
        write_json(sheets_path, drawn)
    return {"probe": measured, "speech": spoken, "sheets": drawn}


def notes_template(folder: Path) -> Path:
    body = {"_help": checks.NOTES_HELP, **checks.NOTES_TEMPLATE}
    return write_json(folder / "notes.template.json", body)


def start(video: Path, chosen_platforms: Optional[list[str]] = None, allow_whisper: bool = False,
          language: Optional[str] = None, subtitles: Optional[Path] = None, recipe: Optional[Path] = None,
          fresh: bool = False) -> dict:
    video = video.expanduser().resolve()
    if not video.is_file():
        raise TsrError(f"no such file: {video}")
    sheets_mod.platforms(chosen_platforms)
    loaded_recipe = load_recipe(recipe) if recipe else None
    identifier = run_id(video)
    folder = runs_dir() / identifier
    previous = read_json_or(folder / "run.json", {})
    measured = measure_into(video, folder, chosen_platforms, allow_whisper, language, subtitles, fresh)
    notes_template(folder)
    if loaded_recipe:
        write_json(folder / "recipe.json", loaded_recipe)
    info = {
        "schema": "tsr/run@1",
        "kind": "check",
        "id": identifier,
        "version": VERSION,
        "created_at": previous.get("created_at") or iso(now()),
        "updated_at": iso(now()),
        "video": {"path": str(video), "name": video.name, "hash": measured["probe"]["video"]["hash"]},
        "options": {"platforms": chosen_platforms or [], "whisper": allow_whisper, "language": language,
                    "subtitles": str(subtitles) if subtitles else None, "recipe": bool(loaded_recipe)},
        "same_name_runs": same_name_runs(video, identifier),
    }
    write_json(folder / "run.json", info)
    outcome = evaluate(folder)
    return {"run": info, "folder": str(folder), **measured, "checks": outcome}


def same_name_runs(video: Path, identifier: str) -> list[str]:
    prefix = f"check-{slug(video.stem, 32)}-"
    found = []
    for run in runs_dir().iterdir():
        if run.name.startswith(prefix) and run.name != identifier and (run / "checks.json").is_file():
            found.append(run.name)
    return sorted(found, key=lambda name: (runs_dir() / name).stat().st_mtime, reverse=True)


def evaluate(folder: Path) -> dict:
    info = read_json(folder / "run.json")
    notes = read_json_or(folder / "notes.json", None)
    recipe = read_json_or(folder / "recipe.json", None)
    outcome = checks.evaluate(
        read_json(folder / "probe.json"), read_json_or(folder / "speech.json", None), notes,
        read_json_or(folder / "sheets.json", None), info["options"].get("platforms"), recipe,
        info["options"].get("language"),
    )
    outcome["run"] = info["id"]
    write_json(folder / "checks.json", outcome)
    return outcome


def check(run: str) -> dict:
    folder = run_path(run)
    return {"folder": str(folder), "checks": evaluate(folder)}


def overview(result: dict) -> str:
    probe, spoken, drawn = result["probe"], result["speech"], result["sheets"]
    folder = Path(result["folder"])
    lines = [f"Run: {result['run']['id']}", f"Folder: {folder}"]
    audio = "audio" if probe["has_audio"] else "no audio"
    lines.append(f"Video: {probe['duration']:.1f} s, {probe['width']}x{probe['height']} ({probe['aspect']}), "
                 f"{probe['fps']} fps, {audio}")
    first_cut = f"first at {probe['first_cut']:.2f} s" if probe["first_cut"] is not None else "no cuts"
    longest = probe.get("longest_shot") or {}
    lines.append(f"Cuts: {probe['cut_count']} ({first_cut}), {probe['cuts_per_10s']} per 10 s, "
                 f"longest shot {longest.get('length', 0):.1f} s")
    if spoken.get("words"):
        rate = f"{spoken['words_per_minute']} words/min" if spoken.get("words_per_minute") else "rate n/a"
        lines.append(f"Speech: first word {spoken['first_word_s']:.2f} s, {rate}, language "
                     f"{spoken.get('language') or 'unknown'}, from {spoken['source']} ({spoken['granularity']})")
    else:
        lines.append(f"Speech: not measured ({spoken.get('not_measured')})")
    audio_info = probe.get("audio") or {}
    if audio_info.get("integrated_lufs") is not None:
        lines.append(f"Loudness: {audio_info['integrated_lufs']:.1f} LUFS")
    files = [drawn[k]["file"] for k in ("first_3s", "shots", "safe_zones") if drawn.get(k, {}).get("file")]
    lines.append("Sheets: " + "  ".join(str(folder / f) for f in files))
    if result["run"].get("same_name_runs"):
        lines.append(f"Earlier check of a file with this name: {result['run']['same_name_runs'][0]} "
                     f"(compare: tsr compare {result['run']['same_name_runs'][0]} {result['run']['id']})")
    lines.append("")
    lines.append(checks.text_table(result["checks"]))
    if not result["checks"]["looked"]:
        lines.append("")
        lines.append(f"Next: look at the sheets, write {folder / 'notes.json'} "
                     f"(from notes.template.json), then run: tsr check {result['run']['id']}")
    return "\n".join(lines)


def copy_sheets(folder: Path, target: Path) -> list[Path]:
    target.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in SHEET_FILES:
        source = folder / name
        if source.is_file():
            copied.append(Path(shutil.copy2(source, target / name)))
    return copied
