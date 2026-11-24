# Sports clips: match highlights, goals, reactions

Sport is the niche where the first three seconds are already shot: the moment exists, the work is choosing it and
putting it first. Read this next to the mode in use.

## What the opening should be

- **The decisive moment on frame 0**, or a frame just before it: the ball in flight, the keeper mid-dive, the
  referee reaching for the card. Context (teams, minute, score) comes as text in the same second, never as an intro.
- **Text = the stake, not the description.** "93' — 2-1" or "how is this saved?" beats "Great goal by …".
- **The outcome is shown.** A freeze before the shot is a hook; withholding the goal to the end is bait.
- **Keep a second moment for the payoff.** Goal first spends the best moment; the turn is the replay from another
  angle, the celebration, the stat, the reaction.

Archetypes for sports (`tsr archetypes --family sports`): goal first, save or miss, controversial call, stat shock,
prediction.

## Checking a highlight (preflight)

All checks apply. In sports they read like this:

| Check | In a highlight |
|---|---|
| H1, H2 | a static scoreboard, a channel ident or a wide shot of a calm pitch on frame 0 fails |
| H3 | commentary or a voice-over word by 0.5 s; crowd noise alone does not count as a word |
| H4 | the score, the minute, or a one-line stake on screen by 1.5 s |
| H6 | a cut to a closer angle inside 3 s |
| B2 | a 6 s wide shot of build-up play: cut it or punch in |
| T2 | broadcast graphics (scoreboard, channel logo) sitting in the app's red zone are fine; your own text is not |

## Choosing the moment from a full match

The skill does not detect goals automatically. What helps:

- The broadcast scoreboard changes after a goal: scrub to the change and go back 10-20 s.
- Crowd and commentary get loud at big moments: `tsr preflight` on the match file measures loudness and silence for
  the whole file, not per moment, so use it to check the cut clip, not to find the moment.
- Open-source detectors exist (scoreboard OCR plus commentary, audio-only goal detection); they are outside this
  skill.

## Rights

Broadcast footage belongs to leagues and broadcasters. Use only clips the user has the right to post (their own
footage, licensed clips, the league's own social clips where its rules allow). In a teardown, frames of a match stay
in the cache like any other creator's video.

## Betting and predictions

A prediction hook states an opinion, never a certainty. No odds as guarantees, no "sure win", no promise of money.
When the user's brand has rules for gambling content, those rules win over any hook.
