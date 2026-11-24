from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from helpers import TempDir

from threesec import niche
from threesec.common import write_json

READ_AT = datetime(2026, 11, 20, tzinfo=timezone.utc)


def make_posts(prefix: str, rising: list[str], fading: list[str]) -> list[dict]:
    posts = []
    for n in range(12):
        posts.append({"id": f"{prefix}-old{n}", "platform": "tiktok", "views": 10_000 + n * 100,
                      "published_at": (READ_AT - timedelta(days=35 + n)).isoformat()})
    for n, post_id in enumerate(rising):
        days = 25 - n * 6
        views = 30_000 if days < 15 else 12_000
        posts.append({"id": post_id, "platform": "tiktok", "views": views,
                      "published_at": (READ_AT - timedelta(days=days)).isoformat()})
    for n, post_id in enumerate(fading):
        days = 26 - n * 6
        views = 12_000 if days >= 15 else 4_000
        posts.append({"id": post_id, "platform": "tiktok", "views": views,
                      "published_at": (READ_AT - timedelta(days=days)).isoformat()})
    return posts


class NicheTest(TempDir):
    def setUp(self) -> None:
        super().setUp()
        self.folder = self.tmp / "niche-coffee"
        self.rising_ids, self.fading_ids = [], []
        for creator in ("a", "b", "c", "d"):
            rising = [f"{creator}-r{n}" for n in range(3)]
            fading = [f"{creator}-f{n}" for n in range(3)]
            self.rising_ids += rising
            self.fading_ids += fading
            niche.save_creator(self.folder, "tiktok", creator, {"handle": creator}, make_posts(creator, rising, fading))
        habit_posts = make_posts("e", [], [])
        habit_posts += [{"id": f"e-h{n}", "platform": "tiktok", "views": 40_000,
                         "published_at": (READ_AT - timedelta(days=20 - n)).isoformat()} for n in range(3)]
        niche.save_creator(self.folder, "tiktok", "e", {"handle": "e"}, habit_posts)

    def test_rank_and_format_map(self) -> None:
        trends = niche.rank(self.folder, read_at=READ_AT)
        self.assertEqual(trends["status"], "ok")
        self.assertEqual(len(trends["creators_with_own_usual"]), 5)
        self.assertTrue(all(row["ratio"] >= 2 for row in trends["trends"]))
        write_json(self.folder / "formats.json", {"formats": [
            {"id": "rising", "name": "Rising format", "post_ids": self.rising_ids},
            {"id": "fading", "name": "Fading format", "post_ids": self.fading_ids},
            {"id": "habit", "name": "One creator's habit", "post_ids": ["e-h0", "e-h1", "e-h2"]},
        ]})
        result = niche.map_formats(self.folder)
        by_id = {f["id"]: f for f in result["formats"]}
        self.assertEqual(result["scope"], "niche")
        self.assertEqual(by_id["rising"]["direction_label"], "rising")
        self.assertEqual(by_id["rising"]["quadrant"], "scale_it")
        self.assertEqual(by_id["fading"]["direction_label"], "fading")
        self.assertEqual(by_id["habit"]["scope_status"], "creator habit")
        self.assertEqual(by_id["habit"]["quadrant"], "too_few")
        self.assertEqual(result["problems"], [])

    def test_overlap_and_unknown_posts_are_problems(self) -> None:
        niche.rank(self.folder, read_at=READ_AT)
        write_json(self.folder / "formats.json", {"formats": [
            {"id": "one", "post_ids": ["a-r0", "a-r1"]},
            {"id": "two", "post_ids": ["a-r1", "nope"]},
        ]})
        problems = niche.map_formats(self.folder)["problems"]
        self.assertEqual(len(problems), 2)

    def test_too_few_creators(self) -> None:
        folder = self.tmp / "niche-small"
        niche.save_creator(folder, "tiktok", "a", {"handle": "a"}, make_posts("a", ["a-r0"], []))
        niche.save_creator(folder, "tiktok", "b", {"handle": "b"}, make_posts("b", ["b-r0"], []))
        self.assertEqual(niche.rank(folder, read_at=READ_AT)["status"], "too_few_creators")

    def test_one_account_is_its_own_scope(self) -> None:
        folder = self.tmp / "niche-me"
        niche.save_creator(folder, "tiktok", "me", {"handle": "me"}, make_posts("me", ["me-r0"], ["me-f0"]))
        result = niche.rank(folder, read_at=READ_AT)
        self.assertEqual(result["scope"], "account")
        self.assertEqual(result["status"], "too_few_posts")


if __name__ == "__main__":
    unittest.main()
