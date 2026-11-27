# The checks in detail

Every check of a preflight, why it matters, how it is measured and where its threshold comes from. Thresholds live in
[`skills/three-second-rule/data/checks.json`](../skills/three-second-rule/data/checks.json); change a value there and every run
after uses it.

Statuses: **pass**, **warn**, **fail**, **not measured** (the input was missing: no subtitles, no notes yet, an
uncovered language — with the reason), **n/a** (does not apply: no audio, nobody speaks, not 9:16).

## Sources

| Key | Source |
|---|---|
| `ootto` | Ootto-AI/claude-virality-skill: winners against flops of 262 posts of one Instagram account (2026). One account's observation, not a study. |
| `vyral` | vyralcontent/content-skills, viral-hooks: the three-layer hook and its anti-patterns (general craft). |
| `craft` | General short-form editing craft, repeated across creator guides; no single measured source. |
| `platform` | The platforms' own loudness normalisation and interface (approximate, see platforms.json). |
| `tsr` | A default of this skill, chosen to be strict enough to be useful; tune it for your niche. |

## The first 3 seconds

### H1 — Frame 0 shows something

**Why.** A black, empty or fading-in first frame is a frame of swipe: the feed shows it while the thumb decides.

**How it is measured** (MEASURED+SEEN). ffmpeg `blackdetect` on the first frames (black longer than `max_black_s`), the brightness spread of frame 0 (a single flat colour), your `frame0.kind` (blank), and your `frame0_small_ok`: frame 0 is drawn again at profile-grid size (cropped to 3:4) and blurred, and a frame whose subject is lost there warns.

**Thresholds:** `max_black_s` = 0.1 · source: `ootto`

**Fix.** Start on the most telling frame of the video: the result, the face mid-sentence, the object in motion. Cut the fade-in and any logo.

### H2 — Something moves in the first 0.5 s

**Why.** A still card reads as a picture, not a video. Movement on frame 0 stops the eye before any word lands.

**How it is measured** (MEASURED). The mean difference between frames at 0, 0.25 and 0.5 s (64 px wide, grey), ffmpeg `freezedetect` from the start, and the first cut. Passes with a change of at least `min_change` or a cut by 0.5 s; fails when the opening is frozen for `frozen_fail_s` or barely changes. On a fail or a warning, the same frame difference is measured over the whole video (4 frames a second, the first 180 s, changes across a cut left out) and the most active half-second after 0.5 s is named in the fix when it moves at least `best_start_ratio` times more than the opening: a measured place to start the video from.

**Thresholds:** `min_change` = 0.008, `frozen_fail_s` = 0.5 · source: `ootto`; `best_start_ratio` = 2.0 is this skill's default

**Fix.** Open mid-action: a push-in, a hand entering, a counter running, text building word by word. A still frame needs at least a zoom.

### H3 — The first word comes fast

**Why.** Silence at the start is dead time; the viewer has nothing to hold on to.

**How it is measured** (MEASURED). The first word's start from subtitles (cue start, about ±0.3 s, or word timings from YouTube's auto captions) or local Whisper. Not measured without either; not applicable without audio or when nobody speaks.

**Thresholds:** `pass_s` = 0.5, `warn_s` = 1.0 · source: `ootto`

**Fix.** Trim the silence before the first word, and open on the subject of the sentence, not on 'so' or 'hey'.

### H4 — The hook is written on screen, early and short

**Why.** Most feeds start muted. Text on screen carries the promise to the viewer who cannot hear it.

**How it is measured** (SEEN). Your `hook_text` and `hook_text_tile` from `first-3s.jpg`: time = (tile − 1) × 0.25 s; words counted by the tool. No text fails, or warns when `muted_ok` says the picture alone carries the promise.

**Thresholds:** `pass_s` = 1.6, `warn_s` = 2.5, `min_words` = 3, `max_words` = 7, `warn_words` = 12 · source: `ootto+vyral`

**Fix.** Put 3 to 7 words of the promise on screen by 1.5 s, big, high contrast, inside the safe zone.

