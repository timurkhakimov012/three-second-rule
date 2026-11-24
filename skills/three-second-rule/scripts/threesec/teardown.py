from __future__ import annotations

import csv
from pathlib import Path
from typing import Optional

from . import baseline, checks, fetch
from .common import VERSION, TsrError, iso, now, read_json, run_path, runs_dir, slug, write_json
from .preflight import measure_into, notes_template

MAX_PICKS = 4


def run_folder(platform: str, post_id: str) -> Path:
    return runs_dir() / f"teardown-{slug(platform, 12)}-{slug(post_id, 40)}"


def load_csv(path: Path) -> list[dict]:
    posts = []
    with open(path, newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            clean = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
            if not clean.get("id"):
                continue
            posts.append({
                "platform": clean.get("platform") or "unknown",
                "id": clean["id"],
                "url": clean.get("url") or None,
                "published_at": clean.get("published_at") or None,
                "views": int(float(clean["views"])) if clean.get("views") else None,
                "likes": int(float(clean["likes"])) if clean.get("likes") else None,
                "title": clean.get("title") or "",
                "creator": {"handle": clean.get("creator") or None},
            })
    if not posts:
        raise TsrError(f"{path}: no rows with an id column")
    return posts


def measure_video(folder: Path, file: Path, subtitles: Optional[str], language: Optional[str]) -> dict:
    measured = measure_into(file, folder, subtitles=Path(subtitles) if subtitles else None, language=language)
    notes_template(folder)
    write_json(folder / "run.json", {
        "schema": "tsr/run@1", "kind": "check", "id": str(folder), "version": VERSION, "created_at": iso(now()),
        "video": {"path": str(file), "name": file.name, "hash": measured["probe"]["video"]["hash"]},
        "options": {"platforms": [], "whisper": False, "language": language, "subtitles": subtitles, "recipe": False},
        "part_of": folder.parent.parent.name,
    })
    outcome = checks.evaluate(measured["probe"], measured["speech"], None, measured["sheets"])
    write_json(folder / "checks.json", outcome)
    probe, spoken = measured["probe"], measured["speech"]
    return {
        "folder": str(folder), "duration": probe["duration"], "first_cut": probe["first_cut"],
        "cuts_per_10s": probe["cuts_per_10s"], "first_word_s": spoken.get("first_word_s"),
        "words_per_minute": spoken.get("words_per_minute"), "first_3s_text": spoken.get("first_3s_text"),
        "checks": outcome["summary"]["line"],
    }


def start(url: Optional[str] = None, limit: int = 30, full: bool = False, download: bool = True,
          csv_path: Optional[Path] = None, target_id: Optional[str] = None, video: Optional[Path] = None) -> dict:
    if csv_path:
        posts = load_csv(csv_path)
        target = next((p for p in posts if p["id"] == target_id), posts[0]) if target_id else posts[0]
        source = f"csv {csv_path}"
    elif url:
        target = fetch.read_post(url)
        page = fetch.creator_page(target)
        posts = fetch.read_creator(page, limit, full) if page else []
        source = "yt-dlp"
    else:
        raise TsrError("give a post link, or --csv with the creator's posts")
    folder = run_folder(target["platform"], target["id"])
    folder.mkdir(parents=True, exist_ok=True)
    scored = baseline.score(target, posts)
    write_json(folder / "post.json", target)
    write_json(folder / "posts.json", posts)
    write_json(folder / "baseline.json", scored)
    language = target.get("language")
    watched = {}
    wanted = [target["id"]] + (scored["picks"]["ordinary"] + scored["picks"]["flops"])[:MAX_PICKS]
    by_id = {p["id"]: p for p in [target] + posts}
    for post_id in wanted:
        sub = folder / "videos" / slug(post_id, 40)
        if post_id == target["id"] and video:
            watched[post_id] = {"role": "target", **measure_video(sub, Path(video).expanduser(), None, language)}
            continue
        post = by_id.get(post_id) or {}
        role = "target" if post_id == target["id"] else (
            "ordinary" if post_id in scored["picks"]["ordinary"] else "flop")
        if not download or not post.get("url"):
            watched[post_id] = {"role": role, "read": False,
                                "reason": "downloads off" if not download else "no link for this post"}
            continue
        got = fetch.download(post["url"], sub, language)
        if not got["read"]:
            watched[post_id] = {"role": role, "read": False, "reason": got["reason"]}
            write_json(sub / "not_read.json", got)
            continue
        watched[post_id] = {"role": role, "read": True,
                            **measure_video(sub, Path(got["file"]), got.get("subtitles"), language)}
    info = {
        "schema": "tsr/run@1", "kind": "teardown", "id": folder.name, "version": VERSION, "created_at": iso(now()),
        "source": source, "post": {"platform": target["platform"], "id": target["id"], "url": target.get("url")},
        "watched": watched,
    }
    write_json(folder / "run.json", info)
    return {"folder": str(folder), "run": info, "baseline": scored}


def overview(result: dict) -> str:
    lines = [f"Run: {result['run']['id']}", f"Folder: {result['folder']}", baseline.text_report(result["baseline"])]
    for post_id, item in result["run"]["watched"].items():
        if not item.get("read", True) and "folder" not in item:
            lines.append(f"  {item['role']:8} {post_id}: not read ({item['reason']})")
            continue
        first_word = f"{item['first_word_s']:.2f} s" if item.get("first_word_s") is not None else "n/a"
        first_cut = f"{item['first_cut']:.2f} s" if item.get("first_cut") is not None else "none"
        lines.append(f"  {item['role']:8} {post_id}: {item['duration']:.1f} s, first word {first_word}, "
                     f"first cut {first_cut}, {item['cuts_per_10s']} cuts/10 s")
        lines.append(f"           sheets: {item['folder']}/first-3s.jpg, shots.jpg")
    lines.append("Next: look at every sheet side by side, write notes.json in each video folder, "
                 "then recipe.json and findings.md in the run folder (references/teardown.md).")
    return "\n".join(lines)


def load(run: str) -> dict:
    folder = run_path(run)
    return {"folder": folder, "run": read_json(folder / "run.json")}
