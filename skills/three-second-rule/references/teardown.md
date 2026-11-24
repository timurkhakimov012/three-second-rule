# Teardown: why did this post work?

Input: a link to a post (or a local file plus the creator's numbers). Output: the post against its own creator's
usual, what its first 3 seconds do that the creator's ordinary posts and flops do not, and a timed recipe the user
can film with their own material.

## 1. Read and measure

```
tsr teardown <post link> [--limit 30] [--full] [--no-download]
```

- Reads the post and the creator's last `--limit` posts with `yt-dlp` (public pages only), scores the post against the
  creator's usual, then downloads and measures the post plus up to 4 comparison posts (2 ordinary, 1-2 flops).
- `--full` reads each post's own page: slower, but it gives dates where the list does not (YouTube lists have no
  dates). Use it when the output says posts are undated.
- `--no-download`: numbers only.
- No list available (Instagram without sign-in, a private site): ask the user for the creator's posts as CSV
  (`id,url,views,published_at,title`; the post to explain first or named with `--target`) and run
  `tsr teardown --csv posts.csv [--target ID] [--video local.mp4]`.

## 2. The numbers (MEASURED, from `baseline.json`)

- **The usual** = the median views of the creator's other posts that are at least 7 days old (3 on X and Threads),
  so still-growing posts do not pull it down. Likes stand in when fewer than 8 in 10 posts show views (said).
- **Ratio** = the post's views ÷ the usual. **Hit** ≥ 2×, **flop** ≤ 0.5×, ordinary 0.75-1.33×.
- Fewer than 8 settled posts: a **weak basis**. Say it beside the ratio.
- A post under 7 days old: its ratio is a **floor** ("at least 3.1× so far").
- Say the verdict exactly as `tsr` prints it: "4.9× its creator's usual (10,000 views): hit". A post that is big in
  absolute views but ordinary for its creator is **not** a hit, and that is a finding in itself.

## 3. Look side by side

For every watched video `tsr` prints its folder. Open each `first-3s.jpg` (at most 6 in one turn), and the target's
`shots.jpg`. Fill `notes.json` in each video folder exactly as in a preflight (`references/preflight.md`) and run
`tsr check <video folder>` on the target if you want its checklist (useful: a hit that breaks a rule is worth saying).

Then compare, and write only what the pictures and numbers show:

- What the hit does in tiles 1-12 that the ordinary posts and flops do not: the frame-0 kind, when text lands, the
  first cut, the first word, the claim's shape.
- What all of them share: that is the creator's style, not the reason.
- The measured differences (`first_word_s`, `first_cut`, `cuts_per_10s`) from each video's `probe.json`/`speech.json`.

A difference seen on one hit is a **lead**, not a cause. Write it as "the hit opens on X; the ordinary posts open on
Y" (SEEN), never "X made it go viral".

## 4. Write the recipe (`recipe.json` in the run folder)

`tsr recipe template` prints the shape; `tsr recipe check <file>` validates it.

- `length_s`, `cuts_per_10s`: start from the target's measured values; change them only with a written reason.
- `beats`: from the target's `shots.jpg` and `first-3s.jpg`, each with its time. `"cut": true` only where a measured
  cut is (`probe.json#cuts`). Kinds: hook, setup, turn, proof, payoff, ask, loop.
- `hook_pattern`, `text_style`, `sound`, `ask`: what you saw, in a reusable form.
- `evidence.from_posts`: the post ids the beats were seen on.
- `do_not_copy`: everything that is the creator's own — face, voice, footage, catchphrases, a mascot, an authority the
  user does not have. Binding for any hook or remake.

A remake filmed by the user is checked against the recipe with `tsr preflight <file> --recipe <run>/recipe.json`.

## 5. Write `findings.md` in the run folder

```
## Verdict
MEASURED baseline.json#verdict: 4.9× its creator's usual (10,000 views, 11 settled posts): hit.

## What its first 3 seconds do
- SEEN target first-3s tile 1: the finished product on frame 0, a hand already moving. Ordinary posts p3 and p7 open on a face at rest (their tile 1).
- MEASURED target speech.json#first_word_s 0.21 s vs 0.9 s and 1.3 s on the ordinary posts.
- INFERRED: the hit shows the result before the claim; the ordinary posts state the claim first. One hit: a lead, not a cause.

## What it shares with the flops (so not why)
- SEEN: the same caption style and the same yellow text box on all five.

## Not read
- flop f2: download refused (HTTP 403).
```

## 6. Answer (in the user's language)

The verdict line; 3-5 findings, each with its label; the recipe in one table (time · beat · what); "what not to
copy". Then the one offer: hooks for the user's own topic in this recipe's shape (hook lab), or a check of their remake
against the recipe. `tsr report <run> --out <folder>` saves it as a file when asked.
