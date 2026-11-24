from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from .baseline import HIT, settle_days
from .common import TsrError, iso, middle, now, parse_time, read_json, read_json_or, rounded, slug, write_json

WINDOW_DAYS = 30
RECENT_EXTRA_DAYS = 30
MIN_OWN_POSTS = 8
MIN_CREATORS = 3
MIN_SCORED = 20
NICHE_COMMON = 0.40
ACCOUNT_COMMON = 0.15
RISING, FADING = 1.33, 0.75
MIN_HALF = 3


def creator_key(posts_file: Path) -> str:
    return posts_file.stem


def load_creators(folder: Path) -> dict[str, dict]:
    creators = {}
    for path in sorted((folder / "creators").glob("*.json")):
        body = read_json(path)
        creators[creator_key(path)] = body
    if not creators:
        raise TsrError(f"no creators in {folder / 'creators'}; add them with `tsr creator <url> --into {folder}`")
    return creators


def save_creator(folder: Path, platform: str, handle: str, creator: dict, posts: list[dict]) -> Path:
    path = folder / "creators" / f"{platform}-{slug(handle, 60)}.json"
    write_json(path, {"creator": creator, "posts": posts})
    return path


def score_creator(key: str, body: dict, read_at: datetime, window_start: datetime) -> dict:
    posts = body.get("posts") or []
    platform = posts[0].get("platform", "") if posts else ""
    settle = settle_days(platform)
    recent_since = window_start - timedelta(days=RECENT_EXTRA_DAYS)
    dated = []
    for post in posts:
        published = parse_time(post.get("published_at"))
        if published is None or post.get("views") is None:
            continue
        dated.append((post, published))
    settled = [(p, t) for p, t in dated if (read_at - t).days >= settle and t >= recent_since]
    followers = (body.get("creator") or {}).get("followers")
    rows = []
    for post, published in dated:
        if published < window_start:
            continue
        others = [p["views"] for p, _ in settled if p["id"] != post["id"]]
        young = (read_at - published).days < settle
        row = {"creator": key, "id": post["id"], "url": post.get("url"), "published_at": iso(published),
               "views": post["views"], "title": (post.get("title") or "")[:120], "still_growing": young}
        if len(others) >= MIN_OWN_POSTS and middle(others):
            usual = middle(others)
            row.update(basis="own usual", usual=round(usual), baseline_n=len(others),
                       ratio=rounded(post["views"] / usual, 2))
        elif followers:
            row.update(basis="views per follower (weaker)", ratio=rounded(post["views"] / followers, 2),
                       baseline_n=len(others))
        else:
            row.update(basis="none", ratio=None, baseline_n=len(others))
        rows.append(row)
    own = sum(1 for r in rows if r["basis"] == "own usual")
    return {"key": key, "rows": rows, "has_own_usual": own > 0, "posts_read": len(posts)}


def rank(folder: Path, window_days: int = WINDOW_DAYS, read_at: Optional[datetime] = None) -> dict:
    read_at = read_at or now()
    window_start = read_at - timedelta(days=window_days)
    creators = load_creators(folder)
    scored_creators = [score_creator(k, b, read_at, window_start) for k, b in creators.items()]
    rows = [r for c in scored_creators for r in c["rows"]]
    scored = [r for r in rows if r["basis"] == "own usual" and not r["still_growing"]]
    with_usual = [c["key"] for c in scored_creators if c["has_own_usual"]]
    status = "ok"
    single = len(creators) == 1
    if not scored:
        status = "empty"
    elif not single and len(with_usual) < MIN_CREATORS:
        status = "too_few_creators"
    elif len(scored) < MIN_SCORED:
        status = "too_few_posts"
    trends = sorted((r for r in scored if r["ratio"] and r["ratio"] >= HIT), key=lambda r: r["ratio"], reverse=True)
    weaker = sorted((r for r in rows if r["basis"].startswith("views per follower") and r["ratio"]),
                    key=lambda r: r["ratio"], reverse=True)
    result = {
        "schema": "tsr/trends@1", "scope": "account" if single else "niche", "read_at": iso(read_at), "window": {"from": iso(window_start), "to": iso(read_at)},
        "status": status, "creators": len(creators), "creators_with_own_usual": with_usual,
        "scored_posts": len(scored), "trends": trends, "leads_weaker_basis": weaker[:10],
        "still_growing": [r for r in rows if r["still_growing"]], "posts": rows,
        "deep_read": deep_read(scored, trends),
    }
    write_json(folder / "trends.json", result)
    return result


