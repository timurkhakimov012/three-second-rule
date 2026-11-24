from __future__ import annotations

import tempfile
from pathlib import Path

from .common import run, run_bytes

GLYPHS = {
    "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
    "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
    "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
    "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
    "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
    "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
    "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
    "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
    "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
    "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
    ".": ["00000", "00000", "00000", "00000", "00000", "01100", "01100"],
    ":": ["00000", "01100", "01100", "00000", "01100", "01100", "00000"],
    "-": ["00000", "00000", "00000", "11111", "00000", "00000", "00000"],
    "#": ["01010", "01010", "11111", "01010", "11111", "01010", "01010"],
    "s": ["00000", "00000", "01111", "10000", "01110", "00001", "11110"],
    "e": ["00000", "00000", "01110", "10001", "11111", "10000", "01110"],
    "n": ["00000", "00000", "10110", "11001", "10001", "10001", "10001"],
    "d": ["00001", "00001", "01101", "10011", "10001", "10011", "01101"],
    "c": ["00000", "00000", "01110", "10000", "10000", "10001", "01110"],
    "u": ["00000", "00000", "10001", "10001", "10001", "10011", "01101"],
    "t": ["01000", "01000", "11100", "01000", "01000", "01001", "00110"],
    " ": ["00000"] * 7,
}
GLYPH_W, GLYPH_H = 5, 7


class Image:
    def __init__(self, width: int, height: int, color: tuple[int, int, int] = (0, 0, 0)):
        self.width = width
        self.height = height
        self.pixels = bytearray(bytes(color) * (width * height))

    @classmethod
    def from_rgb(cls, width: int, height: int, data: bytes) -> "Image":
        image = cls(width, height)
        expected = width * height * 3
        image.pixels[:min(expected, len(data))] = data[:expected]
        return image

    def paste(self, other: "Image", x: int, y: int) -> None:
        for row in range(other.height):
            target_y = y + row
            if not 0 <= target_y < self.height:
                continue
            left = max(0, x)
            right = min(self.width, x + other.width)
            if right <= left:
                continue
            source = (row * other.width + (left - x)) * 3
            target = (target_y * self.width + left) * 3
            self.pixels[target:target + (right - left) * 3] = other.pixels[source:source + (right - left) * 3]

    def fill(self, x: int, y: int, width: int, height: int, color: tuple[int, int, int]) -> None:
        left, right = max(0, x), min(self.width, x + width)
        if right <= left:
            return
        line = bytes(color) * (right - left)
        for target_y in range(max(0, y), min(self.height, y + height)):
            start = (target_y * self.width + left) * 3
            self.pixels[start:start + len(line)] = line

    def shade(self, x: int, y: int, width: int, height: int, color: tuple[int, int, int], alpha: float) -> None:
        keep = 1 - alpha
        tint = [c * alpha for c in color]
        for target_y in range(max(0, y), min(self.height, y + height)):
            for target_x in range(max(0, x), min(self.width, x + width)):
                index = (target_y * self.width + target_x) * 3
                for channel in range(3):
                    self.pixels[index + channel] = int(self.pixels[index + channel] * keep + tint[channel])

    def outline(self, x: int, y: int, width: int, height: int, color: tuple[int, int, int], thickness: int = 2) -> None:
        self.fill(x, y, width, thickness, color)
        self.fill(x, y + height - thickness, width, thickness, color)
        self.fill(x, y, thickness, height, color)
        self.fill(x + width - thickness, y, thickness, height, color)

    def text(self, x: int, y: int, label: str, scale: int = 3, color: tuple[int, int, int] = (255, 255, 255),
             background: tuple[int, int, int] = (0, 0, 0)) -> None:
        characters = [c for c in label.lower() if c in GLYPHS]
        width = (len(characters) * (GLYPH_W + 1) + 1) * scale
        height = (GLYPH_H + 2) * scale
        self.fill(x, y, width, height, background)
        for number, character in enumerate(characters):
            glyph = GLYPHS[character]
            left = x + (1 + number * (GLYPH_W + 1)) * scale
            for row, bits in enumerate(glyph):
                for column, bit in enumerate(bits):
                    if bit == "1":
                        self.fill(left + column * scale, y + (1 + row) * scale, scale, scale, color)

    def ppm(self) -> bytes:
        return f"P6\n{self.width} {self.height}\n255\n".encode() + bytes(self.pixels)

    def save_jpeg(self, path: Path, quality: int = 4) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(suffix=".ppm", dir=path.parent, delete=False) as handle:
            handle.write(self.ppm())
            temporary = Path(handle.name)
        try:
            run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(temporary),
                 "-q:v", str(quality), str(path)])
        finally:
            temporary.unlink(missing_ok=True)
        return path


def even(value: float) -> int:
    return max(2, int(round(value / 2)) * 2)


def tile_size(width: int, height: int, tile_width: int) -> tuple[int, int]:
    return tile_width, even(tile_width * height / width)


def frame_at(video: Path, seconds: float, width: int, height: int) -> Image:
    raw = run_bytes([
        "ffmpeg", "-hide_banner", "-nostats", "-loglevel", "error", "-ss", f"{max(0.0, seconds):.3f}",
        "-i", str(video), "-map", "0:v:0", "-frames:v", "1", "-vf", f"scale={width}:{height}:flags=area",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
    ])
    if not raw:
        raw = run_bytes([
            "ffmpeg", "-hide_banner", "-nostats", "-loglevel", "error", "-sseof", "-0.2", "-i", str(video),
            "-map", "0:v:0", "-frames:v", "1", "-vf", f"scale={width}:{height}:flags=area",
            "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
        ])
    return Image.from_rgb(width, height, raw)


def frames_every(video: Path, step: float, count: int, width: int, height: int) -> list[Image]:
    raw = run_bytes([
        "ffmpeg", "-hide_banner", "-nostats", "-loglevel", "error", "-i", str(video), "-map", "0:v:0", "-an",
        "-t", f"{step * count:.3f}", "-vf", f"fps={1 / step:.6f}:start_time=0,scale={width}:{height}:flags=area",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-",
    ])
    size = width * height * 3
    return [Image.from_rgb(width, height, raw[i:i + size]) for i in range(0, len(raw) - size + 1, size)][:count]
