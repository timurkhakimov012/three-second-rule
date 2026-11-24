from __future__ import annotations

import os
import platform
import shutil
import sys
from typing import Optional

from .common import VERSION, home

WHISPER_COMMANDS = ("mlx_whisper", "whisper", "whisper-cli")


def ffmpeg_ready() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def ytdlp() -> Optional[str]:
    return shutil.which("yt-dlp")


def whisper() -> Optional[str]:
    forced = os.environ.get("TSR_WHISPER")
    if forced:
        return forced if shutil.which(forced) else None
    for name in WHISPER_COMMANDS:
        if name == "whisper-cli" and not os.environ.get("TSR_WHISPER_MODEL"):
            continue
        if shutil.which(name):
            return name
    return None


def install_hint(tool: str) -> str:
    system = platform.system()
    if tool == "ffmpeg":
        if system == "Darwin":
            return "brew install ffmpeg"
        if system == "Windows":
            return "winget install Gyan.FFmpeg"
        return "sudo apt install ffmpeg  (or your system's package manager)"
    if tool == "yt-dlp":
        if system == "Darwin":
            return "brew install yt-dlp"
        return "python3 -m pip install --user yt-dlp"
    if tool == "whisper":
        if system == "Darwin" and platform.machine() == "arm64":
            return "python3 -m pip install --user mlx-whisper   (runs the tiny model on the Mac's GPU)"
        return "python3 -m pip install --user openai-whisper"
    return ""


def doctor() -> dict:
    found_whisper = whisper()
    report = {
        "version": VERSION,
        "python": sys.version.split()[0],
        "python_ok": sys.version_info >= (3, 9),
        "platform": f"{platform.system()} {platform.machine()}",
        "cache": str(home()),
        "tools": {
            "ffmpeg": {"found": ffmpeg_ready(), "needed_for": "every mode that reads a video", "required": True},
            "yt-dlp": {"found": ytdlp() is not None, "needed_for": "reading and downloading public posts by link",
                       "required": False},
            "whisper": {"found": found_whisper is not None, "command": found_whisper,
                        "needed_for": "word timings when a video has no subtitles", "required": False},
        },
    }
    for name, tool in report["tools"].items():
        if not tool["found"]:
            tool["install"] = install_hint(name)
    report["ready"] = report["python_ok"] and report["tools"]["ffmpeg"]["found"]
    return report


def doctor_text(report: dict) -> str:
    lines = [f"three-second-rule {report['version']}  python {report['python']}  {report['platform']}"]
    for name, tool in report["tools"].items():
        mark = "ok " if tool["found"] else ("MISSING" if tool["required"] else "missing")
        line = f"  {mark:8} {name:8} {tool['needed_for']}"
        if not tool["found"]:
            line += f"\n           install: {tool['install']}"
        lines.append(line)
    lines.append(f"  cache    {report['cache']}")
    if not report["python_ok"]:
        lines.append("Python 3.9 or newer is needed.")
    lines.append("Ready." if report["ready"] else "Not ready: install ffmpeg first.")
    return "\n".join(lines)
