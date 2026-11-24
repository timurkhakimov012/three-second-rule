from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional

from . import tools
from .common import TsrError, ToolMissing, iso, is_url, parse_time, run

READ_TIMEOUT = 300
DOWNLOAD_TIMEOUT = 900
PLATFORMS = {
    "tiktok": "tiktok", "youtube": "youtube", "youtubetab": "youtube", "instagram": "instagram",
    "twitter": "x", "facebook": "facebook", "threads": "threads",
}
COUNT_KEYS = {"views": "view_count", "likes": "like_count", "comments": "comment_count", "shares": "repost_count"}


def ytdlp() -> str:
    found = tools.ytdlp()
    if not found:
        raise ToolMissing("yt-dlp", tools.install_hint("yt-dlp"))
    return found


def checked_url(url: str) -> str:
    if not is_url(url):
        raise TsrError(f"not a web link: {url}")
    return url.strip()


def platform_of(info: dict, url: str = "") -> str:
    key = str(info.get("extractor_key") or info.get("ie_key") or info.get("extractor") or "").lower()
    for prefix, name in PLATFORMS.items():
        if key.startswith(prefix):
            return name
    host = re.sub(r"^https?://(www\.|m\.)?", "", url or info.get("webpage_url") or "").split("/")[0]
    for marker, name in (("tiktok", "tiktok"), ("youtu", "youtube"), ("instagram", "instagram"),
                         ("x.com", "x"), ("twitter", "x")):
        if marker in host:
            return name
    return key or "unknown"


def number(value) -> Optional[int]:
    try:
        return None if value is None else int(value)
    except (TypeError, ValueError):
        return None


def normalize(info: dict, url: str = "") -> dict:
    published = parse_time(info.get("timestamp")) or parse_time(info.get("upload_date"))
    handle = info.get("uploader_id") or info.get("channel_id") or info.get("uploader") or info.get("channel")
    post = {
        "platform": platform_of(info, url),
        "id": str(info.get("id") or ""),
        "url": info.get("webpage_url") or info.get("url") or url,
        "published_at": iso(published) if published else None,
        "duration": info.get("duration"),
        "title": info.get("title") or "",
        "caption": info.get("description") or "",
        "creator": {
            "handle": str(handle) if handle else None,
            "name": info.get("uploader") or info.get("channel"),
            "url": info.get("uploader_url") or info.get("channel_url"),
            "followers": number(info.get("channel_follower_count")),
        },
        "language": info.get("language"),
    }
    for name, key in COUNT_KEYS.items():
        post[name] = number(info.get(key))
    return post


def read_post(url: str) -> dict:
    url = checked_url(url)
    result = run([ytdlp(), "-J", "--no-download", "--no-playlist", "--no-warnings", "--", url], timeout=READ_TIMEOUT)
    return normalize(json.loads(result.stdout), url)


def creator_page(post: dict) -> Optional[str]:
    url = post["creator"].get("url")
    if not url:
        return None
    if post["platform"] == "youtube" and not url.rstrip("/").endswith("/shorts"):
        return url.rstrip("/") + "/shorts"
    return url


def read_creator(url: str, limit: int = 30, full: bool = False) -> list[dict]:
    url = checked_url(url)
    args = [ytdlp(), "-J", "--no-warnings", "--playlist-end", str(limit)]
    if not full:
        args.append("--flat-playlist")
    result = run(args + ["--", url], timeout=READ_TIMEOUT * (4 if full else 1))
    body = json.loads(result.stdout)
    entries = body.get("entries") or []
    posts = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("_type") == "playlist" and entry.get("entries"):
            entries.extend(entry["entries"])
            continue
        post = normalize(entry, entry.get("url") or "")
        if not post["creator"]["handle"]:
            post["creator"]["handle"] = body.get("uploader_id") or body.get("channel_id") or body.get("id")
        posts.append(post)
    return posts[:limit]


def download(url: str, folder: Path, language: Optional[str] = None) -> dict:
    url = checked_url(url)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / "video.%(ext)s"
    formats = "bv*[height<=720]+ba/b[height<=720]/bv*+ba/b"
    result = run([ytdlp(), "--no-playlist", "--no-warnings", "-f", formats, "--merge-output-format", "mp4",
                  "-o", str(target), "--", url], timeout=DOWNLOAD_TIMEOUT, check=False)
    videos = sorted(folder.glob("video.*"))
    videos = [v for v in videos if v.suffix.lower() in (".mp4", ".mkv", ".webm", ".mov")]
    if result.returncode != 0 or not videos:
        reason = " ".join(result.stderr.strip().splitlines()[-2:]) or "unknown error"
        return {"read": False, "reason": reason}
    subtitles = download_subtitles(url, folder, language)
    return {"read": True, "file": str(videos[0]), "subtitles": subtitles}


def download_subtitles(url: str, folder: Path, language: Optional[str]) -> Optional[str]:
    wanted = f"{language}.*,{language}" if language else "en.*,en"
    run([ytdlp(), "--no-playlist", "--no-warnings", "--skip-download", "--write-subs", "--write-auto-subs",
         "--sub-format", "vtt/srt/best", "--sub-langs", wanted, "-o", str(folder / "video.%(ext)s"), "--", url],
        timeout=READ_TIMEOUT, check=False)
    found = sorted(list(folder.glob("video*.vtt")) + list(folder.glob("video*.srt")))
    return str(found[0]) if found else None
