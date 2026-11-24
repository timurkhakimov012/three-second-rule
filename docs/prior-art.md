# Prior art

Before writing this skill we read the open-source skills and tools around short-form virality (November 2026). This is
what each does well, what we took as an idea (never as code or text), and the gap this skill tries to fill.

## What exists

| Project | What it does | Strength | What it lacks |
|---|---|---|---|
| [wpsoul/rea-viral](https://github.com/wpsoul/rea-viral) | account, post and niche teardowns with Python scripts, HTML reports | the method: each post against its own creator's usual; hits, ordinary posts and flops together; MEASURED / SEEN / INFERRED; formats as containers; a 3-creator rule | no check of your own video before posting; English word lists only; heavy; tied to a commercial planner |
| [vyralcontent/content-skills](https://github.com/vyralcontent/content-skills) | seven knowledge skills: hooks, scripts, captions, platforms | the three-layer hook, named archetypes, a clear list of anti-patterns | no measurement at all; general rules; built-in promotion of a paid product |
| [Ootto-AI/claude-virality-skill](https://github.com/Ootto-AI/claude-virality-skill) | rules from one account's 262 posts | a concrete, timed hook checklist (frame 0 moving, first word by 0.5 s, text by 1.2–1.6 s) | the checklist is text: nothing measures it |
| [jakalwaz/reelscope](https://github.com/jakalwaz/reelscope) | local teardown of one video: transcript, voice energy, pacing, frames | fully local; voice analysis; a draft check against your account | macOS only; teardown-first; no checklist with thresholds |
| [andrew4522-cr/instagram-tiktok-agent-skill](https://github.com/andrew4522-cr/instagram-tiktok-agent-skill) | 11 skills from hook formulas to a retention doctor | cover-to-hook alignment; breadth | formula-based, little measurement |
| [solutionsystempro/tiktok-agent-skill](https://github.com/solutionsystempro/tiktok-agent-skill) | 12 TikTok skills with stdlib tools | per-layer hook scoring, beat sheets | text-only hook scoring |
| [riccivr/retention-analyzer](https://github.com/riccivr/retention-analyzer) | retention drops against edit events | correlating the retention graph with cuts | needs retention exports and a local LLM stack |
| [kleZ799/clipmint](https://github.com/kleZ799/clipmint), [mutonby/openshorts](https://github.com/mutonby/openshorts) | long video → short clips | moment detection from audio and transcripts | a clipper, not a checker |

## What this skill adds

1. **A measured preflight of your own video.** The checklists above are advice; here every timing is measured and
   every visual judgement is tied to a numbered frame. This is the gap none of them closes.
2. **Two-step honesty.** Numbers first, eyes second, verdict third — and a "seen" check cannot pass before the agent
   has looked.
3. **One small tool, no dependencies.** Python's standard library and ffmpeg; contact sheets drawn without ffmpeg's
   optional `drawtext`, so it runs on stock builds.
4. **Four languages of word checks**, extensible by a JSON file.
5. **A loop.** Teardown → recipe → your remake checked against the recipe → compare before and after.
6. **Sports** as a first-class niche: archetypes and checks for match clips.

## Credits

The method of measuring a post against its own creator's usual, the evidence labels and the niche-format rules follow
REA Viral (Apache-2.0). The three-layer hook, Kallaway's archetypes and the anti-pattern names follow the collection in
vyralcontent/content-skills (MIT) and the creators it cites. The hook timing thresholds H2–H4 are Ootto-AI's published
observation (MIT). Thank you to all of them. All text and code here is original.