### H5 — By 3 s the viewer knows what this is

**Why.** A hook that has not said what the video is about by the third second is still a setup.

**How it is measured** (SEEN). Your `topic_clear_tile`.

**Source:** `vyral`

**Fix.** Say or show the subject and the stake inside the first 3 s. Move the setup after the promise.

### H6 — The picture changes inside the first 3 s

**Why.** One change in the hook window (a cut, a zoom, a text pop, a new object) resets attention before it settles.

**How it is measured** (MEASURED+SEEN). A measured cut inside `window_s`, or your `visual_change_tile` (a zoom, a pop, a new object). Continuous motion without either only warns.

**Thresholds:** `window_s` = 3.0, `min_motion` = 0.02 · source: `vyral`

**Fix.** Add one change between 1 and 2.5 s: a hard cut, a punch-in zoom or a second line of text.

### H7 — It works with the sound off

**Why.** A viewer scrolling muted decides from the picture and the text alone.

**How it is measured** (SEEN). Your `muted_ok`, from the 12 tiles alone.

**Source:** `vyral`

**Fix.** Make the picture or the text state the promise on its own. Cover the sound and watch the first 3 s.

### H8 — Picture, voice and text say the same thing

**Why.** Three layers pointing at one idea read as inevitable; layers pulling apart read as confused. Text that repeats the voice word for word wastes the second channel.

**How it is measured** (SEEN+MEASURED). Your `layers_agree`, plus a measured repeat test: the longest run of words shared by the hook text and the first 3 s of speech, as a share of the text (warns at `repeat_overlap` with at least `repeat_min_words` words).

**Thresholds:** `repeat_overlap` = 0.8, `repeat_min_words` = 4 · source: `vyral`

**Fix.** Make all three point at one promise, and compress the text: the voice says the sentence, the text says the stake ('$400 -> $39').

### H9 — No dead opener

**Why.** Greetings, 'subscribe' before any value, filler and vague teases are the openings that lose viewers first.

**How it is measured** (MEASURED). The first 3 s of speech and the hook text against the language's word lists in `data/lang/*.json`: greetings and early subscribe asks fail; filler starts and vague teases warn. Not measured in other languages.

**Source:** `vyral`

