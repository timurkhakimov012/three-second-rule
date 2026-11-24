# Evidence: how every claim is labelled

The skill's answers are worth trusting only if each claim says where it comes from. Three labels, no others.

| Label | It means | Cite | Example |
|---|---|---|---|
| **MEASURED** | a script computed it | the file and key, or the check id | "first word at 0.82 s (MEASURED speech.json#first_word_s, from subtitle cues ±0.3 s)" |
| **SEEN** | a picture shows it | the sheet and tile (and the video for a teardown) | "the text 'One setting' is readable from tile 5, 1.00 s (SEEN first-3s)" |
| **INFERRED** | your reasoning | its basis, in the same sentence | "the payoff is delivered: the 2-day battery promised at 0.5 s is on screen at 11 s (INFERRED from shots tile 6)" |

## Rules

- A number without MEASURED is not said. If `tsr` did not compute it, it is "not measured".
- SEEN is only for what you looked at in this run. A tile you did not open is not seen.
- INFERRED is never dressed as a fact: "likely", "a lead", "on this one post" belong to it.
- A cause needs more than one post. From one hit: "the hit does X; the ordinary posts do Y" (SEEN), and at most "a
  lead" (INFERRED). Never "X is why it went viral".
- What a hit shares with ordinary posts and flops is not why it worked: say it as the creator's style.
- Platform algorithms are not observable here. "The algorithm pushed it because …" is never a claim of this skill.

## Words that are never used

"Will go viral", "guaranteed", "the algorithm loves", "virality score", "this always works". Thresholds are
heuristics; say so once per answer when a judgement call matters.

## In files

- `notes.json`: SEEN fields only, `null` when not seen.
- `findings.md` (teardown, niche): one claim per bullet, each starting with its label.
- `checks.json`: every check carries its evidence in `detail` and its threshold's source.

## In chat

Keep the labels light in the answer to the user: one word in brackets is enough, or a short "(measured)" /
"(on tile 5)". The full labels live in the files.
