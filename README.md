# three-second-rule

**Check the first 3 seconds of your short video before you post — measured, not guessed.**

An open-source agent skill for Claude Code (and any agent that reads `SKILL.md`). Give it your video and it measures
the seconds that decide whether a viewer stays: frame 0, motion, the first word, the hook text, the first cut, dead
air, safe zones, loudness. Then it tells you exactly what to change, with the time and the frame for each fix.

TikTok · Instagram Reels · YouTube Shorts · free · local · no API keys · MIT

```
> check draft.mp4 before I post it on TikTok

13 of 18 passed · 2 warnings · 3 failed

Fix first
1. [H1] Frame 0 is black for 0.40 s → open on the shot at 1.0 s (the open laptop).
2. [H9] Opens with "hey guys, today I want to" → open on the claim: "One setting doubles battery life."
3. [B1] 1.5 s of silence at 4.0–5.5 s → cut it or lay the music under it.
4. [H3] First word at 0.82 s → trim 0.4 s of silence before it.
5. [T2] The hook text sits under TikTok's right-hand buttons (safe-zones tile 2).

Better openings
1. [Result first] frame: the phone at 100% next to a dead one · voice: "Same phone, two days of battery." · text: "2 days. 1 setting."
2. [Investigator] frame: thumb opening Settings · voice: "There's a battery setting Apple hides." · text: "1 hidden setting"
3. [Contrarian]  frame: a power bank thrown in a drawer · voice: "Stop buying power banks." · text: "$0 fix"

Send the edited version and I'll check it again and show what changed.
```

## Why

Most hook advice is a list of rules. Most "viral analysis" tools are a model guessing from a thumbnail. This skill does
neither: **scripts measure** (ffmpeg: cuts, black frames, motion, silence, loudness; subtitles or a local Whisper:
the first word), **the agent looks** at three contact sheets of your video, and **every claim says where it comes
from** — measured, seen on a named frame, or inferred with its reason. Nothing is a promise of virality.

## Four modes

| You give | It answers | Mode |
|---|---|---|
| **Your video file** | Will these 3 seconds hold a viewer, and what exactly to fix? | **Preflight** — the main one |
| **A link to someone's post** | What did its first 3 seconds do that its creator's ordinary posts did not? | **Teardown** |
| **A topic** | Which first 3 seconds to film: frame, voice line, on-screen text | **Hook lab** |
| **A niche or an account** | Which openings and formats work now across creators, which fade | **Niche map** |

There is no menu. The skill picks the mode from what you wrote.

### Preflight — check your video

19 checks in three groups, each with its threshold and its source in [`data/checks.json`](skills/three-second-rule/data/checks.json):

- **The first 3 seconds:** frame 0 shows something · something moves by 0.5 s · the first word by 0.5 s · the hook on
  screen by 1.6 s in 3–7 words · the subject clear by 3 s · a visual change inside 3 s · works muted · picture, voice
  and text agree · no dead opener (greeting, early "subscribe", filler, vague tease — in English, Spanish, Portuguese
  and Russian)
- **After the hook:** no dead air · no shot drags on · the promise is paid off · one ask at most · the ending lands
- **Format and delivery:** 9:16 · text inside the safe zone of TikTok / Reels / Shorts · loudness near −14 LUFS ·
  speech captioned · within the length limit

Edit, send it again, and `tsr compare` shows what changed: *"Was 9 of 18, now 15 of 18: H1, H3 and B1 fixed."*

### Teardown — why did that one work?

A post is measured **against its own creator's usual** (the median of their settled posts), never against the
biggest number around: a small creator's 5× beats a big creator's ordinary post. The skill downloads the post, two of
the creator's ordinary posts and one or two flops, measures all of them and looks at them side by side. Whatever the
hit shares with the flops is not why it worked. Out comes a **timed recipe** (beats, cuts, pace) that you film with
your own material — and your remake can be checked against it.

### Hook lab — what to film

