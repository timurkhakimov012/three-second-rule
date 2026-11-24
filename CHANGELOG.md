# Changelog

## Unreleased

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
