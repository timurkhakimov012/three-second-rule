# Teardown

Why did that video work? A link in; the post against its own creator's usual, what its first three seconds do that
the creator's ordinary posts and flops don't, and a recipe you can film out.

## What you say

> why did this blow up? https://www.tiktok.com/@creator/video/… · break this reel down · what's the trick in this short

## The creator's usual

A view count means nothing on its own. 500,000 views is a flop for a creator who usually gets two million and a
breakthrough for one who usually gets 20,000. So the post is compared with **its own creator's usual**:

- **usual** = the median views of the creator's other posts that are at least 7 days old (3 days on X and Threads),
  read from their last 30 posts. Young posts are still growing and would pull the usual down.
- **ratio** = the post's views ÷ the usual. **Hit** ≥ 2×, **flop** ≤ 0.5×, **ordinary** 0.75–1.33×.
- Fewer than 8 settled posts → a **weak basis**, said beside the number.
- A post younger than 7 days → its ratio is a **floor**: "at least 3.1× so far".
- When fewer than 8 in 10 posts show views, likes stand in, and the answer says so.

## The comparison set

The hit alone proves nothing: whatever it shares with the creator's other posts is their style, not the reason. So the
skill also downloads **two ordinary posts** (ratio closest to 1) and **one or two flops**, measures all of them and
looks at their first three seconds side by side. Differences are written as what they are — "the hit opens on the
finished result; both ordinary posts open on a face at rest" — and stay *leads* until more than one post shows them.

## The recipe

What the hit does, as a timed template:

```json
{
  "schema": "tsr/recipe@1",
  "name": "Result first, then three steps",
  "length_s": 24,
  "cuts_per_10s": 3.1,
  "beats": [
    {"at": 0.0, "what": "hook",   "text": "the finished result, the price as text"},
    {"at": 2.2, "what": "turn",   "text": "step 1 on a hard cut", "cut": true},
    {"at": 19.5, "what": "payoff", "text": "the result again, now explained", "cut": true}
  ],
  "hook_pattern": "Result first: the finished thing, then 'here is how'",
  "do_not_copy": ["the creator's face and voice", "their catchphrase 'trust me'"],
  "tolerance": {"length_pct": 10, "cut_s": 0.25, "cuts_per_10s": 1.0}
}
```

Film it with your own material, then `check my remake against the recipe` runs a preflight with three more checks:
length, cut pace and hard cuts on the recipe's beats.

## Without a link

Instagram usually shows no list of a creator's posts without signing in, and the skill never signs in. Give the
numbers instead — a CSV with `id,url,views,published_at,title`, the post to explain first — and, if you have it, the
video file. The teardown runs from those.

## What is never claimed

- That the hit worked *because* of one thing seen on one post.
- Anything about the platform's algorithm.
- Anything about a video that could not be downloaded ("not read", with the reason).
