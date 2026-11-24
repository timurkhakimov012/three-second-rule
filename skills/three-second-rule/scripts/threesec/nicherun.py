from __future__ import annotations

from pathlib import Path
from typing import Optional

from . import fetch, niche
from .common import VERSION, TsrError, iso, now, read_json, read_json_or, run_path, runs_dir, slug, write_json
from .teardown import load_csv, measure_video


def init(name: str, words: Optional[list[str]] = None, platform: Optional[str] = None) -> Path:
    folder = runs_dir() / f"niche-{slug(name, 40)}"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "creators").mkdir(exist_ok=True)
    info = read_json_or(folder / "run.json", None) or {
        "schema": "tsr/run@1", "kind": "niche", "id": folder.name, "version": VERSION, "created_at": iso(now()),
        "name": name, "words": words or [], "platform": platform,
    }
    write_json(folder / "run.json", info)
    return folder


def add_creator(run: str, url: Optional[str] = None, csv_path: Optional[Path] = None, limit: int = 25,
                full: bool = False) -> dict:
    folder = run_path(run)
    if csv_path:
        posts = load_csv(csv_path)
        handle = posts[0]["creator"].get("handle") or csv_path.stem
        platform = posts[0].get("platform") or "unknown"
        creator = {"handle": handle, "url": None, "followers": None}
    elif url:
        page = url
        if "/shorts" not in url and ("youtube.com/@" in url or "youtube.com/channel/" in url):
            page = url.rstrip("/") + "/shorts"
        posts = fetch.read_creator(page, limit, full)
        if not posts:
            raise TsrError(f"no posts found at {url}")
        platform = posts[0]["platform"]
        handle = posts[0]["creator"].get("handle") or slug(url, 40)
        creator = {"handle": handle, "url": url, "followers": posts[0]["creator"].get("followers")}
    else:
        raise TsrError("give a creator link or --csv")
    path = niche.save_creator(folder, platform, handle, creator, posts)
    dated = sum(1 for p in posts if p.get("published_at"))
    return {"creator": path.stem, "posts": len(posts), "dated": dated, "file": str(path)}


def watch(run: str, download: bool = True) -> dict:
    folder = run_path(run)
    trends = read_json_or(folder / "trends.json", None) or niche.rank(folder)
    rows = {r["id"]: r for r in trends["posts"]}
    picks = trends["deep_read"]
    watched = {}
    for role, ids in (("trend", picks["trends"]), ("ordinary", picks["ordinary"]), ("flop", picks["flops"])):
        for post_id in ids:
            row = rows.get(post_id) or {}
            sub = folder / "videos" / slug(post_id, 40)
            if not download or not row.get("url"):
                watched[post_id] = {"role": role, "creator": row.get("creator"), "read": False,
                                    "reason": "downloads off" if not download else "no link"}
                continue
            got = fetch.download(row["url"], sub)
            if not got["read"]:
                watched[post_id] = {"role": role, "creator": row.get("creator"), "read": False, "reason": got["reason"]}
                continue
            watched[post_id] = {"role": role, "creator": row.get("creator"), "read": True,
                                **measure_video(sub, Path(got["file"]), got.get("subtitles"), None)}
    info = read_json(folder / "run.json")
    info["watched"] = watched
    write_json(folder / "run.json", info)
    return {"folder": str(folder), "watched": watched}


def watch_text(result: dict) -> str:
    lines = [f"Folder: {result['folder']}"]
    for post_id, item in result["watched"].items():
        if not item.get("read"):
            lines.append(f"  {item['role']:8} {item.get('creator')} {post_id}: not read ({item['reason']})")
        else:
            lines.append(f"  {item['role']:8} {item.get('creator')} {post_id}: {item['checks']}  "
                         f"sheets in {item['folder']}")
    return "\n".join(lines)
