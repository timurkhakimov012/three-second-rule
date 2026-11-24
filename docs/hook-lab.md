# Hook lab

The first three seconds, written before they are filmed.

## What you say

> hooks for a video about my $39 cold-brew maker · how should I open this? · make this intro stronger: "Hey guys, today…"

Add what you know — platform, audience, goal, "no face" — or let the agent infer it.

## What you get

6 to 10 hooks, from at least three archetypes, each in three layers:

```
1. [Contrarian] frame: two glasses, tags $300 and $39 · voice: "Your $300 machine makes worse cold brew." · text: "$300 vs $39"
   Fits: the video is a taste test. Risk: the test must be blind and shown.
2. [Result first] frame: a glass filling, condensation running · voice: "Twelve hours, thirty-nine dollars, no machine." · text: "$39. No machine."
3. [Investigator] …
```

Film two or three, and let the platform's retention graph pick the winner.

## Three layers

| Layer | Job | Rule of thumb |
|---|---|---|
| Picture | stop the thumb before any word lands | the result, the conflict or the stake on frame 0, already moving |
| Voice | one claim | says in under 3 seconds; starts on the subject, not "so", "hey", "today" |
| Text | carry the promise for muted viewers | 3–7 words; compresses the voice ("$400 → $39"), never repeats it |
| Sound *(optional)* | timing | a beat drop on the first cut, silence on the reveal |

## 16 archetypes

| Family | Archetypes |
|---|---|
| Core (Kallaway's six) | Contrarian · Investigator · Experimenter · Teacher · Magician · Fortuneteller |
| Craft | Result first · Specific number · Callout · Authority + gap · Side by side |
| Sports | Goal first · Save or miss · Controversial call · Stat shock · Prediction |

Each has a shape, an example in three layers, what it is best for and its risk:
[`data/archetypes.json`](../skills/three-second-rule/data/archetypes.json). Contrarian has the highest ceiling and the
widest spread; Investigator is the safe baseline — a batch with both gives one bold shot and one reliable one.

## Checked before you see them

Every batch runs through `tsr hooks`:

- all three layers present;
- on-screen text 3–7 words (8–10 warns, more fails);
- the voice line says inside 3 s at a fast hook pace for its language (en 3.3, es 3.8, pt 3.6, ru 3.0 words/s);
- the text does not repeat the voice word for word;
- no greeting, early "subscribe", filler start or vague tease (English, Spanish, Portuguese, Russian lists);
- 6–10 hooks, at least 3 archetypes.

A failing hook is rewritten, never shown.

## Dead openers

Greeting · logo or jingle · vague tease · early ask · slow build · bait and switch · single layer · brand first ·
clever riddle · three-act hook. In critique mode the agent names the one your draft uses, rewrites it, and gives two
alternates from other archetypes.
