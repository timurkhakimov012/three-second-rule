#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from threesec import baseline as baseline_mod  # noqa: E402
from threesec import hooks, niche, nicherun, preflight, recipe, report, teardown, tools  # noqa: E402
from threesec.common import VERSION, TsrError, ToolMissing, load_data, prune_runs, read_json, run_path  # noqa: E402


def emit(args: argparse.Namespace, result, text: str) -> None:
    if getattr(args, "json", False):
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print(text)


def platforms_arg(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [p.strip().lower() for p in value.split(",") if p.strip()]


def do_doctor(args: argparse.Namespace) -> int:
    found = tools.doctor()
    emit(args, found, tools.doctor_text(found))
    return 0 if found["ready"] else 1


def do_preflight(args: argparse.Namespace) -> int:
    result = preflight.start(Path(args.video), platforms_arg(args.platform), args.whisper, args.lang,
                             Path(args.subs) if args.subs else None, Path(args.recipe) if args.recipe else None,
                             args.fresh)
    emit(args, result, preflight.overview(result))
    return 0


def do_check(args: argparse.Namespace) -> int:
    result = preflight.check(args.run)
    from threesec.checks import text_table
    emit(args, result, f"Folder: {result['folder']}\n{text_table(result['checks'])}")
    return 0


def do_compare(args: argparse.Namespace) -> int:
    result = report.compare(args.before, args.after)
    emit(args, result, report.compare_text(result))
    return 0


def do_runs(args: argparse.Namespace) -> int:
    rows = report.list_runs(args.limit)
    emit(args, rows, report.runs_text(rows))
    return 0


def do_report(args: argparse.Namespace) -> int:
    path = report.write_report(args.run, Path(args.out))
    emit(args, {"report": str(path)}, f"Report: {path}")
    return 0


def do_hooks(args: argparse.Namespace) -> int:
    result = hooks.check_batch(read_json(Path(args.file).expanduser()))
    emit(args, result, hooks.text_report(result))
    return 0 if result["status"] == "pass" else 3


def do_archetypes(args: argparse.Namespace) -> int:
    items = load_data("archetypes.json")["archetypes"]
    if args.family:
        items = [a for a in items if a["family"] == args.family]
    text = "\n".join(f"{a['id']:15} {a['family']:7} {a['shape']}" for a in items)
    emit(args, items, text)
    return 0


def do_recipe(args: argparse.Namespace) -> int:
    if args.action == "template":
        emit(args, recipe.TEMPLATE, json.dumps(recipe.TEMPLATE, indent=2))
        return 0
    if not args.file:
        raise TsrError("give the recipe file: tsr recipe check <file>")
    problems = recipe.validate(read_json(Path(args.file).expanduser()))
    emit(args, {"valid": not problems, "problems": problems},
         "Recipe is valid." if not problems else "Recipe problems:\n" + "\n".join(f"  - {p}" for p in problems))
    return 0 if not problems else 3


def do_teardown(args: argparse.Namespace) -> int:
    result = teardown.start(args.url, args.limit, args.full, not args.no_download,
                            Path(args.csv) if args.csv else None, args.target,
                            Path(args.video) if args.video else None)
    emit(args, result, teardown.overview(result))
    return 0


def do_baseline(args: argparse.Namespace) -> int:
    folder = run_path(args.run)
    posts = read_json(folder / "posts.json")
    target = read_json(folder / "post.json")
    result = baseline_mod.score(target, posts)
    emit(args, result, baseline_mod.text_report(result))
    return 0


def do_niche(args: argparse.Namespace) -> int:
    if args.action == "init":
        folder = nicherun.init(args.name, args.words, args.platform)
        emit(args, {"run": folder.name, "folder": str(folder)},
             f"Run: {folder.name}\nFolder: {folder}\nNext: tsr niche add {folder.name} <creator link>  (5 to 10 creators)")
        return 0
    if args.action == "add":
        result = nicherun.add_creator(args.name, args.url, Path(args.csv) if args.csv else None, args.limit, args.full)
        emit(args, result, f"Added {result['creator']}: {result['posts']} posts ({result['dated']} dated)")
        return 0
    if args.action == "rank":
        result = niche.rank(run_path(args.name), args.window)
        emit(args, result, niche.trends_text(result))
        return 0
    if args.action == "watch":
        result = nicherun.watch(args.name, not args.no_download)
        emit(args, result, nicherun.watch_text(result))
        return 0
    if args.action == "formats":
        result = niche.map_formats(run_path(args.name))
        emit(args, result, niche.text_report(result))
        return 0
    raise TsrError(f"unknown niche action {args.action}")


def do_prune(args: argparse.Namespace) -> int:
    removed = prune_runs(args.days)
    emit(args, {"removed": removed}, f"Removed {len(removed)} run(s).")
    return 0


def parser() -> argparse.ArgumentParser:
    main = argparse.ArgumentParser(prog="tsr", description="three-second-rule: measure the first 3 seconds")
    main.add_argument("--version", action="version", version=f"three-second-rule {VERSION}")
    sub = main.add_subparsers(dest="command", required=True)

    def command(name: str, handler, help_text: str) -> argparse.ArgumentParser:
        item = sub.add_parser(name, help=help_text, description=help_text)
        item.add_argument("--json", action="store_true", help="print JSON instead of text")
        item.set_defaults(handler=handler)
        return item

    command("doctor", do_doctor, "show which tools are installed")

    item = command("preflight", do_preflight, "measure a video and start its checklist")
    item.add_argument("video")
    item.add_argument("--platform", help="tiktok, reels, shorts (comma separated); default: all three")
    item.add_argument("--whisper", action="store_true", help="allow a local Whisper run when no subtitles exist")
    item.add_argument("--lang", help="language code of the speech (en, es, pt, ru, ...)")
    item.add_argument("--subs", help="a subtitle file (.srt or .vtt) for the video")
    item.add_argument("--recipe", help="a recipe.json to check the video against")
    item.add_argument("--fresh", action="store_true", help="measure again even if the file was measured before")

    item = command("check", do_check, "decide the checklist after notes.json is written")
    item.add_argument("run")

    item = command("compare", do_compare, "compare two preflight runs")
    item.add_argument("before")
    item.add_argument("after")

    item = command("runs", do_runs, "list recent runs")
    item.add_argument("--limit", type=int, default=20)

    item = command("report", do_report, "write a markdown report of a run to a folder or file")
    item.add_argument("run")
    item.add_argument("--out", required=True)

    item = command("hooks", do_hooks, "check a batch of hooks written as JSON")
    item.add_argument("file")

    item = command("archetypes", do_archetypes, "list the hook archetypes")
    item.add_argument("--family", choices=["core", "craft", "sports"])

    item = command("recipe", do_recipe, "print a recipe template or check a recipe")
    item.add_argument("action", choices=["template", "check"])
    item.add_argument("file", nargs="?")

    item = command("teardown", do_teardown, "read a post and its creator's posts, measure the comparison set")
    item.add_argument("url", nargs="?")
    item.add_argument("--csv", help="the creator's posts as CSV (id,url,views,published_at,...) instead of a link")
    item.add_argument("--target", help="with --csv: the id of the post to explain (default: the first row)")
    item.add_argument("--video", help="a local file of the target post")
    item.add_argument("--limit", type=int, default=30, help="how many recent posts of the creator to read")
    item.add_argument("--full", action="store_true", help="read each post's full metadata (slower, gives dates)")
    item.add_argument("--no-download", action="store_true", help="numbers only, no videos")

    item = command("baseline", do_baseline, "recompute a teardown's baseline")
    item.add_argument("run")

    item = command("niche", do_niche, "map a niche: init, add, rank, watch, formats")
    item.add_argument("action", choices=["init", "add", "rank", "watch", "formats"])
    item.add_argument("name", help="the niche name (init) or its run id")
    item.add_argument("url", nargs="?", help="add: a creator's profile link")
    item.add_argument("--csv", help="add: the creator's posts as CSV")
    item.add_argument("--words", nargs="*", help="init: the niche's words or tags")
    item.add_argument("--platform", help="init: the network")
    item.add_argument("--limit", type=int, default=25)
    item.add_argument("--full", action="store_true")
    item.add_argument("--window", type=int, default=niche.WINDOW_DAYS)
    item.add_argument("--no-download", action="store_true")

    item = command("prune", do_prune, "remove old runs from the cache")
    item.add_argument("--days", type=int, default=None)
    return main


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command != "doctor":
        prune_runs()
    try:
        return args.handler(args)
    except ToolMissing as error:
        print(f"error: {error}", file=sys.stderr)
        hint = tools.install_hint(error.tool)
        if hint and hint not in str(error):
            print(f"install: {hint}", file=sys.stderr)
        return 2
    except TsrError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
