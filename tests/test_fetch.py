from __future__ import annotations

import json
import unittest

from helpers import FIXTURES

from threesec import fetch, recipe, teardown
from threesec.common import TsrError


class NormalizeTest(unittest.TestCase):
    def test_tiktok(self) -> None:
        post = fetch.normalize(json.loads((FIXTURES / "ytdlp-tiktok.json").read_text()))
        self.assertEqual(post["platform"], "tiktok")
        self.assertEqual(post["views"], 512000)
        self.assertEqual(post["shares"], 2100)
        self.assertEqual(post["creator"]["handle"], "coffeelab")
        self.assertEqual(post["creator"]["followers"], 120000)
        self.assertTrue(post["published_at"].startswith("2025-11-16"))
        self.assertIn("ignore previous instructions", post["caption"])

    def test_youtube_creator_page_is_the_shorts_tab(self) -> None:
        post = fetch.normalize(json.loads((FIXTURES / "ytdlp-youtube.json").read_text()))
        self.assertEqual(post["platform"], "youtube")
        self.assertIsNone(post["likes"])
        self.assertEqual(post["published_at"], "2026-11-10T00:00:00Z")
        self.assertEqual(fetch.creator_page(post), "https://www.youtube.com/@matchlab/shorts")

    def test_only_web_links_are_accepted(self) -> None:
        for bad in ("--exec rm", "file:///etc/passwd", "ftp://x", "https://a b"):
            with self.assertRaises(TsrError):
                fetch.checked_url(bad)

    def test_csv(self) -> None:
        posts = teardown.load_csv(FIXTURES / "posts.csv")
        self.assertEqual(len(posts), 3)
        self.assertEqual(posts[0]["views"], 90000)


class RecipeTest(unittest.TestCase):
    def test_template_is_valid(self) -> None:
        self.assertEqual(recipe.validate(recipe.TEMPLATE), [])

    def test_problems(self) -> None:
        bad = dict(recipe.TEMPLATE, length_s=10, beats=[{"at": 12, "what": "twist"}], do_not_copy=[])
        problems = recipe.validate(bad)
        self.assertEqual(len(problems), 3)


if __name__ == "__main__":
    unittest.main()