def deep_read(scored: list[dict], trends: list[dict]) -> dict:
    per_creator: dict[str, int] = {}
    top = []
    for row in trends:
        if per_creator.get(row["creator"], 0) < 2:
            top.append(row["id"])
            per_creator[row["creator"]] = per_creator.get(row["creator"], 0) + 1
        if len(top) >= 8:
            break
    ordinary = sorted((r for r in scored if 0.75 <= r["ratio"] <= 1.33), key=lambda r: abs(r["ratio"] - 1))
    flops = sorted((r for r in scored if r["ratio"] <= 0.5), key=lambda r: r["ratio"])
    return {"trends": top, "ordinary": distinct_creators(ordinary, 3), "flops": distinct_creators(flops, 2)}


def distinct_creators(rows: list[dict], count: int) -> list[str]:
    picked, seen = [], set()
    for row in rows:
        if row["creator"] not in seen:
            picked.append(row["id"])
            seen.add(row["creator"])
        if len(picked) >= count:
            break
    return picked


def direction(rows: list[dict], start: datetime, end: datetime) -> tuple[Optional[float], Optional[str], dict]:
    middle_point = start + (end - start) / 2
    early = [r["ratio"] for r in rows if parse_time(r["published_at"]) < middle_point]
    late = [r["ratio"] for r in rows if parse_time(r["published_at"]) >= middle_point]
    halves = {"earlier": {"posts": len(early), "lift": rounded(middle(early), 2)},
              "later": {"posts": len(late), "lift": rounded(middle(late), 2)}}
    if len(early) < MIN_HALF or len(late) < MIN_HALF or not middle(early):
        return None, None, halves
    value = middle(late) / middle(early)
    name = "rising" if value >= RISING else "fading" if value < FADING else "steady"
    return round(value, 2), name, halves


def corner(common: bool, lift: float) -> tuple[str, str]:
    if common and lift >= 1:
        return "scale_it", "Scale it"
    if not common and lift >= 1:
        return "underused", "Underused"
    if common:
        return "overused", "Overused"
    return "drop", "Drop"


def map_formats(folder: Path) -> dict:
    trends = read_json_or(folder / "trends.json", None) or rank(folder)
    plan = read_json_or(folder / "formats.json", None)
    if not plan or not plan.get("formats"):
        raise TsrError(f"write {folder / 'formats.json'} first (see references/niche.md)")
    scored = {r["id"]: r for r in trends["posts"] if r["basis"] == "own usual" and not r["still_growing"]}
    every = {r["id"]: r for r in trends["posts"]}
    creators_scored = {r["creator"] for r in scored.values()}
    scope = "niche" if len(load_creators(folder)) > 1 else "account"
    start, end = parse_time(trends["window"]["from"]), parse_time(trends["window"]["to"])
    problems, owner = [], {}
    formats = []
    for item in plan["formats"]:
        ids = [str(i) for i in item.get("post_ids") or []]
        for post_id in ids:
            if post_id not in every:
                problems.append(f"{item['id']}: post {post_id} is not in the window that was read")
            elif post_id in owner:
                problems.append(f"post {post_id} is in both {owner[post_id]} and {item['id']}")
            else:
                owner[post_id] = item["id"]
        rows = [scored[i] for i in ids if i in scored]
        by_creator: dict[str, list[dict]] = {}
        for row in rows:
            by_creator.setdefault(row["creator"], []).append(row)
        creator_medians = [middle(r["ratio"] for r in group) for group in by_creator.values()]
        lift = middle(creator_medians) if scope == "niche" else middle(r["ratio"] for r in rows)
        share = (len(by_creator) / len(creators_scored) if scope == "niche"
                 else len(rows) / max(1, len(scored)))
        value, name, halves = direction(rows, start, end)
        entry = {
            "id": item["id"], "name": item.get("name", item["id"]), "container": item.get("container"),
            "effort": item.get("effort"), "posts_total": len(ids), "posts_scored": len(rows),
            "creators": len(by_creator), "share": rounded(share, 3), "lift": rounded(lift, 2),
            "lift_posts": rounded(middle(r["ratio"] for r in rows), 2),
            "hit_rate": rounded(sum(1 for r in rows if r["ratio"] >= HIT) / len(rows), 2) if rows else None,
            "direction": value, "direction_label": name, "halves": halves,
            "by_creator": {k: {"posts": len(g), "median_ratio": rounded(middle(r["ratio"] for r in g), 2),
                               "best": max(g, key=lambda r: r["ratio"])["id"]} for k, g in by_creator.items()},
            "examples": [r["id"] for r in sorted(rows, key=lambda r: r["ratio"], reverse=True)[:3]],
            "lowest": [r["id"] for r in sorted(rows, key=lambda r: r["ratio"])[:3]],
        }
        entry.update(placement(entry, scope))
        formats.append(entry)
    unformatted = [i for i in scored if i not in owner]
    result = {
        "schema": "tsr/format-map@1", "scope": scope, "status": trends["status"], "window": trends["window"],
        "rules": {"common_share": NICHE_COMMON if scope == "niche" else ACCOUNT_COMMON, "lift_split": 1.0,
                  "min_creators": MIN_CREATORS, "rising": RISING, "fading": FADING},
        "formats": formats, "unformatted": {"posts": len(unformatted), "post_ids": unformatted},
        "problems": problems, "grouping": "by the agent (formats.json); every number is measured",
    }
    write_json(folder / "format-map.json", result)
    return result


