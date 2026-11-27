# Preflight

The main mode: a video file of your own in, a measured checklist and concrete fixes out.

## What you say

> check draft.mp4 · is this ready to post? · why will this flop? · fix my intro · review my reel before TikTok

Add the platform if you know it ("for Shorts"): safe zones and the length limit are then checked for that platform
only. Without it, all three are checked, which is stricter.

## What is measured

| Measurement | Tool | Used by |
|---|---|---|
| Size, aspect, rotation, fps, duration, streams | ffprobe | T1, T5 |
| Scene cuts (scene score > 0.30, cuts closer than 0.2 s merged) | ffmpeg `select` + `showinfo` | H2, H6, B2, R2, R3 |
| Black frames at the start | ffmpeg `blackdetect` | H1 |
| A frozen opening | ffmpeg `freezedetect` | H2 |
| Motion in the first 3 s (frame difference every 0.25 s) | raw frames, computed in Python | H2, H6 |
| Silence (−45 dB, ≥ 0.3 s) | ffmpeg `silencedetect` | B1 |
| Integrated loudness and true peak | ffmpeg `ebur128` | T3 |
| Words and their times | subtitles (`.srt`, `.vtt`, an embedded stream) or local Whisper | H3, H8, H9, B4 |

Then three contact sheets the agent looks at:

- **first-3s.jpg** — 12 frames, one every 0.25 s, numbered: tile 1 is 0.00 s, tile 5 is 1.00 s, tile 12 is 2.75 s. Below them, frame 0 again at profile-grid size (cropped to 3:4) and blurred: does it still read when small?
- **shots.jpg** — the first frame, a frame 0.12 s after each cut, and the last frame.
- **safe-zones.jpg** — four frames: red is covered on an ordinary post (the edges and the button column), amber is covered in ads and under a long caption, the safe area is framed green. Every number has its source in `data/platforms.json`.

The agent writes what it saw into `notes.json` (what is on frame 0, when the hook text is readable, whether the video
works muted, whether the promise is paid off …). Checks that need eyes stay "not measured" until it has.

## The 19 checks

| Group | Checks |
|---|---|
| The first 3 seconds | H1 frame 0 shows something · H2 movement by 0.5 s · H3 the first word by 0.5 s · H4 the hook on screen by 1.6 s, 3–7 words · H5 the subject clear by 3 s · H6 a visual change inside 3 s · H7 works muted · H8 the layers agree · H9 no dead opener |
| After the hook | B1 no dead air · B2 no shot over 5 s · B3 the promise is paid off · B4 one ask at most · B5 the ending lands |
| Format and delivery | T1 9:16 · T2 inside the safe zone · T3 loudness near −14 LUFS · T4 speech captioned · T5 within the length limit |

With a recipe from a teardown, three more: R1 length, R2 cut pace, R3 hard cuts on the recipe's beats.

Each one — why it matters, how it is measured, its threshold and its source — is in [checks.md](checks.md).

## Reading the answer

```
13 of 18 passed · 2 warnings · 3 failed  (1 not measured: no subtitles)
```

- **passed of decided**: checks that were not measured or do not apply are not counted either way.
- **Fix first** is ordered by what decides the swipe: failed checks in the first 3 seconds, then warnings there, then
  the body, then format. Each fix names the check, the measured value or the frame, and one concrete change.
- **Better openings** are written for your video's own footage and promise, in three layers, and checked by the hook
  lab before you see them.

There is no virality score. A video can break a rule and still work; the answer says so when that is likely.

## Again after an edit

Send the edited file. The agent checks it the same way and compares:

```
Before: 9 of 18 passed, 4 warning(s), 5 failed
After:  15 of 18 passed, 2 warning(s), 1 failed
  H1  Frame 0 shows something: fail -> pass  (black for 0.40 s -> not black, not flat)
  H3  The first word comes fast: warn -> pass  (0.82 s -> 0.30 s)
  B1  No dead air: fail -> pass  (4.00-5.50 s -> none)
  first word: 0.82 s -> 0.30 s
```

## Subtitles and Whisper

The first word is timed from, in order: a subtitle file next to the video with the same name, a file you give, a
subtitle stream inside the video, or — only if you agree — a local Whisper run with the tiny model. Subtitle cues are
precise to about ±0.3 s (the answer says so); YouTube's automatic captions and Whisper give each word's time.

Without any of them, H3, H9 and B4 are "not measured" and everything else still works.

## Saving a report

> save the report to ~/Desktop

writes `check-draft-1a2b3c4d.md` and a `check-draft-1a2b3c4d-files/` folder with the three sheets.
