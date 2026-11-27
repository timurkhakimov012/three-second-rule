# Changelog

## Unreleased

## 0.2.0 — 2026-11-27

- **A measured place to start.** When H2 fails or warns, the fix names the most active half-second of the video
  (frame difference over the whole video, changes across a cut left out), when it moves at least twice as much as
  the opening.
- **Frame 0 small and blurred.** `first-3s.jpg` gets a bottom row: frame 0 at profile-grid size (cropped to 3:4) and
  blurred. A new note, `frame0_small_ok`, turns H1 into a warning when the subject is lost there.
- **Safe zones with sources.** `data/platforms.json` now separates what an ordinary post covers (red, with the
  button column) from the stricter ad templates (amber), and names the source and the date of every number.
  TikTok and Reels zones come from an in-app measurement; length limits updated (TikTok 60 min, Reels 20 min).
- **B2 on split screens.** Cuts are also detected inside each half of the frame, so a split screen where one half
  cuts is no longer one long shot.
- **H9 without a transcript.** A short hook text in English (or any covered language) is checked for dead openers
  even when there is no speech transcript.
- **Honest nulls.** A field left `null` in `notes.json` is reported as "left null", not as missing notes.

## 0.1.0 — 2026-11-25

First release.

- **Preflight:** 19 checks on a video file in three groups (the first 3 seconds, after the hook, format and
  delivery), measured with ffmpeg and judged from three contact sheets; fixes in order; `compare` between versions;
  markdown reports on request.
- **Speech timings** from subtitle files, embedded subtitles, YouTube's word-timed captions, or local Whisper
  (`mlx_whisper`, `whisper`, `whisper-cli`) with consent.
- **Word checks** in English, Spanish, Portuguese and Russian: greetings, early asks, filler, vague teases, asks.
- **Hook lab:** 16 archetypes (core, craft, sports) and a batch checker.
- **Teardown:** a post against its own creator's usual, a comparison set of ordinary posts and flops, recipes with
  timed beats, remakes checked against a recipe.
- **Niche map:** creators ranked on their own usual, formats measured and placed (Scale it, Underused, Overused,
  Drop) with their direction.
- Claude Code plugin manifest; installable with `npx skills add`.
