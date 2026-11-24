from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

import helpers  # noqa: F401

from threesec import baseline

READ_AT = datetime(2026, 11, 20, tzinfo=timezone.utc)


def post(post_id: str, views: int, days_ago: float, platform: str = "tiktok") -> dict:
    return {"id": post_id, "platform": platform, "views": views, "url": f"https://example.com/{post_id}",
            "published_at": (READ_AT - timedelta(days=days_ago)).isoformat()}


def creator(target_views: int = 50_000, target_age: float = 10) -> tuple[dict, list[dict]]:
    usual = [10_000, 9_000, 11_000, 10_500, 9_500, 12_000, 8_000, 10_000, 11_500, 9_800]
    posts = [post(f"p{n}", v, 12 + n * 3) for n, v in enumerate(usual)]
    posts.append(post("flop1", 2_000, 15))
    posts.append(post("young", 500, 1))
    return post("target", target_views, target_age), posts


class BaselineTest(unittest.TestCase):
    def test_hit_against_the_creators_usual(self) -> None:
        target, posts = creator()
        result = baseline.score(target, posts, READ_AT)
        self.assertEqual(result["usual"]["from_posts"], 11)
        self.assertAlmostEqual(result["usual"]["value"], 10_000, delta=600)
        self.assertEqual(result["target"]["label"], "hit")
        self.assertGreater(result["target"]["ratio"], 4.5)
        self.assertEqual(result["target"]["rank"], 1)
        self.assertEqual(result["usual"]["left_out_still_growing"], 1)

    def test_picks_ordinary_and_flops(self) -> None:
        target, posts = creator()
        picks = baseline.score(target, posts, READ_AT)["picks"]
        self.assertEqual(len(picks["ordinary"]), 2)
        self.assertEqual(picks["flops"], ["flop1"])
        self.assertNotIn("young", picks["ordinary"] + picks["flops"])

    def test_still_growing_target_is_a_floor(self) -> None:
        target, posts = creator(target_views=30_000, target_age=2)
        result = baseline.score(target, posts, READ_AT)
        self.assertTrue(result["target"]["still_growing"])
        self.assertIsNone(result["target"]["label"])
        self.assertIn("at least", result["verdict"])

    def test_weak_basis_is_said(self) -> None:
        target, posts = creator()
        result = baseline.score(target, posts[:4], READ_AT)
        self.assertTrue(result["usual"]["weak_basis"])
        self.assertTrue(any("weak basis" in n for n in result["notes"]))

    def test_falls_back_to_likes(self) -> None:
        target, posts = creator()
        for item in [target] + posts:
            item["likes"] = item.pop("views") // 10
        result = baseline.score(target, posts, READ_AT)
        self.assertEqual(result["metric"], "likes")

    def test_x_settles_faster(self) -> None:
        self.assertEqual(baseline.settle_days("x"), 3)
        self.assertEqual(baseline.settle_days("tiktok"), 7)


if __name__ == "__main__":
    unittest.main()