def placement(entry: dict, scope: str) -> dict:
    if entry["posts_scored"] < MIN_HALF or entry["lift"] is None:
        return {"quadrant": "too_few", "quadrant_name": "Too few posts", "scope_status": "not scored"}
    if scope == "niche" and entry["creators"] < MIN_CREATORS:
        habit = "creator habit" if entry["creators"] == 1 else "few creators"
        return {"quadrant": "too_few", "quadrant_name": f"Not a niche format: {habit}", "scope_status": habit}
    common = entry["share"] >= (NICHE_COMMON if scope == "niche" else ACCOUNT_COMMON)
    key, name = corner(common, entry["lift"])
    return {"quadrant": key, "quadrant_name": name, "few_posts": entry["posts_scored"] < 6,
            "scope_status": "niche format" if scope == "niche" else "account format"}


def text_report(result: dict) -> str:
    lines = [f"Scope: {result['scope']}  status: {result['status']}"]
    order = {"scale_it": 0, "underused": 1, "overused": 2, "drop": 3, "too_few": 4}
    for entry in sorted(result["formats"], key=lambda e: (order.get(e["quadrant"], 9), -(e["lift"] or 0))):
        arrow = f", {entry['direction_label']}" if entry["direction_label"] else ""
        lift = f"{entry['lift']:.2f}x" if entry["lift"] is not None else "n/a"
        creators = f", {entry['creators']} creators" if result["scope"] == "niche" else ""
        few = " (few posts)" if entry.get("few_posts") else ""
        lines.append(f"  {entry['quadrant_name']:28} {entry['name']}: lift {lift}, share {entry['share']:.0%}"
                     f"{creators}{arrow}{few}")
    lines.append(f"  Unformatted posts: {result['unformatted']['posts']}")
    for problem in result["problems"]:
        lines.append(f"  problem: {problem}")
    return "\n".join(lines)


def trends_text(result: dict) -> str:
    lines = [f"Status: {result['status']}; {result['scored_posts']} scored posts from "
             f"{len(result['creators_with_own_usual'])} of {result['creators']} creators"]
    for row in result["trends"][:15]:
        lines.append(f"  {row['ratio']:>5.1f}x  {row['creator']}  {row['id']}  {row['title'][:60]}")
    if result["leads_weaker_basis"]:
        lines.append("  Leads on the weaker basis (views per follower), not counted toward formats:")
        for row in result["leads_weaker_basis"][:5]:
            lines.append(f"  {row['ratio']:>5.1f}/f {row['creator']}  {row['id']}")
    picks = result["deep_read"]
    lines.append(f"Watch: trends {', '.join(picks['trends']) or 'none'}; ordinary {', '.join(picks['ordinary']) or 'none'}; "
                 f"flops {', '.join(picks['flops']) or 'none'}")
    return "\n".join(lines)
