from __future__ import annotations

from datetime import datetime
from typing import Optional

from .common import iso, middle, now, parse_time, rounded

SETTLE_DAYS = {"x": 3, "threads": 3}
DEFAULT_SETTLE_DAYS = 7
MIN_POSTS = 8
HIT, FLOP = 2.0, 0.5
ORDINARY = (0.75, 1.33)


def settle_days(platform: str) -> int:
    return SETTLE_DAYS.get(platform, DEFAULT_SETTLE_DAYS)


def age_days(post: dict, read_at: datetime) -> Optional[float]:
    published = parse_time(post.get("published_at"))
    return None if published is None else (read_at - published).total_seconds() / 86400


def label(ratio: Optional[float]) -> Optional[str]:
    if ratio is None:
        return None
    if ratio >= HIT:
        return "hit"
    if ratio <= FLOP:
        return "flop"
    if ORDINARY[0] <= ratio <= ORDINARY[1]:
        return "ordinary"
    return "above usual" if ratio > 1 else "below usual"


def metric_of(posts: list[dict]) -> str:
    with_views = sum(1 for p in posts if p.get("views") is not None)
    return "views" if posts and with_views / len(posts) >= 0.8 else "likes"


def usual(target_id: str, posts: list[dict], metric: str, read_at: datetime, platform: str) -> dict:
    settled, growing, undated = [], 0, 0
    for post in posts:
        if post["id"] == target_id or post.get(metric) is None:
            continue
        age = age_days(post, read_at)
        if age is None:
            undated += 1
            settled.append(post[metric])
        elif age >= settle_days(platform):
            settled.append(post[metric])
        else:
            growing += 1
    value = middle(settled)
    return {"value": value, "from_posts": len(settled), "left_out_still_growing": growing, "undated": undated,
            "weak_basis": len(settled) < MIN_POSTS, "metric": metric}


def score(target: dict, posts: list[dict], read_at: Optional[datetime] = None) -> dict:
    read_at = read_at or now()
    everyone = [target] + [p for p in posts if p["id"] != target["id"]]
    metric = metric_of(everyone)
    platform = target.get("platform", "")
    base = usual(target["id"], everyone, metric, read_at, platform)
    rows = []
    for post in everyone:
        own = usual(post["id"], everyone, metric, read_at, platform)
        value = post.get(metric)
        ratio = value / own["value"] if value is not None and own["value"] else None
        age = age_days(post, read_at)
        young = age is not None and age < settle_days(platform)
        rows.append({
            "id": post["id"], "url": post.get("url"), "published_at": post.get("published_at"),
            metric: value, "ratio": rounded(ratio, 2), "label": None if young else label(ratio),
            "still_growing": young, "title": (post.get("title") or "")[:120],
        })
    target_row = rows[0]
    picks = pick_comparisons(rows[1:])
    notes = []
    if base["weak_basis"]:
        notes.append(f"weak basis: the usual comes from {base['from_posts']} posts (at least {MIN_POSTS} wanted)")
    if base["undated"]:
        notes.append(f"{base['undated']} posts have no date; their age could not be checked")
    if target_row["still_growing"]:
        notes.append("the post is still growing: its ratio is a floor, it will only rise")
    if metric != "views":
        notes.append("fewer than 8 in 10 posts show views: measured on likes instead")
    ranked = sorted((r for r in rows if r["ratio"] is not None and not r["still_growing"]),
                    key=lambda r: r["ratio"], reverse=True)
    position = next((n for n, r in enumerate(ranked, 1) if r["id"] == target["id"]), None)
    return {
        "schema": "tsr/baseline@1",
        "read_at": iso(read_at),
        "metric": metric,
        "usual": base,
        "target": {**target_row, "rank": position, "of": len(ranked)},
        "verdict": verdict(target_row, base),
        "picks": picks,
        "posts": rows,
        "notes": notes,
        "rules": {"hit": HIT, "flop": FLOP, "settle_days": settle_days(platform), "min_posts": MIN_POSTS},
    }


def verdict(row: dict, base: dict) -> str:
    if row["ratio"] is None:
        return "not measured: the usual or the post's own number is unknown"
    prefix = "at least " if row["still_growing"] else ""
    strength = f"{prefix}{row['ratio']:.1f}x its creator's usual ({base['value']:,.0f} {base['metric']})"
    if row["still_growing"]:
        return strength + ", still growing"
    return strength + f": {row['label']}"


def pick_comparisons(rows: list[dict]) -> dict:
    scored = [r for r in rows if r["ratio"] is not None and not r["still_growing"]]
    ordinary = sorted((r for r in scored if ORDINARY[0] <= r["ratio"] <= ORDINARY[1]),
                      key=lambda r: abs(r["ratio"] - 1))[:2]
    flops = sorted((r for r in scored if r["ratio"] <= FLOP), key=lambda r: r["ratio"])[:2]
    if not flops:
        flops = sorted((r for r in scored if r["ratio"] < ORDINARY[0]), key=lambda r: r["ratio"])[:1]
    return {"ordinary": [r["id"] for r in ordinary], "flops": [r["id"] for r in flops]}


def text_report(result: dict) -> str:
    lines = [f"Verdict: {result['verdict']}"]
    base = result["usual"]
    if base["value"] is not None:
        lines.append(f"Usual: {base['value']:,.0f} {base['metric']} (median of {base['from_posts']} settled posts)")
    target = result["target"]
    if target.get("rank"):
        lines.append(f"Rank: {target['rank']} of {target['of']} scored posts")
    for note in result["notes"]:
        lines.append(f"Note: {note}")
    picks = result["picks"]
    lines.append(f"Watch next to it: ordinary {', '.join(picks['ordinary']) or 'none'}; "
                 f"flops {', '.join(picks['flops']) or 'none'}")
    return "\n".join(lines)
