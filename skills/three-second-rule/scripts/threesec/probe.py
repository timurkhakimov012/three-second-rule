from __future__ import annotations

import json
import math
import re
from fractions import Fraction
from pathlib import Path
from typing import Optional

from .common import TsrError, file_hash, rounded, run, run_bytes

SCENE_THRESHOLD = 0.30
CUT_MERGE_SEC = 0.2
SILENCE_DB = -45
SILENCE_MIN_SEC = 0.3
MOTION_FPS = 4
MOTION_SECONDS = 3.0
MOTION_WIDTH = 64
FLAT_STD = 0.035
DETECT_WIDTH = 160
REGIONS = {
    "top": "crop=iw:ih/2:0:0",
    "bottom": "crop=iw:ih/2:0:ih/2",
    "left": "crop=iw/2:ih:0:0",
    "right": "crop=iw/2:ih:iw/2:0",
}
SCAN_SECONDS = 180.0
WINDOW_STEPS = 2

PTS_TIME = re.compile(r"pts_time:\s*([0-9.]+)")
SCENE_SCORE = re.compile(r"lavfi\.scene_score=([0-9.]+)")
BLACK = re.compile(r"black_start:\s*([0-9.]+)\s+black_end:\s*([0-9.]+)")
FREEZE_START = re.compile(r"freeze_start:\s*([0-9.]+)")
FREEZE_END = re.compile(r"freeze_end:\s*([0-9.]+)")
SILENCE_START = re.compile(r"silence_start:\s*(-?[0-9.]+)")
SILENCE_END = re.compile(r"silence_end:\s*([0-9.]+)")
LOUDNESS = re.compile(r"I:\s+(-?[0-9.]+|-inf) LUFS")
PEAK = re.compile(r"Peak:\s+(-?[0-9.]+|-inf) dBFS")


def ffprobe(video: Path) -> dict:
    result = run([
        "ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(video),
    ])
    try:
        return json.loads(result.stdout)
    except ValueError:
        raise TsrError(f"ffprobe could not read {video.name}") from None


def stream_rotation(stream: dict) -> int:
    for side in stream.get("side_data_list") or []:
        if "rotation" in side:
            try:
                return int(float(side["rotation"])) % 360
            except (TypeError, ValueError):
                pass
    try:
        return int(float((stream.get("tags") or {}).get("rotate", 0))) % 360
    except (TypeError, ValueError):
        return 0


def frame_rate(stream: dict) -> Optional[float]:
    for key in ("avg_frame_rate", "r_frame_rate"):
        value = stream.get(key)
        if value and value not in ("0/0", "0"):
            try:
                rate = float(Fraction(value))
            except (ValueError, ZeroDivisionError):
                continue
            if rate > 0:
                return round(rate, 3)
    return None


def aspect_label(width: int, height: int) -> str:
    known = {"9:16": 9 / 16, "16:9": 16 / 9, "1:1": 1.0, "4:5": 4 / 5, "3:4": 3 / 4, "4:3": 4 / 3}
    ratio = width / height
    for label, value in known.items():
        if abs(ratio - value) / value < 0.02:
            return label
    divisor = math.gcd(width, height) or 1
    return f"{width // divisor}:{height // divisor}"


def video_info(video: Path) -> dict:
    data = ffprobe(video)
    streams = data.get("streams") or []
    visual = next((s for s in streams if s.get("codec_type") == "video"
                   and not (s.get("disposition") or {}).get("attached_pic")), None)
    if visual is None:
        raise TsrError(f"{video.name} has no video stream")
    width, height = int(visual.get("width") or 0), int(visual.get("height") or 0)
    rotation = stream_rotation(visual)
    if rotation in (90, 270):
        width, height = height, width
    duration = None
    for source in (data.get("format") or {}, visual):
        try:
            duration = float(source.get("duration"))
            break
        except (TypeError, ValueError):
            continue
    if not duration or duration <= 0:
        raise TsrError(f"{video.name}: duration is unknown")
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    subtitles = [s for s in streams if s.get("codec_type") == "subtitle"]
    return {
        "width": width,
        "height": height,
        "rotation": rotation,
        "aspect": aspect_label(width, height) if width and height else None,
        "vertical": bool(height > width),
        "fps": frame_rate(visual),
        "duration": round(duration, 3),
        "video_codec": visual.get("codec_name"),
        "has_audio": audio is not None,
        "audio_codec": audio.get("codec_name") if audio else None,
        "subtitle_streams": [
            {"index": s.get("index"), "codec": s.get("codec_name"),
             "language": (s.get("tags") or {}).get("language")} for s in subtitles
        ],
        "size_bytes": int((data.get("format") or {}).get("size") or video.stat().st_size),
    }


def merge_close(times: list[float], gap: float = CUT_MERGE_SEC) -> list[float]:
    merged: list[float] = []
    for value in sorted(times):
        if merged and value - merged[-1] < gap:
            continue
        merged.append(value)
    return merged


