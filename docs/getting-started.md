# Getting started

## 1. Install the tools

```
brew install ffmpeg            # macOS   (Linux: sudo apt install ffmpeg · Windows: winget install Gyan.FFmpeg)
brew install yt-dlp            # optional: read posts by link
pip install mlx-whisper        # optional, Apple Silicon: first-word timings without subtitles
```

Python 3.9 or newer is all the skill itself needs; it uses the standard library only.

## 2. Install the skill

Pick one:

```
/plugin marketplace add timurkhakimov012/three-second-rule      # inside Claude Code
/plugin install three-second-rule@three-second-rule
```

```
npx skills add timurkhakimov012/three-second-rule              # any agent that reads SKILL.md
```

```
git clone https://github.com/timurkhakimov012/three-second-rule
cp -r three-second-rule/skills/three-second-rule ~/.claude/skills/
```

A skill installed while a session is open is available from the next message (or the next session).

## 3. Check the setup

Ask the agent "is three-second-rule ready?", or run it yourself:

```
python3 ~/.claude/skills/three-second-rule/scripts/tsr.py doctor
```

```
three-second-rule 0.1.0  python 3.12.4  Darwin arm64
  ok       ffmpeg   every mode that reads a video
  ok       yt-dlp   reading and downloading public posts by link
  missing  whisper  word timings when a video has no subtitles
           install: python3 -m pip install --user mlx-whisper
  cache    /Users/you/.cache/three-second-rule
Ready.
```

## 4. Your first check

Put your export next to its subtitles if you have them (`draft.mp4` and `draft.srt`), then ask:

> check ~/Movies/draft.mp4 — it's for Reels

What happens:

1. The agent runs `tsr preflight`: about 5–20 seconds for a minute of video. It prints the measured numbers and the
   checks those numbers already decide.
2. It opens three images — the first 3 seconds frame by frame, a frame after every cut, and the frame with the app's
   buttons shaded — and writes down what it sees.
3. It runs `tsr check` and answers: how many checks passed, the fixes in order with times and frames, and three better
   openings.
4. One question at the end: send the edited version for a re-check.

Nothing is written to your folders. Ask "save the report" to get `report.md` and its images where you want them.

## 5. Next

- [Preflight](preflight.md): what each check means and how to read the answer.
- [Hook lab](hook-lab.md): "give me hooks for a video about …".
- [Teardown](teardown.md): "why did this go viral?" + a link.
- [Niche map](niche-map.md): "what works in home-espresso TikTok right now?".