**Fix.** Delete the greeting and the filler; replace a vague tease ('you won't believe') with the category of the answer ('one setting doubles battery life').

## After the hook

### B1 — No dead air

**Why.** A stretch with no sound at all feels like the video stopped.

**How it is measured** (MEASURED). ffmpeg `silencedetect` at −45 dB: stretches of total silence inside the video (the first and last `edge_s` excluded).

**Thresholds:** `warn_s` = 0.7, `fail_s` = 1.2, `edge_s` = 0.4 · source: `tsr`

**Fix.** Cut the silent stretch or lay room tone or music under it.

### B2 — No shot drags on

**Why.** A long stretch without any change lets attention settle. Zooms and text pops count too, but the cut detector does not see them.

**How it is measured** (MEASURED). The longest shot between measured cuts. Cuts are also detected inside each half of the frame (top, bottom, left, right), so a split screen where one half cuts is not one long shot (`probe.json#region_cuts`, `#longest_unchanged`). Warn only: zooms, pans and text pops are changes too, and the cut detector does not see them.

**Thresholds:** `warn_s` = 5.0 · source: `craft`

**Fix.** Break the long shot with a punch-in, a b-roll insert or a text pop every 3 to 5 s.

### B3 — The hook's promise is paid off

**Why.** A hook that promises more than the video delivers gets the view and loses the trust; satisfaction signals fall.

**How it is measured** (INFERRED). Your `payoff_delivered`, from `shots.jpg`.

**Source:** `vyral`

**Fix.** Change the hook to what the video really delivers, or show the promised result.

### B4 — At most one kind of ask

**Why.** Follow, comment, save and the link all at once split the viewer's one action.

**How it is measured** (MEASURED). The transcript against the language's ask phrases (follow, comment, save, share, link, buy).

**Thresholds:** `max_kinds` = 1 · source: `craft`

**Fix.** Keep the one ask that fits the goal: follow for followers, a comment word for reach, save for a resource, the link for a sale.

### B5 — The ending lands

**Why.** A video that trails off loses the rewatch and the last-second share.

**How it is measured** (SEEN). Your `ending_lands`, from the last tile of `shots.jpg`. Warn only.

**Source:** `craft`

**Fix.** End on the result, a turn or a line that loops back to the first frame. No 'that's it, bye'.

## Format and delivery

### T1 — Vertical 9:16, sharp enough

**Why.** Short-form feeds are 9:16; anything else is letterboxed or cropped.

**How it is measured** (MEASURED). ffprobe size and rotation.

**Thresholds:** `min_height` = 1280 · source: `platform`

**Fix.** Export 1080 x 1920.

### T2 — Text and faces sit inside the safe zone

**Why.** The app's buttons, caption and tabs cover the edges of the frame.

**How it is measured** (SEEN). Your `safe_zone_ok`, from `safe-zones.jpg`. Red: the union of the chosen platforms' areas covered on an ordinary post, the button column included. Amber: the stricter ad templates, which also cover long captions. Text or a face on red fails; amber is mentioned, not failed. Every number names its source in `data/platforms.json`.

**Source:** `platform`

**Fix.** Move text and faces inside the green frame of safe-zones.jpg.

### T3 — Loudness near the feed's level

**Why.** Platforms normalise to about -14 LUFS: a quiet video stays quiet, a hot one gets squashed.

**How it is measured** (MEASURED). ffmpeg `ebur128` integrated loudness against −14 LUFS.

**Thresholds:** `warn_lu` = 4, `fail_lu` = 7 · source: `platform`

**Fix.** Normalise the mix to about -14 LUFS integrated, peaks under -1 dBTP.

### T4 — Speech is captioned

**Why.** Muted viewers read; captions also keep the eye on the frame.

**How it is measured** (SEEN). Your `captions` when someone speaks.

**Source:** `vyral`

**Fix.** Burn in captions, one short line at a time, inside the safe zone.

### T5 — Fits the platform's length limit

**Why.** A video over the limit is cut or refused.

**How it is measured** (MEASURED). Duration against `max_seconds` in `data/platforms.json` (TikTok 60 min, Reels 20 min, Shorts 3 min, each with its source); fails only for a platform you named.

**Source:** `platform`

**Fix.** Trim to the limit of the platform you post on.

## Against the format's recipe

### R1 — Length matches the recipe

**Why.** The format's timing is part of the format.

**How it is measured** (MEASURED). Duration against the recipe's `length_s` and `tolerance.length_pct`.

**Source:** `tsr`

**Fix.** Trim or extend toward the recipe's length.

### R2 — Cut pace matches the recipe

**Why.** Pace is part of the format: too slow reads as a different video.

**How it is measured** (MEASURED). Cuts per 10 s against the recipe's `cuts_per_10s` and `tolerance.cuts_per_10s`.

**Source:** `tsr`

**Fix.** Add or remove cuts toward the recipe's cuts per 10 s.

### R3 — The recipe's hard cuts land on time

**Why.** The turn of a format sits on a hard cut at a known time.

**How it is measured** (MEASURED). For each recipe beat with `"cut": true`, the nearest measured cut within `tolerance.cut_s`.

**Source:** `tsr`

**Fix.** Move the cuts to the recipe's beat times.

## Tuning for your niche

- A talking-head channel that always opens on a face: lower nothing, but read H2 with the face in mind — a face that
  speaks on frame 0 moves enough to pass.
- Music-only edits: H3, H9 and B4 become n/a or not measured; H4 and H7 carry the hook.
- Long-form explainers on Shorts: raise `B2.warn_s` to 7.
- A brand with fixed loudness: change `loudness_target_lufs` in `data/platforms.json`.

Change thresholds with a reason, and keep the `source` honest: write `tsr` or your own name for a value you chose.
