# Hook lab: the first 3 seconds, written

Input: a topic, an idea, a script, or a hook to critique. Optional: platform, audience, goal (reach, saves,
followers, clicks), constraints (no face, no voice, brand rules), language, a recipe from a teardown. Output: 6 to 10
hooks across at least 3 archetypes, each in three layers, every one passing `tsr hooks`.

Ask nothing you can infer. If the user wants speed, infer the brief and go.

## A hook has three layers (and a fourth)

| Layer | What it is | Rules |
|---|---|---|
| **Picture** (frame 0 to 1 s) | what the eye gets before any word lands | shows the result, the conflict or the stake; moves from frame 0; reads at thumbnail size; no logo, no countdown, no fade-in |
| **Voice** (the first spoken line) | what is said | one claim, said once; lands by 3 s at a fast pace (`tsr hooks` estimates it per language); opens on the subject, not on "so", "hey", "today" |
| **Text on screen** | what the muted viewer reads | 3 to 7 words; compresses the voice instead of repeating it: drop verbs and articles, keep numbers and the contrast ("$400 → $39"); front-load the strongest word; inside the safe zone |
| **Sound** (optional) | the timing cue | a beat drop on the first cut, a sudden silence on the reveal; a trending sound only when it fits |

Test each hook two ways: cover the text — does the picture still pull? Cover the picture — does the text alone earn a
pause? Both should pass.

## Archetypes

`tsr archetypes` lists them with a shape and an example (`--family core|craft|sports`). Use at least three per batch,
so the user picks an angle, not a wording:

- **core** (Kallaway's six): contrarian (highest ceiling, highest variance: the video must prove the claim),
  investigator (safe baseline), experimenter, teacher, magician (the picture does the work), fortuneteller.
- **craft:** result first, specific number, callout, authority + gap, side by side.
- **sports:** goal first, save or miss, controversial call, stat shock, prediction (`references/sports.md`).

Match the idea: a product with a visual payoff → result first or magician; education → teacher, investigator, number;
a strong opinion → contrarian (only if the payoff defends it); visible effort → experimenter or number; a narrow
audience → callout.

## Dead openers (name them in a critique)

| Name | Looks like | Fix |
|---|---|---|
| Greeting | "Hey guys", "welcome back", "in this video" | delete it; start on the claim |
| Logo or jingle | a 1-2 s brand card | brand goes at the end |
| Vague tease | "you won't believe", "this changed everything" | name the category of the answer: "one setting doubles battery life" |
| Early ask | "subscribe before we start" | deliver first; ask once at the end |
| Slow build | the real hook is the third sentence | delete the first two |
| Bait and switch | the hook promises what the video does not deliver | change the hook, not the truth |
| Single layer | a sharp line over a static face, no text | design all three layers |
| Brand first | "Check out our new…" | lead with the viewer's outcome or pain |
| Clever riddle | wordplay that needs decoding | clarity at second 1, wit in the payoff |
| Three-act hook | the hook itself takes 8 s | one beat; resolve by 3 s |

## Write the batch as JSON, then check it

```json
{
  "topic": "a $39 cold-brew maker",
  "language": "en",
  "platform": "tiktok",
  "hooks": [
    {"archetype": "contrarian",
     "visual": "two glasses side by side, price tags $300 and $39 already on screen",
     "spoken": "Your $300 machine makes worse cold brew.",
     "on_screen": "$300 vs $39",
     "audio": "beat drops on the cut to the tasting",
     "risk": "must prove it with a blind taste test"}
  ]
}
```

Save it in the cache, `~/.cache/three-second-rule/hooks/<topic>.json` (or under `$TSR_HOME` when set), never in the
user's folders; after a preflight or a teardown, its run folder is fine too. Then:

```
tsr hooks <file.json>
```

It checks each hook: the three layers are present; the text is 3-7 words; the voice can be said inside 3 s at the
language's hook pace; the text does not repeat the voice; no greeting, early ask, filler start or vague tease (in en,
es, pt, ru); and the batch: 6-10 hooks, at least 3 archetypes. Exit code 3 means rewrite: fix every failing hook and
run it again. **Never show a hook that failed.**

## Show them

One line per layer, labelled by archetype, with a one-line reason why it fits this idea and its risk:

```
1. [Contrarian] frame: two glasses, $300 and $39 tags · voice: "Your $300 machine makes worse cold brew." · text: "$300 vs $39"
   Fits: the video is a taste test. Risk: the test must be blind and shown.
```

Close with one sentence: film two or three of them and keep the one whose first 3 seconds hold best (the platform's
retention graph or `3-second views / views` decides, not taste).

## Critique mode

A draft hook in: read it aloud at a fast pace (or run it through `tsr hooks` as a batch of one), name the dead opener
or the weak layer, rewrite it, and give two alternates in other archetypes. If the same problem shows up in several
drafts, say it is one habit.

## With a recipe

After a teardown, write hooks in the recipe's `hook_pattern`, on the recipe's first beat, with the user's own subject.
Never the reference creator's sentences, face or catchphrases (`recipe.json#do_not_copy`).
