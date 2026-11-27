# Commands and files

`tsr` = `python3 "SKILL_DIR/scripts/tsr.py"`. Every command takes `--json` to print the full result as JSON instead
of text. Exit codes: 0 done, 1 not ready (doctor), 2 an error (printed on stderr), 3 a check you must act on failed
(hooks, recipe check).

## Commands

| Command | Does |
|---|---|
| `tsr doctor` | Python, ffmpeg, yt-dlp, Whisper: found or not, with the install line |
| `tsr preflight <video> [--platform p1,p2] [--lang xx] [--subs f] [--whisper] [--recipe f] [--fresh]` | measure, draw the sheets, write the notes template, print what the numbers decide |
| `tsr check <run id or folder>` | read `notes.json`, decide every check, write `checks.json` |
| `tsr compare <before> <after>` | checks that changed, and the main numbers before and after |
| `tsr runs [--limit N]` | recent runs, newest first |
| `tsr report <run> --out <folder or file.md>` | a markdown report and its pictures, written where the user asked |
| `tsr hooks <file.json>` | check a batch of hooks (exit 3 when any fails) |
| `tsr archetypes [--family core|craft|sports]` | the hook archetypes |
| `tsr recipe template` / `tsr recipe check <file>` | the recipe shape / validate one |
| `tsr teardown <link> [--limit N] [--full] [--no-download]` | a post against its creator's usual, comparison videos measured |
| `tsr teardown --csv <file> [--target ID] [--video file]` | the same from numbers the user gives |
| `tsr baseline <teardown run>` | recompute the baseline |
| `tsr niche init "<name>" [--words ...] [--platform p]` | start a niche run |
| `tsr niche add <run> <profile link> [--limit N] [--full]` / `--csv <file>` | add a creator |
| `tsr niche rank <run> [--window days]` | every post against its own creator's usual |
| `tsr niche watch <run> [--no-download]` | download and measure the picks |
| `tsr niche formats <run>` | measure `formats.json` and place the formats |
| `tsr prune [--days N]` | delete old runs now (it also happens at the start of each command) |

## Where things are

The cache is `~/.cache/three-second-rule` (or `$TSR_HOME`). Runs older than 30 days (`$TSR_KEEP_DAYS`) are removed.

| File | Written by | Holds |
|---|---|---|
| `run.json` | tsr | what was run, on what, with which options |
| `probe.json` | tsr | MEASURED: size, aspect, fps, duration, cuts (and cuts inside one half of the frame), shots, black, freezes, motion (and its most active half-second), silences, loudness |
| `speech.json` | tsr | MEASURED: words with times, first word, words per minute, gaps, first 3 s text, language, source |
| `sheets.json` | tsr | which tile of which sheet is which time |
| `first-3s.jpg`, `shots.jpg`, `safe-zones.jpg` | tsr | the sheets you look at |
| `notes.template.json` | tsr | the fields to fill, with help |
| `notes.json` | you | SEEN: what the sheets show |
| `checks.json` | tsr | the checklist, each check with value, expected, evidence, source, fix |
| `post.json`, `posts.json`, `baseline.json` | tsr (teardown) | the post, the creator's posts, the scores |
| `videos/<id>/` | tsr (teardown, niche) | one measured run per watched video |
| `recipe.json` | you (teardown) | the format with timed beats and tolerance |
| `findings.md` | you (teardown, niche) | the reading, one labelled claim per bullet |
| `creators/*.json`, `trends.json` | tsr (niche) | the creators' posts and every post's ratio |
| `formats.json` | you (niche) | the grouping into formats |
| `format-map.json` | tsr (niche) | the measured formats and their corners |

## Environment

| Variable | Default | Does |
|---|---|---|
| `TSR_HOME` | `~/.cache/three-second-rule` | where runs live |
| `TSR_KEEP_DAYS` | `30` | age at which runs are pruned; `0` keeps everything |
| `TSR_WHISPER` | auto | force a Whisper command: `mlx_whisper`, `whisper` or `whisper-cli` |
| `TSR_WHISPER_MODEL` | `whisper-tiny` / `tiny` | the model name; for `whisper-cli`, the path to a ggml model file |
