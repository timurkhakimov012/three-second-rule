# Configuration

Everything configurable is a JSON file in `skills/three-second-rule/data/` or an environment variable. No config file
of its own, no settings to lose.

## Environment

| Variable | Default | Does |
|---|---|---|
| `TSR_HOME` | `~/.cache/three-second-rule` | where runs live |
| `TSR_KEEP_DAYS` | `30` | runs older than this are pruned at the start of each command; `0` keeps everything |
| `TSR_WHISPER` | auto: `mlx_whisper`, then `whisper`, then `whisper-cli` | force one Whisper command |
| `TSR_WHISPER_MODEL` | `mlx-community/whisper-tiny` / `tiny` | the model; for `whisper-cli` (whisper.cpp) the path to a ggml file, required |

## Thresholds — `data/checks.json`

Each check carries its numbers and a `source`:

```json
{"id": "H3", "key": "first_word", "title": "The first word comes fast",
 "pass_s": 0.5, "warn_s": 1.0, "source": "ootto"}
```

Change a number, keep the source honest (`"tsr"` or your own name for a value you chose). The `why` and `fix` texts are
what the answer shows, so they can be rewritten for your team's language too. Every check is documented in
[checks.md](checks.md).

## Platforms — `data/platforms.json`

```json
"tiktok": {
  "name": "TikTok",
  "safe_zone": {"top": 0.06, "bottom": 0.13, "left": 0.03, "right": 0.03},
  "buttons": {"width": 0.11, "from_top": 0.46},
  "ads_zone": {"top": 0.125, "bottom": 0.344, "left": 0.111, "right": 0.111},
  "max_seconds": 3600,
  "sources": {"safe_zone": "…", "ads_zone": "…", "max_seconds": "…"},
  "checked": "2026-11-27"
}
```

- `safe_zone`: the share of a 9:16 frame covered on an ordinary post, each side (red on the sheet).
- `buttons`: the like / comment / share column on the right: its width and where it starts from the top (red).
- `ads_zone`: the platform's published ad template, which also covers long captions and ad add-ons (amber).
- `max_seconds`: the upload limit, used by T5.
- `sources` and `checked`: where each number comes from and when it was last checked. Apps change their interface;
  when a new layout ships, update the number and its source together. YouTube publishes no measurement of an
  ordinary Shorts post, so its `safe_zone` is this skill's estimate and says so.
- `loudness_target_lufs` and `loudness_tolerance_lu` at the top: T3's target.

Add a platform by adding an entry; `--platform <key>` then accepts it.

## Languages — `data/lang/<code>.json`

```json
{
  "code": "de", "name": "Deutsch", "hook_words_per_second": 3.2,
  "stopwords": ["der", "die", "und", "ist", "das", "…"],
  "welcome": ["hallo zusammen", "willkommen zurück", "in diesem video"],
  "subscribe": ["abonnieren", "lass ein like da"],
  "filler_openers": ["also", "ähm"],
  "vague_teases": ["du wirst nicht glauben"],
  "asks": {"follow": ["folg mir"], "comment": ["schreib in die kommentare"], "save": ["speicher dir das"],
           "share": ["teil das"], "link": ["link in der bio"], "buy": ["code"]}
}
```

A new file is picked up automatically: language detection uses `stopwords` (30 common words), H9 and B4 use the
phrase lists, the hook lab uses `hook_words_per_second`. Phrases match whole words, case-insensitive. Keep
`filler_openers` to phrases that never start a good hook (English drops "so" and "well" for that reason).

## Archetypes — `data/archetypes.json`

Add an archetype with an `id`, a `family`, a `shape`, an `example` in three layers, `best_for`, `risk` and `source`.
The hook lab lists it at once and counts it toward a batch's variety.
