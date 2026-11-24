# Niche map: which openings and formats work now

Input: a niche (words, tags), a list of creators, or one account ("what works for me"). Output: the posts that beat
their own creator's usual, the formats behind them placed on a map, which are rising and which fade, and the openings
of the winners.

## 1. Set up and read

```
tsr niche init "<niche name>" [--words ...] [--platform tiktok]
tsr niche add <run id> <creator profile link> [--limit 25] [--full]     # once per creator, 5 to 10 creators
tsr niche add <run id> --csv <creator.csv>                               # when no list can be read
```

- Choose creators who post in the niche regularly, of different sizes. Ask the user for seeds, or use the creators
  they named. Never guess a handle: a creator that cannot be found is named in the answer and counts for nothing.
- One account ("what works for me"): init a niche with that one creator. The map then compares the account's formats
  against its own usual (scope "account").
- YouTube lists have no dates: use `--full` (slower) or the posts count as undated and cannot be scored.

## 2. Rank

```
tsr niche rank <run id> [--window 30]
```

Every post of the window against **its own creator's usual**: the median of the creator's other settled posts from the
window and the 30 days before it (at least 8; still-growing posts left out). A **trend** is 2× or more. A creator with
fewer settled posts is ranked on views per follower, labelled weaker, and never counts toward a format.

Statuses: `ok`; `too_few_creators` (under 3 with their own usual); `too_few_posts` (under 20 scored); `empty`. In the
last three, list the trends and call no format of the niche; offer to read more creators.

## 3. Watch

```
tsr niche watch <run id>
```

Downloads and measures the deep-read picks: the top trends (at most 2 per creator), 3 ordinary posts and 2 flops of
different creators. Open their `first-3s.jpg` sheets (at most 6 per turn) and fill each video's `notes.json` as in a
preflight.

## 4. Group into formats (`formats.json` in the run folder)

A **format** is a repeatable container: a kind of hook, a structure, a look, a length. "Three mistakes, talking head
over a screenshot, 25 s" is a format; "a video about pricing" is a topic.

```json
{"formats": [
  {"id": "result-first-demo", "name": "Result first, then the steps",
   "container": {"hook": "the finished result on frame 0", "structure": "result → 3 steps → result again",
                 "look": "hands only, top-down", "length": "20-30 s"},
   "effort": "medium",
   "post_ids": ["7301...", "7302..."]}
]}
```

- Group from what you saw (the sheets) and the titles; name a format only for something repeated. One-offs stay out.
- A post belongs to one format at most.

## 5. Map

```
tsr niche formats <run id>
```

Per format: the creators using it, its share, its **lift** (the median of each creator's median ratio, so one prolific
creator cannot carry it), its hit rate, and its **direction** (later half of the window ÷ earlier half: rising ≥ 1.33,
fading < 0.75, else steady; null with too few posts).

| Corner | Where it sits | Say |
|---|---|---|
| Scale it | used by ≥ 40% of creators (≥ 15% of posts for one account), lift ≥ 1 | make it now (unless fading: say so) |
| Underused | rarer, lift ≥ 1 | it works where it is used: an opening |
| Overused | common, lift < 1 | everyone has it, it no longer lifts |
| Drop | rare, lift < 1 | skip it |

A format with fewer than 3 creators is **not a format of the niche**: it is one creator's habit (or "few creators"),
shown as such. 3-5 scored posts: shown, marked "few posts", never a finding on its own. The output lists problems
(a post in two formats, an id not in the window): fix `formats.json` and run it again.

## 6. Answer

1. The status line and what was read ("8 creators, 142 scored posts, last 30 days").
2. The map, best first: format · corner · lift · creators · direction. The fading and overused ones are said as
   plainly as the winners.
3. For the top 1-2 formats: the openings of their winning posts (SEEN, tile numbers, two creators at least) and a
   recipe (`references/teardown.md`, step 4) built from watched posts of at least two creators.
4. Who to watch: the creators with the most trends.
5. The one offer: hooks in the strongest format for the user's topic, or a teardown of one of its posts.
