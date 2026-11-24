from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

from . import lang, tools
from .common import TsrError, read_json, rounded, run

HOOK_WINDOW = 3.0
GAP_SEC = 0.7
MIN_SPAN_FOR_RATE = 2.0
LOW_PROBABILITY = 0.15
SIDECAR_SUFFIXES = (".srt", ".vtt")
WHISPER_TIMEOUT = 1800
DEFAULT_MODELS = {"mlx_whisper": "mlx-community/whisper-tiny", "whisper": "tiny"}

TIMESTAMP = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})[.,](\d{1,3})")
ARROW = re.compile(r"^\s*(\S+)\s+-->\s+(\S+)")
INLINE = re.compile(r"<(\d{1,2}:\d{2}(?::\d{2})?[.,]\d{1,3})>")
TAG = re.compile(r"<[^>]*>|\{[^}]*\}")


def seconds(stamp: str) -> float:
    match = TIMESTAMP.fullmatch(stamp.strip())
    if not match:
        raise ValueError(stamp)
    hours, minutes, secs, fraction = match.groups()
    return int(hours or 0) * 3600 + int(minutes) * 60 + int(secs) + int(fraction.ljust(3, "0")) / 1000


def clean(text: str) -> str:
    text = TAG.sub("", text)
    text = re.sub(r"[♪♫]", " ", text)
    text = re.sub(r"\[[^\]]*\]|\([^)]*\)", " ", text)
    return " ".join(text.split())


def parse_cues(text: str) -> list[dict]:
    cues = []
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    number = 0
    while number < len(lines):
        match = ARROW.match(lines[number])
        if not match:
            number += 1
            continue
        try:
            start, end = seconds(match.group(1)), seconds(match.group(2))
        except ValueError:
            number += 1
            continue
        body = []
        number += 1
        while number < len(lines) and lines[number].strip():
            body.append(lines[number])
            number += 1
        cues.append({"start": start, "end": end, "lines": body})
    return cues


def has_inline_timing(cues: list[dict]) -> bool:
    return any(INLINE.search(line) for cue in cues for line in cue["lines"])


def inline_words(cues: list[dict]) -> list[dict]:
    words = []
    for cue in cues:
        for line in cue["lines"]:
            if not INLINE.search(line):
                continue
            pieces = INLINE.split(line)
            current = cue["start"]
            for index, piece in enumerate(pieces):
                if index % 2 == 1:
                    current = seconds(piece)
                    continue
                for token in clean(piece).split():
                    words.append({"w": token, "start": round(current, 3), "end": None})
    words.sort(key=lambda w: w["start"])
    for number, word in enumerate(words):
        following = words[number + 1]["start"] if number + 1 < len(words) else word["start"] + 0.4
        word["end"] = round(min(following, word["start"] + 1.0), 3)
    return words


def even_words(cues: list[dict]) -> list[dict]:
    words = []
    seen_text = None
    for cue in cues:
        text = clean(" ".join(cue["lines"]))
        if not text or text == seen_text:
            continue
        seen_text = text
        tokens = text.split()
        total = sum(len(t) for t in tokens) or 1
        position = cue["start"]
        span = max(0.01, cue["end"] - cue["start"])
        for token in tokens:
            length = span * len(token) / total
            words.append({"w": token, "start": round(position, 3), "end": round(position + length, 3)})
            position += length
    return words


def subtitle_words(text: str) -> tuple[list[dict], str]:
    cues = parse_cues(text)
    if has_inline_timing(cues):
        return inline_words(cues), "word"
    return even_words(cues), "cue"


def whisper_words(body: dict) -> tuple[list[dict], int, Optional[str]]:
    words, dropped = [], 0
    if "transcription" in body:
        return whisper_cpp_words(body), 0, (body.get("result") or {}).get("language")
    for segment in body.get("segments") or []:
        for item in segment.get("words") or []:
            probability = item.get("probability")
            if probability is not None and probability < LOW_PROBABILITY:
                dropped += 1
                continue
            token = clean(str(item.get("word", "")))
            if token:
                words.append({"w": token, "start": round(float(item["start"]), 3), "end": round(float(item["end"]), 3)})
    return words, dropped, body.get("language")


def whisper_cpp_words(body: dict) -> list[dict]:
    words: list[dict] = []
    for segment in body.get("transcription") or []:
        for token in segment.get("tokens") or []:
            text = str(token.get("text", ""))
            if text.startswith("[_") or not text.strip():
                continue
            offsets = token.get("offsets") or {}
            start, end = offsets.get("from", 0) / 1000, offsets.get("to", 0) / 1000
            if text.startswith(" ") or not words:
                words.append({"w": text.strip(), "start": round(start, 3), "end": round(end, 3)})
            else:
                words[-1]["w"] += text.strip()
                words[-1]["end"] = round(end, 3)
    return [w for w in words if clean(w["w"])]


