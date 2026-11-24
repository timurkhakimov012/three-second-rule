# Contributing

Thanks for helping. The skill is small on purpose; contributions that keep it small, honest and dependency-free are
the most welcome.

## Ground rules

- **Standard library only.** No `pip install` for the skill itself. External programs: ffmpeg (required), yt-dlp and
  Whisper (optional), always called with argument lists, never a shell string.
- **Python 3.9+.** CI runs 3.9, 3.12 and 3.13.
- **Every number from code, every threshold with a source.** A new check needs its threshold in `data/checks.json`
  with a `source` key, a test with a known answer, and an entry in `docs/checks.md`.
- **Unknown is not zero.** New measurements return `None` with a reason when they cannot be made.
- **No promises.** Nothing in the code or the docs may claim to predict virality.

## Easy first contributions

- **A language:** add `skills/three-second-rule/data/lang/<code>.json` (see `docs/configuration.md`), plus a test in
  `tests/test_checks.py` that a greeting in that language fails H9.
- **A platform:** add an entry to `data/platforms.json` with its safe zone and length limit.
- **An archetype:** add it to `data/archetypes.json` with a three-layer example.
- **Safe-zone updates** when an app changes its interface, with a screenshot reference in the pull request.

## Development

```
git clone https://github.com/timurkhakimov012/three-second-rule
cd three-second-rule
python3 -m unittest discover -s tests          # needs ffmpeg for the video tests; they skip without it
python3 skills/three-second-rule/scripts/tsr.py doctor
```

Video tests build synthetic clips with ffmpeg's own generators (colour fields, a test pattern, a tone with silent
stretches) whose answers are known: put the defect in, assert the check finds it. No test downloads anything or runs a
speech model.

Layout: `skills/three-second-rule/` is the skill exactly as installed (`SKILL.md`, `references/`, `scripts/`, `data/`);
`docs/` is for people; `tests/` and `.github/` stay out of the installed skill.

## Changing the skill's instructions

`SKILL.md` and `references/*.md` are read by agents. Keep them imperative, concrete and short; put the reasons in
`docs/`. The `description` in `SKILL.md` must stay under 1024 characters (a test checks it).

## Pull requests

One topic per pull request, tests green, a line in `CHANGELOG.md` under "Unreleased".
