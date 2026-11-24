from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from .checks import DECIDED, FAIL, SYMBOLS, WARN, config
from .common import read_json, read_json_or, run_path, runs_dir, write_text

COMPARE_METRICS = (
    ("first word", ("speech", "first_word_s"), "s"),
    ("first cut", ("probe", "first_cut"), "s"),
    ("cuts per 10 s", ("probe", "cuts_per_10s"), ""),
    ("black at start", ("probe", "black_at_start"), "s"),
    ("loudness", ("probe", "audio", "integrated_lufs"), "LUFS"),
    ("length", ("probe", "duration"), "s"),
)


def dig(body: dict, path: tuple) -> Optional[float]:
    value = body
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return value if isinstance(value, (int, float)) else None


def bundle(folder: Path) -> dict:
    return {
        "run": read_json(folder / "run.json"),
        "probe": read_json_or(folder / "probe.json", {}),
        "speech": read_json_or(folder / "speech.json", {}),
        "checks": read_json_or(folder / "checks.json", {}),
    }


def compare(first: str, second: str) -> dict:
    a, b = bundle(run_path(first)), bundle(run_path(second))
    before = {c["id"]: c for c in a["checks"].get("checks", [])}
    after = {c["id"]: c for c in b["checks"].get("checks", [])}
    changes, unchecked = [], []
    for check_id, row in after.items():
        old = before.get(check_id)
        if old and old["status"] in DECIDED and row["status"] not in DECIDED:
            unchecked.append(check_id)
            continue
        if old and old["status"] != row["status"]:
            changes.append({"id": check_id, "title": row["title"], "before": old["status"], "after": row["status"],
                            "value_before": old.get("value"), "value_after": row.get("value")})
    metrics = []
    for name, path, unit in COMPARE_METRICS:
        old, new = dig(a, path), dig(b, path)
        if old is not None or new is not None:
            metrics.append({"name": name, "before": old, "after": new, "unit": unit})
    return {"before": a["run"]["id"], "after": b["run"]["id"],
            "summary_before": a["checks"].get("summary", {}).get("line"),
            "summary_after": b["checks"].get("summary", {}).get("line"),
            "changes": changes, "not_checked_after": unchecked, "metrics": metrics}


def compare_text(result: dict) -> str:
    lines = [f"Before: {result['summary_before']}  ({result['before']})",
             f"After:  {result['summary_after']}  ({result['after']})"]
    for change in result["changes"]:
        lines.append(f"  {change['id']:3} {change['title']}: {change['before']} -> {change['after']}"
                     f"  ({change['value_before']} -> {change['value_after']})")
    if not result["changes"]:
        lines.append("  No check changed its status.")
    if result["not_checked_after"]:
        lines.append(f"  Not checked yet in the new run: {', '.join(result['not_checked_after'])} "
                     "(write its notes.json and run tsr check)")
    for metric in result["metrics"]:
        lines.append(f"  {metric['name']}: {format_value(metric['before'], metric['unit'])} -> "
                     f"{format_value(metric['after'], metric['unit'])}")
    return "\n".join(lines)


def format_value(value: Optional[float], unit: str) -> str:
    if value is None:
        return "n/a"
    return f"{value:.2f} {unit}".strip()


def list_runs(limit: int = 20) -> list[dict]:
    rows = []
    for folder in runs_dir().iterdir():
        info = read_json_or(folder / "run.json", None)
        if not info or info.get("part_of"):
            continue
        outcome = read_json_or(folder / "checks.json", {})
        rows.append({"id": info["id"], "kind": info["kind"], "updated": info.get("updated_at") or info.get("created_at"),
                     "subject": (info.get("video") or {}).get("name") or (info.get("post") or {}).get("url") or "",
                     "summary": (outcome.get("summary") or {}).get("line", ""), "mtime": folder.stat().st_mtime})
    rows.sort(key=lambda r: r["mtime"], reverse=True)
    for row in rows:
        row.pop("mtime")
    return rows[:limit]


def runs_text(rows: list[dict]) -> str:
    if not rows:
        return "No runs yet."
    return "\n".join(f"{r['id']:48} {r['kind']:9} {r['updated'] or '':21} {r['summary']}" for r in rows)