def scene_scores(log: str, name: str) -> list[tuple[float, float]]:
    marker = f"[metadata@{name} "
    scores, moment = [], None
    for line in log.splitlines():
        if marker not in line:
            continue
        found = PTS_TIME.search(line)
        if found:
            moment = float(found.group(1))
            continue
        score = SCENE_SCORE.search(line)
        if score and moment is not None:
            scores.append((moment, float(score.group(1))))
            moment = None
    return scores


def cut_times(log: str, name: str, threshold: float) -> list[float]:
    return merge_close([t for t, score in scene_scores(log, name) if score > threshold and t > 0.04])


def video_detectors(video: Path, threshold: float = SCENE_THRESHOLD) -> dict:
    labels = ["full", *REGIONS]
    score = "select='gte(scene,0)',metadata@{name}=mode=print:key=lavfi.scene_score"
    branches = ["[full]blackdetect=d=0.05:pix_th=0.10,freezedetect=n=0.003:d=0.4," + score.format(name="full") + "[out_full]"]
    for name, crop in REGIONS.items():
        branches.append(f"[{name}]{crop}," + score.format(name=name) + f"[out_{name}]")
    graph = f"[0:v:0]scale={DETECT_WIDTH}:-2,split={len(labels)}" + "".join(f"[{n}]" for n in labels) + ";" + ";".join(branches)
    args = ["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-filter_complex", graph]
    for name in labels:
        args += ["-map", f"[out_{name}]", "-f", "null", "-"]
    log = run(args).stderr
    cuts = cut_times(log, "full", threshold)
    in_regions = merge_close([t for name in REGIONS for t in cut_times(log, name, threshold)])
    region_cuts = [t for t in in_regions if all(abs(t - c) >= CUT_MERGE_SEC for c in cuts)]
    blacks = [(float(a), float(b)) for a, b in BLACK.findall(log)]
    freeze_starts = [float(v) for v in FREEZE_START.findall(log)]
    freeze_ends = [float(v) for v in FREEZE_END.findall(log)]
    return {
        "cuts": [round(t, 3) for t in cuts],
        "region_cuts": [round(t, 3) for t in region_cuts],
        "black": [[round(a, 3), round(b, 3)] for a, b in blacks],
        "freezes": pair_intervals(freeze_starts, freeze_ends),
    }


def pair_intervals(starts: list[float], ends: list[float], until: Optional[float] = None) -> list[list[float]]:
    pairs = []
    for number, start in enumerate(starts):
        end = ends[number] if number < len(ends) else until
        pairs.append([round(start, 3), None if end is None else round(end, 3)])
    return pairs


def audio_detectors(video: Path, duration: float) -> dict:
    result = run([
        "ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-map", "0:a:0", "-vn", "-sn", "-dn",
        "-af", f"silencedetect=n={SILENCE_DB}dB:d={SILENCE_MIN_SEC},ebur128=peak=true", "-f", "null", "-",
    ])
    log = result.stderr
    starts = [max(0.0, float(v)) for v in SILENCE_START.findall(log)]
    ends = [float(v) for v in SILENCE_END.findall(log)]
    silences = [[a, b if b is not None else round(duration, 3)] for a, b in pair_intervals(starts, ends, duration)]
    loud = LOUDNESS.findall(log)
    peak = PEAK.findall(log)
    silent_total = sum(max(0.0, b - a) for a, b in silences)
    first_sound = 0.0
    if silences and silences[0][0] <= 0.05:
        first_sound = silences[0][1] if silences[0][1] < duration else None
    return {
        "silences": [[round(a, 3), round(b, 3)] for a, b in silences],
        "first_sound_s": rounded(first_sound, 3),
        "non_silent_share": rounded(max(0.0, 1 - silent_total / duration), 3),
        "integrated_lufs": number_or_none(loud[-1]) if loud else None,
        "true_peak_dbfs": number_or_none(peak[-1]) if peak else None,
    }


def number_or_none(text: str) -> Optional[float]:
    try:
        value = float(text)
    except ValueError:
        return None
    return value if value > -200 else None


def gray_frames(video: Path, width: int, height: int, seconds: float = MOTION_SECONDS,
                fps: int = MOTION_FPS) -> list[bytes]:
    small_height = max(2, int(round(MOTION_WIDTH * height / width / 2)) * 2)
    raw = run_bytes([
        "ffmpeg", "-hide_banner", "-nostats", "-loglevel", "error", "-i", str(video), "-map", "0:v:0", "-an",
        "-t", f"{seconds:.3f}", "-vf", f"fps={fps},scale={MOTION_WIDTH}:{small_height}:flags=area,format=gray",
        "-f", "rawvideo", "-pix_fmt", "gray", "-",
    ])
    size = MOTION_WIDTH * small_height
    return [raw[i:i + size] for i in range(0, len(raw) - size + 1, size)]


