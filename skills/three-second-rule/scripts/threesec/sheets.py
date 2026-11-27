from __future__ import annotations

from pathlib import Path
from typing import Optional

from .common import TsrError, load_data
from .image import Image, even, frame_at, frames_every, tile_size

TILE_WIDTH = 240
GAP = 6
COLUMNS = 4
BACKGROUND = (28, 28, 28)
FIRST_STEP = 0.25
FIRST_COUNT = 12
SHOT_OFFSET = 0.12
MAX_SHOT_TILES = 19
ZONE_COLOR = (235, 20, 20)
ZONE_ALPHA = 0.45
ADS_COLOR = (255, 230, 0)
ADS_ALPHA = 0.35
SAFE_LINE = (40, 255, 120)
GRID_SHARE = 1 / 3
GRID_CROP = "crop='min(iw,ih*3/4)':'min(ih,iw*4/3)'"
BLUR = "gblur=sigma=6"


def platforms(names: Optional[list[str]] = None) -> dict:
    known = load_data("platforms.json")["platforms"]
    if not names:
        return known
    unknown = [n for n in names if n not in known]
    if unknown:
        raise TsrError(f"unknown platform {', '.join(unknown)}; known: {', '.join(known)}")
    return {n: known[n] for n in names}


SIDES = ("top", "bottom", "left", "right")


def union_zone(selected: dict, key: str = "safe_zone") -> dict:
    return {side: max(p[key][side] for p in selected.values()) for side in SIDES}


def union_buttons(selected: dict) -> Optional[dict]:
    columns = [p["buttons"] for p in selected.values() if p.get("buttons")]
    if not columns:
        return None
    return {"width": max(c["width"] for c in columns), "from_top": min(c["from_top"] for c in columns)}


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


def small_frames(video: Path, width: int, height: int) -> list[Image]:
    cell_width = even(width * GRID_SHARE)
    cell = frame_at(video, 0.0, cell_width, even(cell_width * 4 / 3), before=GRID_CROP)
    small = Image(width, height, BACKGROUND)
    small.paste(cell, (width - cell.width) // 2, (height - cell.height) // 2)
    blurred = frame_at(video, 0.0, width, height, after=BLUR)
    return [stamp(small, "grid"), stamp(blurred, "blur")]


def first_seconds(video: Path, info: dict, out: Path) -> dict:
    width, height = tile_size(info["width"], info["height"], TILE_WIDTH)
    count = min(FIRST_COUNT, max(1, int(info["duration"] / FIRST_STEP + 1e-6)))
    frames = frames_every(video, FIRST_STEP, count, width, height)
    tiles = []
    for number, frame in enumerate(frames, 1):
        tiles.append({"n": number, "t": round((number - 1) * FIRST_STEP, 2)})
        stamp(frame, f"{number} {seconds_label((number - 1) * FIRST_STEP)}")
    padding = [Image(width, height, BACKGROUND) for _ in range(-len(frames) % COLUMNS)]
    grid(frames + padding + small_frames(video, width, height)).save_jpeg(out)
    return {"file": out.name, "tiles": tiles, "step_s": FIRST_STEP,
            "extras": [{"label": "grid", "what": "frame 0 cropped to 3:4 at profile-grid size"},
                       {"label": "blur", "what": "frame 0 blurred: what reads at a glance"}],
            "how_to_read": "tile n shows the frame at (n - 1) x 0.25 s; the bottom row is frame 0 at grid size and blurred"}


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


def buttons_box(buttons: Optional[dict], zone: dict, width: int, height: int) -> Optional[tuple[int, int, int, int]]:
    if not buttons:
        return None
    column = int(round(buttons["width"] * width))
    top = int(round(buttons["from_top"] * height))
    bottom = int(round(zone["bottom"] * height))
    return (width - column, top, column, max(0, height - top - bottom))


def inside(box: tuple[int, int, int, int], x: int, y: int) -> bool:
    left, top, width, height = box
    return left <= x < left + width and top <= y < top + height


def shade_zones(frame: Image, covered: list, ads: list) -> None:
    for y in range(frame.height):
        for x in range(frame.width):
            if any(inside(box, x, y) for box in covered):
                frame.shade(x, y, 1, 1, ZONE_COLOR, ZONE_ALPHA)
            elif any(inside(box, x, y) for box in ads):
                frame.shade(x, y, 1, 1, ADS_COLOR, ADS_ALPHA)


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
    ads = union_zone(selected, "ads_zone")
    buttons = union_buttons(selected)
    width, height = tile_size(info["width"], info["height"], TILE_WIDTH)
    duration = info["duration"]
    times = sorted({round(min(t, max(0.0, duration - 0.1)), 2) for t in (0.5, 1.5, 2.5, duration / 2)})
    frames, tiles = [], []
    for number, seconds in enumerate(times, 1):
        frame = frame_at(video, seconds, width, height)
        column = buttons_box(buttons, zone, width, height)
        covered = zone_box(zone, width, height) + ([column] if column else [])
        shade_zones(frame, covered, zone_box(ads, width, height))
        safe = safe_rect(zone, width, height)
        frame.outline(*safe, SAFE_LINE, 2)
        stamp(frame, f"#{number} {seconds_label(seconds)}")
        frames.append(frame)
        tiles.append({"n": number, "t": seconds})
    grid(frames).save_jpeg(out)
    return {"file": out.name, "tiles": tiles, "platforms": list(selected), "zone": zone, "buttons": buttons,
            "ads_zone": ads,
            "how_to_read": "red is covered by the app on an ordinary post (edges and the button column); amber is covered "
                           "in ads and under a long caption; keep text and faces off red, and the key words off amber"}


def draw_all(video: Path, probe: dict, folder: Path, names: Optional[list[str]] = None) -> dict:
    return {
        "first_3s": first_seconds(video, probe, folder / "first-3s.jpg"),
        "shots": shot_sheet(video, probe, probe.get("cuts") or [], folder / "shots.jpg"),
        "safe_zones": safe_zone_sheet(video, probe, folder / "safe-zones.jpg", names),
    }
