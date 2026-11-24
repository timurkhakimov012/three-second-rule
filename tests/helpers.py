from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "skills" / "three-second-rule" / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

HAS_FFMPEG = shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
needs_ffmpeg = unittest.skipUnless(HAS_FFMPEG, "ffmpeg is not installed")

WIDTH, HEIGHT, RATE = 180, 320, 25


def segment_source(kind: str, seconds: float) -> str:
    if kind == "pattern":
        return f"testsrc2=s={WIDTH}x{HEIGHT}:r={RATE}:d={seconds}"
    return f"color=c={kind}:s={WIDTH}x{HEIGHT}:r={RATE}:d={seconds}"


def make_video(path: Path, segments: list[tuple[str, float]], quiet: list[tuple[float, float]] = (),
               audio: bool = True, size: tuple[int, int] = (WIDTH, HEIGHT)) -> Path:
    args = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error"]
    for kind, seconds in segments:
        source = segment_source(kind, seconds).replace(f"{WIDTH}x{HEIGHT}", f"{size[0]}x{size[1]}")
        args += ["-f", "lavfi", "-i", source]
    total = sum(seconds for _, seconds in segments)
    labels = "".join(f"[{n}:v]" for n in range(len(segments)))
    graph = f"{labels}concat=n={len(segments)}:v=1:a=0,format=yuv420p[v]"
    if audio:
        silent = "+".join(f"between(t,{a},{b})" for a, b in quiet) or "0"
        args += ["-f", "lavfi", "-i",
                 f"aevalsrc='if({silent},0,0.25*sin(2*PI*440*t))':s=44100:d={total}"]
        args += ["-filter_complex", graph, "-map", "[v]", "-map", f"{len(segments)}:a", "-c:a", "aac"]
    else:
        args += ["-filter_complex", graph, "-map", "[v]"]
    args += ["-c:v", "libx264", "-preset", "ultrafast", "-g", "25", "-t", str(total), str(path)]
    subprocess.run(args, check=True)
    return path


class TempDir(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="tsr-test-"))
        self.home = self.tmp / "home"
        import os
        self._old_home = os.environ.get("TSR_HOME")
        os.environ["TSR_HOME"] = str(self.home)

    def tearDown(self) -> None:
        import os
        if self._old_home is None:
            os.environ.pop("TSR_HOME", None)
        else:
            os.environ["TSR_HOME"] = self._old_home
        shutil.rmtree(self.tmp, ignore_errors=True)