def find_sidecar(video: Path) -> Optional[Path]:
    candidates = []
    for path in video.parent.glob(f"{glob_escape(video.stem)}*"):
        if path.suffix.lower() in SIDECAR_SUFFIXES and path.is_file():
            candidates.append(path)
    candidates.sort(key=lambda p: (len(p.name), p.name))
    return candidates[0] if candidates else None


def glob_escape(text: str) -> str:
    return re.sub(r"([\[\]*?])", r"[\1]", text)


def embedded_subtitles(video: Path, probe: dict) -> Optional[str]:
    if not probe.get("subtitle_streams"):
        return None
    result = run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(video), "-map", "0:s:0",
                  "-f", "srt", "-"], check=False)
    return result.stdout if result.returncode == 0 and "-->" in result.stdout else None


def run_whisper(video: Path, folder: Path, language: Optional[str]) -> tuple[list[dict], int, Optional[str], str]:
    command = tools.whisper()
    if command is None:
        raise TsrError("no Whisper found: " + tools.install_hint("whisper"))
    out = folder / "whisper"
    out.mkdir(parents=True, exist_ok=True)
    audio = out / "audio.wav"
    run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000",
         str(audio)])
    name = Path(command).name
    model = os.environ.get("TSR_WHISPER_MODEL") or DEFAULT_MODELS.get(name, "tiny")
    if name == "whisper-cli":
        args = [command, "-m", model, "-f", str(audio), "-ojf", "-of", str(out / "result")]
        if language:
            args += ["-l", language]
    elif name == "mlx_whisper":
        args = [command, str(audio), "--model", model, "--word-timestamps", "True", "--output-format", "json",
                "--output-dir", str(out)]
        if language:
            args += ["--language", language]
    else:
        args = [command, str(audio), "--model", model, "--word_timestamps", "True", "--output_format", "json",
                "--output_dir", str(out)]
        if language:
            args += ["--language", language]
    run(args, timeout=WHISPER_TIMEOUT)
    results = sorted((p for p in out.glob("*.json")), key=lambda p: p.stat().st_mtime, reverse=True)
    if not results:
        raise TsrError(f"{name} wrote no JSON")
    words, dropped, detected = whisper_words(read_json(results[0]))
    audio.unlink(missing_ok=True)
    return words, dropped, detected, f"{name} ({model})"


def metrics(words: list[dict], duration: float, language: Optional[str]) -> dict:
    if not words:
        return {"first_word_s": None, "words": 0, "words_per_minute": None, "gaps": [], "first_3s_text": "",
                "transcript": "", "language": language}
    transcript = " ".join(w["w"] for w in words)
    code = language or lang.guess(transcript)
    first, last = words[0]["start"], max(w["end"] for w in words)
    span = last - first
    gaps = []
    for previous, current in zip(words, words[1:]):
        pause = current["start"] - previous["end"]
        if pause >= GAP_SEC:
            gaps.append({"from": round(previous["end"], 2), "to": round(current["start"], 2), "length": round(pause, 2)})
    early = [w for w in words if w["start"] < HOOK_WINDOW]
    return {
        "first_word_s": rounded(first, 2),
        "last_word_s": rounded(last, 2),
        "words": len(words),
        "words_per_minute": round(len(words) / span * 60) if span >= MIN_SPAN_FOR_RATE else None,
        "words_first_3s": len(early),
        "first_3s_text": " ".join(w["w"] for w in early),
        "gaps": gaps,
        "speech_share": rounded(min(1.0, span / duration), 3) if duration else None,
        "transcript": transcript,
        "language": code,
    }


def analyze(video: Path, probe: dict, folder: Path, subtitles: Optional[Path] = None, allow_whisper: bool = False,
            language: Optional[str] = None) -> dict:
    duration = probe["duration"]
    result = {"schema": "tsr/speech@1", "source": None, "granularity": None, "detail": None, "dropped_low_confidence": 0}
    words: list[dict] = []
    sidecar = subtitles or find_sidecar(video)
    if sidecar is not None:
        words, granularity = subtitle_words(sidecar.read_text(encoding="utf-8", errors="replace"))
        result.update(source="subtitle file", granularity=granularity, detail=str(sidecar))
    if not words:
        embedded = embedded_subtitles(video, probe)
        if embedded:
            words, granularity = subtitle_words(embedded)
            result.update(source="embedded subtitles", granularity=granularity, detail="stream 0:s:0")
    if not words and allow_whisper and probe.get("has_audio"):
        words, dropped, detected, used = run_whisper(video, folder, language)
        result.update(source="whisper", granularity="word", detail=used, dropped_low_confidence=dropped)
        language = language or detected
    if not words:
        reasons = []
        if not probe.get("has_audio"):
            reasons.append("the video has no audio track")
        else:
            reasons.append("no subtitle file next to the video and no subtitle stream inside it")
            if not allow_whisper:
                reasons.append("Whisper was not allowed for this run (--whisper)")
            elif tools.whisper() is None:
                reasons.append("Whisper is not installed")
        result["not_measured"] = "; ".join(reasons)
    result["words_list"] = words
    result.update(metrics(words, duration, language))
    return result