6–10 hooks across at least three of 16 archetypes (Kallaway's six, craft openers, and five for sports), each written
in three layers: what is on frame 0, what is said, what is on screen. Every hook is checked before you see it: says in
under 3 s, 3–7 words of text, text that compresses the voice instead of repeating it, no dead opener.

### Niche map — what works now

5–10 creators, every post against its own creator's usual, the winners watched, the posts grouped into formats, and
each format placed: **Scale it**, **Underused**, **Overused** or **Drop**, with its direction (rising, steady,
fading). A format of the niche needs three creators or more; less is one creator's habit and is shown as such.

## Install

**Claude Code plugin**

```
/plugin marketplace add timurkhakimov012/three-second-rule
/plugin install three-second-rule@three-second-rule
```

**skills.sh** (Claude Code, Cursor, Codex, Gemini CLI, …)

```
npx skills add timurkhakimov012/three-second-rule
```

**By hand**

```
git clone https://github.com/timurkhakimov012/three-second-rule
cp -r three-second-rule/skills/three-second-rule ~/.claude/skills/
```

Then ask your agent: *"check ~/Movies/draft.mp4"*.

## Requirements

| | Needed for | Install |
|---|---|---|
| Python 3.9+ | everything (standard library only, no pip) | usually already there |
| **ffmpeg** | every mode that reads a video | `brew install ffmpeg` · `sudo apt install ffmpeg` · `winget install Gyan.FFmpeg` |
| yt-dlp *(optional)* | reading and downloading public posts by link | `brew install yt-dlp` |
| Whisper *(optional)* | the first word's time when a video has no subtitles | `pip install mlx-whisper` (Apple Silicon) or `pip install openai-whisper` |

Run `python3 skills/three-second-rule/scripts/tsr.py doctor` to see what is there. Without Whisper, a `.srt` next to the
video (same name) is enough. Whisper runs locally, with the tiny model, and only after you say yes.

## What it does not do

- **Predict virality.** No score out of 100. Thresholds are heuristics with named sources; a video can break one and
  still work, and the skill says so.
- **Read private data.** No sign-in, no cookies, no accounts. Instagram rarely gives a creator's post list without
  signing in: give the numbers as a CSV and the teardown works from them.
- **Post anything,** or send your video anywhere.
- **Copy anyone.** Recipes keep the craft and list what not to copy (face, voice, footage, catchphrases).
- **Detect goals in a full match** (see [`references/sports.md`](skills/three-second-rule/references/sports.md)).

## How it works

```
your video ──► tsr preflight ──► probe.json      cuts, black, freeze, motion, silence, loudness
                                 speech.json     words and times (subtitles or local Whisper)
                                 first-3s.jpg    12 frames, one every 0.25 s
                                 shots.jpg       a frame after each cut, and the end
                                 safe-zones.jpg  the app's interface shaded red
           ──► the agent looks at 3 images ──► notes.json  (what is on screen, when)
           ──► tsr check ──► checks.json ──► the answer: N of M, fixes in order, better openings
```

Working files live in `~/.cache/three-second-rule` and are pruned after 30 days. A report is written to your folder
only when you ask. Details: [docs/architecture.md](docs/architecture.md).

## Documentation

| | |
|---|---|
| [Getting started](docs/getting-started.md) | install, first check, what you see |
| [Preflight](docs/preflight.md) | the 19 checks, how each is measured, how to read the answer |
| [The checks in detail](docs/checks.md) | every check: why it matters, how it is measured, threshold, source, how to tune it |
| [Teardown](docs/teardown.md) | the creator's usual, the comparison set, recipes |
| [Hook lab](docs/hook-lab.md) | three layers, 16 archetypes, dead openers |
| [Niche map](docs/niche-map.md) | formats, corners, direction |
| [Evidence and ethics](docs/evidence-and-ethics.md) | the three labels, privacy, copyright, what is never claimed |
| [Configuration](docs/configuration.md) | environment, thresholds, platforms, languages |
| [CLI reference](skills/three-second-rule/references/commands.md) | every command and file |
| [Troubleshooting](docs/troubleshooting.md) · [FAQ](docs/faq.md) | when something does not work |
| [Architecture](docs/architecture.md) | layers, runs, design decisions |
| [Prior art](docs/prior-art.md) | the open-source skills this one learned from, and what it adds |

## Credits

Built on ideas from open-source work, written from scratch: the post-against-its-creator's-usual method and evidence
labels from [REA Viral](https://github.com/wpsoul/rea-viral); the three-layer hook, archetypes and anti-patterns
collected in [vyralcontent/content-skills](https://github.com/vyralcontent/content-skills); the measurable hook
checklist from [claude-virality-skill](https://github.com/Ootto-AI/claude-virality-skill); local teardowns from
[reelscope](https://github.com/jakalwaz/reelscope). See [docs/prior-art.md](docs/prior-art.md).

## License

[MIT](LICENSE). Contributions welcome: [CONTRIBUTING.md](CONTRIBUTING.md).
