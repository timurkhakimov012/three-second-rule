# Preflight: check a video before it is posted

The main mode. Input: a video file of the user's own. Output: a measured checklist, the fixes in order, three better
openings.

## 1. Measure

```
tsr preflight <video> [--platform tiktok|reels|shorts] [--lang en] [--subs file.srt] [--whisper] [--recipe recipe.json]
```

- `--platform`: when the user named where they post. Without it, safe zones and length are checked for all three
  (stricter, and T5 only warns).
- Speech timings come from, in order: a `.srt`/`.vtt` next to the video with the same name (found automatically),
  `--subs`, a subtitle stream inside the file, then Whisper only with `--whisper`. If none, ask once: "No subtitles
  in the file. Run a small local speech model (whisper-tiny, ~75 MB, runs on this computer) to time the first word?"
  Yes → run again with `--whisper`. No → go on; H3, H9 and B4 stay "not measured".
- Subtitle cues give the first word to about ±0.3 s (the output says "cue"); word-level timings say "word".
- `--recipe`: a `recipe.json` from a teardown; adds R1-R3 (length, pace, cut beats).

The output names the run id, the run folder and the three sheets, and prints the checks that numbers alone decide.

## 2. Look

Open the three sheets, each once:

| Sheet | What it is | Look for |
|---|---|---|
| `first-3s.jpg` | 12 tiles, tile n = the frame at (n−1)×0.25 s: tile 1 = 0.00 s, tile 5 = 1.00 s, tile 7 = 1.50 s, tile 12 = 2.75 s | frame 0, when the hook text is readable, when the subject is clear, any zoom or pop, whether the 3 s make sense muted |
| `shots.jpg` | tile 1 = the first frame, then a frame 0.12 s after each cut, the last tile = the end | what the video delivers, whether the promise is paid off, how it ends, captions |
| `safe-zones.jpg` | 4 frames with the app's interface shaded red and the safe area framed green | text or a face touching red |

Then copy `notes.template.json` to `notes.json` in the run folder and fill it. Rules for each field:

| Field | Write | Not |
|---|---|---|
| `looked` | `true` only after opening all the sheets listed in the output | `true` from the numbers alone |
| `frame0.kind` | one of `face`, `person`, `text`, `product`, `action`, `scene`, `graphic`, `blank` | — |
| `frame0.what` | one plain sentence about tile 1 | an opinion |
| `hook_text` | the words on screen in tiles 1-12, verbatim, that state the promise (a title, a big caption). Not the running subtitles of the speech, unless the subtitles are the only text | a paraphrase |
| `hook_text_tile` | the first tile where it is fully readable | the tile where it starts animating in |
| `topic_clear_tile` | the first tile by which a stranger would know what the video is about (from picture, text, or the measured `first_3s_text`) | `null` just because it is subtle: decide |
| `visual_change_tile` | the first tile with a zoom, a text pop, a new object entering, when there is no cut in the first 3 s | a cut (measured already) |
| `muted_ok` | `true` if picture + text alone state the promise | `true` because the voice is good |
| `muted_why` | one line: what carries it, or what is missing | — |
| `layers_agree` | `true` if picture, voice (`first_3s_text`) and text point at one promise | — |
| `safe_zone_ok` | `false` if any text or face touches red on any tile; name the tile in `safe_zone_issue` | — |
| `speaking` | `true` if anyone talks | — |
| `captions` | `true` if the speech is captioned on screen; `null` if nobody speaks | — |
| `payoff_delivered` | `true`/`false` if `shots.jpg` shows the promised result; `null` if you cannot tell from the stills | a guess |
| `ending_lands` | `false` if the end tile is a trailing shot, a "bye", a fade to nothing | — |

Write `null` for anything you cannot tell. A `null` stays "not measured", which is honest; a guess is not.

## 3. Decide

```
tsr check <run id>
```

It validates `notes.json` (fix what it names), decides every check and writes `checks.json`.

## The checklist

