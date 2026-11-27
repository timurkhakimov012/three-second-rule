from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Optional, Sequence

VERSION = "0.2.0"
SKILL_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = SKILL_DIR / "data"
DEFAULT_KEEP_DAYS = 30
COMMAND_TIMEOUT = 600


class TsrError(Exception):
    pass


class ToolMissing(TsrError):
    def __init__(self, tool: str, hint: str = ""):
        self.tool = tool
        message = f"{tool} is not installed"
        if hint:
            message += f": {hint}"
        super().__init__(message)


def home() -> Path:
    configured = os.environ.get("TSR_HOME")
    root = Path(configured).expanduser() if configured else Path.home() / ".cache" / "three-second-rule"
    root.mkdir(parents=True, exist_ok=True)
    return root


def runs_dir() -> Path:
    path = home() / "runs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def keep_days() -> int:
    raw = os.environ.get("TSR_KEEP_DAYS", "")
    try:
        return max(0, int(raw)) if raw else DEFAULT_KEEP_DAYS
    except ValueError:
        return DEFAULT_KEEP_DAYS


def prune_runs(days: Optional[int] = None) -> list[str]:
    limit = keep_days() if days is None else days
    if limit <= 0:
        return []
    cutoff = time.time() - limit * 86400
    removed = []
    for run in runs_dir().iterdir():
        if run.is_dir() and run.stat().st_mtime < cutoff:
            shutil.rmtree(run, ignore_errors=True)
            removed.append(run.name)
    return removed


def load_data(name: str) -> Any:
    return read_json(DATA_DIR / name)


def read_json(path: Path) -> Any:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def read_json_or(path: Path, default: Any) -> Any:
    try:
        return read_json(path)
    except FileNotFoundError:
        return default


def write_json(path: Path, value: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=".tmp-", suffix=".json")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            json.dump(value, out, ensure_ascii=False, indent=2)
            out.write("\n")
        os.replace(temporary, path)
    except BaseException:
        if os.path.exists(temporary):
            os.unlink(temporary)
        raise
    return path


def write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=".tmp-")
    with os.fdopen(handle, "w", encoding="utf-8") as out:
        out.write(text)
    os.replace(temporary, path)
    return path


def run(args: Sequence[str], timeout: int = COMMAND_TIMEOUT, check: bool = True) -> subprocess.CompletedProcess:
    tool = args[0]
    if shutil.which(tool) is None:
        raise ToolMissing(tool)
    try:
        result = subprocess.run(
            list(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.TimeoutExpired:
        raise TsrError(f"{tool} took longer than {timeout} s") from None
    if check and result.returncode != 0:
        raise TsrError(f"{tool} failed: {last_lines(result.stderr)}")
    return result


def run_bytes(args: Sequence[str], timeout: int = COMMAND_TIMEOUT) -> bytes:
    tool = args[0]
    if shutil.which(tool) is None:
        raise ToolMissing(tool)
    try:
        result = subprocess.run(list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise TsrError(f"{tool} took longer than {timeout} s") from None
    if result.returncode != 0:
        raise TsrError(f"{tool} failed: {last_lines(result.stderr.decode('utf-8', 'replace'))}")
    return result.stdout


def last_lines(text: str, count: int = 3) -> str:
    lines = [line for line in text.strip().splitlines() if line.strip()]
    return " | ".join(lines[-count:]) if lines else "no output"


def file_hash(path: Path, limit: int = 16 * 1024 * 1024) -> str:
    digest = hashlib.sha256()
    size = path.stat().st_size
    digest.update(str(size).encode())
    with open(path, "rb") as handle:
        digest.update(handle.read(limit))
        if size > limit:
            handle.seek(max(limit, size - limit))
            digest.update(handle.read(limit))
    return digest.hexdigest()


def slug(text: str, limit: int = 40) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (cleaned[:limit].strip("-")) or "video"


def now() -> datetime:
    return datetime.now(timezone.utc)


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_time(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    text = str(value).strip()
    if re.fullmatch(r"\d{8}", text):
        return datetime(int(text[:4]), int(text[4:6]), int(text[6:8]), tzinfo=timezone.utc)
    if re.fullmatch(r"\d+(\.\d+)?", text):
        return datetime.fromtimestamp(float(text), tz=timezone.utc)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def middle(values: Iterable[float]) -> Optional[float]:
    items = [v for v in values if v is not None]
    return float(median(items)) if items else None


def rounded(value: Optional[float], digits: int = 2) -> Optional[float]:
    return None if value is None else round(float(value), digits)


def plural(count: int, word: str) -> str:
    return f"{count} {word}" if count == 1 else f"{count} {word}s"


def run_path(run_id: str) -> Path:
    candidate = Path(run_id).expanduser()
    if candidate.is_dir() and (candidate / "run.json").is_file():
        return candidate
    path = runs_dir() / run_id
    if not (path / "run.json").is_file():
        raise TsrError(f"no run called {run_id}; `tsr runs` lists them")
    return path


def is_url(text: str) -> bool:
    return bool(re.match(r"^https?://[^\s]+$", text.strip()))