def frame_stats(frame: bytes) -> tuple[float, float]:
    count = len(frame)
    mean = sum(frame) / count
    variance = sum((value - mean) ** 2 for value in frame) / count
    return mean / 255, variance ** 0.5 / 255


def frame_difference(first: bytes, second: bytes) -> float:
    return sum(abs(a - b) for a, b in zip(first, second)) / (len(first) * 255)


def most_active(changes: list[dict], cuts: list[float], step: float) -> Optional[dict]:
    clean = [p for p in changes if all(not (p["t"] - step - 0.05 <= c <= p["t"] + 0.05) for c in cuts)]
    by_time = {p["t"]: p["change"] for p in clean}
    best = None
    for point in clean:
        start = round(point["t"] - step, 2)
        if start < 0.5:
            continue
        window = [by_time.get(round(point["t"] + n * step, 2)) for n in range(WINDOW_STEPS)]
        if None in window:
            continue
        value = sum(window) / WINDOW_STEPS
        if best is None or value > best["change"]:
            best = {"start": start, "end": round(start + WINDOW_STEPS * step, 2), "change": round(value, 4)}
    return best


def motion(video: Path, width: int, height: int, duration: float = MOTION_SECONDS,
           cuts: Optional[list[float]] = None) -> dict:
    frames = gray_frames(video, width, height, seconds=min(max(duration, MOTION_SECONDS), SCAN_SECONDS))
    if not frames:
        return {"curve": [], "first_half_second": None, "frame0": None, "most_active": None}
    step = 1 / MOTION_FPS
    changes = []
    for number in range(1, len(frames)):
        changes.append({"t": round(number * step, 2), "change": round(frame_difference(frames[number - 1], frames[number]), 4)})
    curve = [p for p in changes if p["t"] <= MOTION_SECONDS + 1e-6]
    early = [point["change"] for point in curve if point["t"] <= 0.5 + 1e-6]
    mean, std = frame_stats(frames[0])
    return {
        "curve": curve,
        "first_half_second": round(max(early), 4) if early else None,
        "first_three_seconds": round(max(p["change"] for p in curve), 4) if curve else None,
        "frame0": {"brightness": round(mean, 3), "contrast": round(std, 3), "flat": std < FLAT_STD},
        "most_active": most_active(changes, cuts or [], step),
    }


def longest_stretch(changes: list[float], duration: float) -> Optional[dict]:
    edges = [0.0] + sorted(c for c in changes if 0 < c < duration) + [duration]
    pairs = [(a, b) for a, b in zip(edges, edges[1:]) if b - a > 0.001]
    if not pairs:
        return None
    start, end = max(pairs, key=lambda pair: pair[1] - pair[0])
    return {"start": round(start, 3), "end": round(end, 3), "length": round(end - start, 3)}


def shots(cuts: list[float], duration: float) -> list[dict]:
    edges = [0.0] + [c for c in cuts if 0 < c < duration] + [duration]
    return [{"n": n + 1, "start": round(a, 3), "end": round(b, 3), "length": round(b - a, 3)}
            for n, (a, b) in enumerate(zip(edges, edges[1:])) if b - a > 0.001]


def start_interval(intervals: list[list[float]], duration: float) -> float:
    for start, end in intervals:
        if start <= 0.05:
            return round((end if end is not None else duration) - start, 3)
    return 0.0


def measure(video: Path, threshold: float = SCENE_THRESHOLD) -> dict:
    video = video.expanduser().resolve()
    if not video.is_file():
        raise TsrError(f"no such file: {video}")
    info = video_info(video)
    duration = info["duration"]
    detected = video_detectors(video, threshold)
    cuts = detected["cuts"]
    shot_list = shots(cuts, duration)
    audio = audio_detectors(video, duration) if info["has_audio"] else None
    lengths = [s["length"] for s in shot_list]
    region_cuts = detected["region_cuts"]
    return {
        "schema": "tsr/probe@1",
        "video": {"path": str(video), "name": video.name, "hash": file_hash(video)[:16]},
        **info,
        "cuts": cuts,
        "cut_count": len(cuts),
        "first_cut": cuts[0] if cuts else None,
        "cuts_first_3s": len([c for c in cuts if c <= 3.0]),
        "cuts_per_10s": round(len(cuts) / duration * 10, 2),
        "region_cuts": region_cuts,
        "shots": shot_list,
        "longest_shot": max(shot_list, key=lambda s: s["length"]) if shot_list else None,
        "longest_unchanged": longest_stretch(cuts + region_cuts, duration) if region_cuts else None,
        "average_shot": round(sum(lengths) / len(lengths), 3) if lengths else None,
        "black": detected["black"],
        "black_at_start": start_interval(detected["black"], duration),
        "freezes": detected["freezes"],
        "frozen_at_start": start_interval(detected["freezes"], duration),
        "motion": motion(video, info["width"], info["height"], duration, cuts),
        "audio": audio,
        "settings": {"scene_threshold": threshold, "silence_db": SILENCE_DB, "silence_min_s": SILENCE_MIN_SEC},
    }