| Id | Check | From | Pass |
|---|---|---|---|
| H1 | Frame 0 shows something | black detection + frame 0 | no black over 0.1 s, frame 0 not blank |
| H2 | Something moves in the first 0.5 s | frame difference, freeze, cuts | change ≥ 0.008 or a cut by 0.5 s |
| H3 | The first word comes fast | speech timings | ≤ 0.5 s (warn ≤ 1.0 s) |
| H4 | The hook is on screen, early and short | your notes | 3-7 words by 1.6 s (warn ≤ 2.5 s, ≤ 12 words); no text: fail, or warn if the picture alone carries it |
| H5 | By 3 s the viewer knows what this is | your notes | a tile ≤ 12 |
| H6 | The picture changes inside 3 s | cuts, your notes, motion | a cut, a zoom or a pop by 3 s |
| H7 | It works with the sound off | your notes | `muted_ok` |
| H8 | Picture, voice and text agree | your notes + transcript | agree, and the text does not repeat 80% of a spoken phrase word for word |
| H9 | No dead opener | transcript + hook text | no greeting, no early "subscribe" (fail); no filler start, no vague tease (warn) |
| B1 | No dead air | silence detection | no total silence ≥ 0.7 s (fail ≥ 1.2 s), ends excluded |
| B2 | No shot drags on | cuts | no shot over 5 s (warn only: zooms are invisible to the cut detector) |
| B3 | The promise is paid off | your notes | `payoff_delivered` |
| B4 | At most one kind of ask | transcript | one of follow / comment / save / share / link / buy |
| B5 | The ending lands | your notes | `ending_lands` (warn only) |
| T1 | Vertical 9:16 | probe | 9:16, at least 1280 px high (warn below) |
| T2 | Inside the safe zone | your notes | `safe_zone_ok` |
| T3 | Loudness | EBU R128 | −14 ± 4 LUFS (fail beyond ±7) |
| T4 | Speech is captioned | your notes | `captions` when someone speaks |
| T5 | Length limit | duration | under the platform's limit |
| R1-R3 | Against a recipe | probe | length ±10%, cuts per 10 s ±1, each hard-cut beat within 0.25 s |

Every threshold and its source is in `data/checks.json`. Where a check fails on a video that clearly works (a famous
creator's hit that breaks H3), say so: the rules are averages, not laws.

## 4. Answer (in the user's language)

```
<N> of <M> passed · <W> warnings · <F> failed  (<K> not measured: <why, in a few words>)

Fix first
1. [H1] Frame 0 is black for 0.40 s → start on tile 3's shot (the open laptop); cut the fade.
2. [H9] Opens with "hey guys, today I want to" → open on the claim: "One setting doubles battery life."
3. [B1] 1.5 s of silence at 4.0-5.5 s → cut it or lay the music under it.
…

Better openings
1. [Result first]  frame: the battery at 100% next to a dead phone · voice: "Same phone, two days of battery." · text: "2 days. 1 setting."
2. [Investigator]  …
3. [Contrarian]    …

Report: not saved (say "save the report" to get it as a file)
```

- Order the fixes by what decides the swipe: failed hook checks first, then warnings in the hook, then the body, then
  format and delivery. At most 7; group small ones.
- Each fix names the check, the value (MEASURED or SEEN with its tile) and one concrete change. No generic advice.
- The three openings come from the hook lab (`references/hooks.md`), built from this video's own footage and promise,
  and pass `tsr hooks` before you show them.
- Mention once that thresholds are heuristics, if any check failed on a judgement call.
- Never print the full table unless asked; the short form above is the answer.

## 5. Again, after an edit

When the user sends the edited file: `tsr preflight <new file>`, look, `notes.json`, `tsr check`, then
`tsr compare <old run> <new run>`. The output of `preflight` names an earlier run of a file with the same name. Answer
with what changed: "Was 9 of 18, now 15 of 18: H1, H3 and B1 fixed; H8 still repeats the voice."

## 6. Save a report (only when asked)

```
tsr report <run id> --out <folder>
```

Writes `<run id>.md` and a `<run id>-files/` folder with the three sheets. Give the path. Without the request, nothing
is written outside the cache (`~/.cache/three-second-rule`, kept 30 days).
