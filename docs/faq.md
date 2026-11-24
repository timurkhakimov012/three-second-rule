# FAQ

**Does it predict whether my video will go viral?**
No. It measures what the first three seconds do and compares that with rules that come from observation and craft.
Reach depends on things no file contains: the topic, the timing, the audience, luck. A clean checklist removes the
reasons viewers leave early; it does not guarantee they stay.

**Why should I trust the thresholds?**
Don't, blindly. Every one has a source in `data/checks.json` — one creator's published winners-versus-flops study, a
platform's loudness normalisation, or general editing craft — and every one can be changed. A video that breaks a rule
and works anyway is real; the answer says so when it happens.

**Does my video leave my computer?**
No. ffmpeg, the sheets and Whisper all run locally. The agent sees three small contact-sheet images, like any image
you show it.

**Why does it need to "look" at all? Can't the script do everything?**
Times, cuts, motion, silence and loudness are measured. Whether the text on screen states the promise, whether frame 0
shows the result, whether the video makes sense on mute — those need eyes. The skill keeps the two apart: the agent
cannot pass a "seen" check without opening the frames, and cannot invent a measured number.

**Why three images and not the video?**
Context. Twelve frames of the first three seconds on one sheet show the hook precisely (one frame every 0.25 s) for
the cost of one image, and a whole session of checks still fits.

**Which languages?**
Measurements and frames work in any language. Word checks (dead openers, asks, hook timing) cover English, Spanish,
Portuguese and Russian; adding one is a JSON file ([configuration.md](configuration.md)).

**Which agents?**
Claude Code first (plugin or skill). The `SKILL.md` format is read by Cursor, Codex, Gemini CLI and others; the tool is
plain Python, so any agent with a shell can run it.

**TikTok vs Reels vs Shorts?**
The checks are the same; the safe zones and length limits differ (`data/platforms.json`). Name the platform for the
tightest check.

**Can it check a video against a competitor's?**
Yes: a teardown of their post makes a recipe, and "check my video against the recipe" adds three timing checks.

**Is it free?**
Yes, MIT, and it calls no paid service.
