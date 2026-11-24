# Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `error: ffmpeg is not installed` | ffmpeg or ffprobe is not on `PATH` | `brew install ffmpeg` · `sudo apt install ffmpeg` · `winget install Gyan.FFmpeg`, then a new terminal |
| `error: yt-dlp is not installed` | reading by link needs it | `brew install yt-dlp`, or give the file / a CSV instead |
| H3, H9 and B4 say "not measured" | no subtitles and Whisper not allowed or not installed | put `video.srt` next to `video.mp4`, or allow Whisper (`--whisper`) |
| `no Whisper found` | none of `mlx_whisper`, `whisper`, `whisper-cli` | `pip install mlx-whisper` (Apple Silicon) or `pip install openai-whisper`; for whisper.cpp set `TSR_WHISPER_MODEL` to a ggml model |
| The first word is ~0.3 s off | subtitle cues start a little before the word | expected: cue timings are marked "cue"; Whisper or YouTube auto-captions give word timings |
| Safe zones "skipped" | the video is not 9:16 | export 1080×1920; T1 fails meanwhile |
| A cut is missing | a soft cross-fade or a zoom is not a scene cut | the agent notes zooms and pops from the frames (H6); B2 is a warning for this reason |
| Too many cuts on a flashing video | strobes and fast motion pass the 0.30 scene threshold | expected on such footage; the shots sheet shows them |
| A teardown says "not read: HTTP Error 403" | the site refused the download | try again later; the rest of the run goes on, and that post is never described |
| Instagram teardown finds no posts | Instagram lists posts only to signed-in users; the skill never signs in | give the creator's numbers as CSV (`id,url,views,published_at,title`) |
| "weak basis" beside a ratio | fewer than 8 of the creator's posts are older than 7 days | read more posts (`--limit 50`), or accept the weaker number |
| YouTube posts are "undated" | channel lists do not include dates | run the teardown with `--full` (slower) |
| `notes.json` problems in `tsr check` | a field has the wrong type or a tile out of 1–12 | fix exactly the fields named |
| Old runs vanished | runs older than 30 days are pruned | set `TSR_KEEP_DAYS=0` to keep everything |
| The sheets look washed out | a 10-bit or HDR source | expected: frames are converted to 8-bit sRGB for the sheets only |
