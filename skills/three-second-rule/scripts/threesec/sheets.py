from __future__ import annotations

from pathlib import Path
from typing import Optional

from .common import TsrError, load_data
from .image import Image, frame_at, frames_every, tile_size

TILE_WIDTH = 240
GAP = 6
COLUMNS = 4
BACKGROUND = (28, 28, 28)
FIRST_STEP = 0.25
FIRST_COUNT = 12
SHOT_OFFSET = 0.12
MAX_SHOT_TILES = 19
ZONE_COLOR = (230, 40, 40)
ZONE_ALPHA = 0.45
SAFE_LINE = (40, 255, 120)


def platforms(names: Optional[list[str]] = None) -> dict:
    known = load_data("platforms.json")["platforms"]
    if not names:
        return known
    unknown = [n for n in names if n not in known]
    if unknown:
        raise TsrError(f"unknown platform {', '.join(unknown)}; known: {', '.join(known)}")
    return {n: known[n] for n in names}


def union_zone(selected: dict) -> dict:
    sides = ("top", "bottom", "left", "right")
    return {side: max(p["safe_zone"][side] for p in selected.values()) for side in sides}


def grid(tiles: list[Image], columns: int = COLUMNS) -> Image:
    if not tiles:
        raise TsrError("no frames to draw")
    width, height = tiles[0].width, tiles[0].height
    rows = (len(tiles) + columns - 1) // columns
    used_columns = min(columns, len(tiles))
    sheet = Image(used_columns * width + (used_columns + 1) * GAP, rows * height + (rows + 1) * GAP, BACKGROUND)
    for number, tile in enumerate(tiles):
        row, column = divmod(number, columns)
        sheet.paste(tile, GAP + column * (width + GAP), GAP + row * (height + GAP))
    return sheet


def stamp(tile: Image, label: str) -> Image:
    tile.text(4, 4, label, scale=3)
    return tile


def seconds_label(seconds: float) -> str:
    return f"{seconds:.2f}s"


def first_seconds(video: Path, info: dict, out: Path) -> dict:
    width, height = tile_size(info["width"], info["height"], TILE_WIDTH)
    count = min(FIRST_COUNT, max(1, int(info["duration"] / FIRST_STEP + 1e-6)))
    frames = frames_every(video, FIRST_STEP, count, width, height)
    tiles = []
    for number, frame in enumerate(frames, 1):
        tiles.append({"n": number, "t": round((number - 1) * FIRST_STEP, 2)})
        stamp(frame, f"{number} {seconds_label((number - 1) * FIRST_STEP)}")
    grid(frames).save_jpeg(out)
    return {"file": out.name, "tiles": tiles, "step_s": FIRST_STEP,
            "how_to_read": "tile n shows the frame at (n - 1) x 0.25 s"}


def shot_times(cuts: list[float], duration: float) -> tuple[list[dict], bool]:
    picks = [{"t": 0.0, "kind": "start"}]
    inner = [c for c in cuts if c + SHOT_OFFSET < duration - 0.05]
    sampled = len(inner) > MAX_SHOT_TILES
    if sampled:
        step = len(inner) / MAX_SHOT_TILES
        inner = [inner[int(i * step)] for i in range(MAX_SHOT_TILES)]
    picks += [{"t": round(c + SHOT_OFFSET, 3), "kind": "cut", "cut": c} for c in inner]
    picks.append({"t": round(max(0.0, duration - 0.08), 3), "kind": "end"})
    return picks, sampled


def shot_sheet(video: Path, info: dict, cuts: list[float], out: Path) -> dict:
    width, height = tile_size(info["width"], info["height"], TILE_WIDTH)
    picks, sampled = shot_times(cuts, info["duration"])
    frames = []
    for number, pick in enumerate(picks, 1):
        pick["n"] = number
        label = "end" if pick["kind"] == "end" else f"#{number}"
        frames.append(stamp(frame_at(video, pick["t"], width, height), f"{label} {seconds_label(pick['t'])}"))
    grid(frames).save_jpeg(out)
    return {"file": out.name, "tiles": picks, "sampled": sampled,
            "how_to_read": "tile 1 is the first frame, each next tile is 0.12 s after a cut, the last is the end"}


def zone_box(zone: dict, width: int, height: int) -> list[tuple[int, int, int, int]]:
    top = int(round(zone["top"] * height))
    bottom = int(round(zone["bottom"] * height))
    left = int(round(zone["left"] * width))
    right = int(round(zone["right"] * width))
    return [
        (0, 0, width, top),
        (0, height - bottom, width, bottom),
        (0, top, left, height - top - bottom),
        (width - right, top, right, height - top - bottom),
    ]


def safe_rect(zone: dict, width: int, height: int) -> tuple[int, int, int, int]:
    top = int(round(zone["top"] * height))
    left = int(round(zone["left"] * width))
    return (left, top, width - left - int(round(zone["right"] * width)),
            height - top - int(round(zone["bottom"] * height)))


def safe_zone_sheet(video: Path, info: dict, out: Path, names: Optional[list[str]] = None) -> dict:
    selected = platforms(names)
    if not info.get("vertical") or info.get("aspect") != "9:16":
        return {"file": None, "skipped": f"the video is {info.get('aspect')}, safe zones are drawn for 9:16 only",
                "platforms": list(selected)}
    zone = union_zone(selected)
    width, height = tile_size(info["width"], info["height"], TILE_WIDTH)
    duration = info["duration"]
    times = sorted({round(min(t, max(0.0, duration - 0.1)), 2) for t in (0.5, 1.5, 2.5, duration / 2)})
    frames, tiles = [], []
    for number, seconds in enumerate(times, 1):
        frame = frame_at(video, seconds, width, height)
        for box in zone_box(zone, width, height):
            frame.shade(*box, ZONE_COLOR, ZONE_ALPHA)
        safe = safe_rect(zone, width, height)
        frame.outline(*safe, SAFE_LINE, 2)
        stamp(frame, f"#{number} {seconds_label(seconds)}")
        frames.append(frame)
        tiles.append({"n": number, "t": seconds})
    grid(frames).save_jpeg(out)
    return {"file": out.name, "tiles": tiles, "platforms": list(selected), "zone": zone,
            "how_to_read": "red areas are covered by the app's interface; keep text and faces inside the green frame"}


def draw_all(video: Path, probe: dict, folder: Path, names: Optional[list[str]] = None) -> dict:
    return {
        "first_3s": first_seconds(video, probe, folder / "first-3s.jpg"),
        "shots": shot_sheet(video, probe, probe.get("cuts") or [], folder / "shots.jpg"),
        "safe_zones": safe_zone_sheet(video, probe, folder / "safe-zones.jpg", names),
    }