def check_markdown(folder: Path, files_dir: str) -> str:
    data = bundle(folder)
    outcome, probe = data["checks"], data["probe"]
    conf = config()
    lines = [f"# Preflight: {data['run']['video']['name']}", "",
             f"**{outcome['summary']['line']}**", "",
             f"{probe.get('duration', 0):.1f} s · {probe.get('width')}x{probe.get('height')} ({probe.get('aspect')}) · "
             f"{probe.get('cut_count')} cuts · checked {data['run'].get('updated_at', '')}", ""]
    fixes = [r for r in outcome["checks"] if r["status"] in (FAIL, WARN)]
    if fixes:
        lines += ["## Fix first", ""]
        ordered = sorted(fixes, key=lambda r: (r["status"] != FAIL, list(conf["sections"]).index(r["section"])))
        for number, row in enumerate(ordered, 1):
            lines.append(f"{number}. **{row['id']} {row['title']}** ({row['value']}). {row['fix']}")
        lines.append("")
    for section, title in conf["sections"].items():
        rows = [r for r in outcome["checks"] if r["section"] == section]
        if not rows:
            continue
        lines += [f"## {title}", "", "| | Check | Result | Expected | Evidence |", "|---|---|---|---|---|"]
        for row in rows:
            value = str(row.get("value") or "").replace("|", "/")
            detail = str(row.get("detail") or "").replace("|", "/")
            lines.append(f"| {SYMBOLS[row['status']].strip()} | {row['id']} {row['title']} | {value} | "
                         f"{row.get('expected') or ''} | {detail} |")
        lines.append("")
    lines += ["## Frames", "",
              f"![First 3 seconds, one frame every 0.25 s]({files_dir}/first-3s.jpg)", "",
              f"![A frame after each cut]({files_dir}/shots.jpg)", ""]
    if (folder / "safe-zones.jpg").is_file():
        lines += [f"![Safe zones]({files_dir}/safe-zones.jpg)", ""]
    findings = folder / "findings.md"
    if findings.is_file():
        lines += ["## Reading", "", findings.read_text(encoding="utf-8").strip(), ""]
    decided = sum(1 for r in outcome["checks"] if r["status"] in DECIDED)
    lines += ["---", "",
              f"{decided} checks decided. Thresholds are heuristics with named sources (data/checks.json), "
              "not predictions. Made with three-second-rule."]
    return "\n".join(lines) + "\n"


def teardown_markdown(folder: Path, files_dir: str) -> str:
    info = read_json(folder / "run.json")
    scored = read_json(folder / "baseline.json")
    lines = [f"# Teardown: {info['post'].get('url') or info['post']['id']}", "", f"**{scored['verdict']}**", ""]
    for note in scored["notes"]:
        lines.append(f"- {note}")
    lines += ["", "## Watched", "", "| Role | Post | Length | First word | First cut | Cuts/10 s |", "|---|---|---|---|---|---|"]
    for post_id, item in info["watched"].items():
        if "folder" not in item:
            lines.append(f"| {item['role']} | {post_id} | not read: {item.get('reason', '')} | | | |")
            continue
        first_word = f"{item['first_word_s']:.2f} s" if item.get("first_word_s") is not None else "n/a"
        first_cut = f"{item['first_cut']:.2f} s" if item.get("first_cut") is not None else "none"
        lines.append(f"| {item['role']} | {post_id} | {item['duration']:.1f} s | {first_word} | {first_cut} | "
                     f"{item['cuts_per_10s']} |")
        lines += ["", f"![{item['role']} {post_id}]({files_dir}/{post_id}-first-3s.jpg)", ""]
    recipe = read_json_or(folder / "recipe.json", None)
    if recipe:
        lines += ["## Recipe", "", f"**{recipe.get('name')}**: {recipe.get('hook_pattern', '')}", "",
                  "| At | Beat | What |", "|---|---|---|"]
        for beat in recipe.get("beats", []):
            lines.append(f"| {beat['at']:.1f} s | {beat['what']}{' (cut)' if beat.get('cut') else ''} | {beat.get('text', '')} |")
        lines.append("")
    findings = folder / "findings.md"
    if findings.is_file():
        lines += ["## Reading", "", findings.read_text(encoding="utf-8").strip(), ""]
    lines += ["---", "", "Frames are small stills for study, each from the post linked above. Made with three-second-rule."]
    return "\n".join(lines) + "\n"


def write_report(run: str, out: Path) -> Path:
    folder = run_path(run)
    info = read_json(folder / "run.json")
    out = out.expanduser()
    if out.is_dir() or not out.suffix:
        out.mkdir(parents=True, exist_ok=True)
        out = out / f"{info['id']}.md"
    files = out.parent / f"{out.stem}-files"
    files.mkdir(parents=True, exist_ok=True)
    if info["kind"] == "check":
        for name in ("first-3s.jpg", "shots.jpg", "safe-zones.jpg"):
            if (folder / name).is_file():
                shutil.copy2(folder / name, files / name)
        text = check_markdown(folder, files.name)
    elif info["kind"] == "teardown":
        for post_id, item in info["watched"].items():
            sheet = Path(item.get("folder", "")) / "first-3s.jpg"
            if sheet.is_file():
                shutil.copy2(sheet, files / f"{post_id}-first-3s.jpg")
        text = teardown_markdown(folder, files.name)
    else:
        raise ValueError(f"no report for runs of kind {info['kind']}")
    return write_text(out, text)
