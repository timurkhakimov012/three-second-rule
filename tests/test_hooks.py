from __future__ import annotations

import unittest

import helpers  # noqa: F401

from threesec import hooks

GOOD = [
    {"archetype": "contrarian", "visual": "two cups, price tags", "spoken": "Your $300 grinder is the problem.",
     "on_screen": "$300 vs $39"},
    {"archetype": "investigator", "visual": "thumb opening settings", "spoken": "There's a hidden grind setting.",
     "on_screen": "1 hidden setting"},
    {"archetype": "number", "visual": "a pile of gear", "spoken": "I burned $413 on coffee gear.",
     "on_screen": "$413 -> $39"},
    {"archetype": "result_first", "visual": "the finished latte art", "spoken": "Twelve seconds, no machine.",
     "on_screen": "12 s, no machine"},
    {"archetype": "callout", "visual": "a sour face over a cup", "spoken": "If your coffee tastes sour, read this.",
     "on_screen": "sour coffee? fix"},
    {"archetype": "comparison", "visual": "split screen, two cups", "spoken": "Same beans, two grinds.",
     "on_screen": "fine vs coarse"},
]


class HookBatchTest(unittest.TestCase):
    def test_good_batch_passes(self) -> None:
        result = hooks.check_batch({"language": "en", "hooks": GOOD})
        self.assertEqual(result["status"], "pass", hooks.text_report(result))

    def test_dead_openers_fail(self) -> None:
        bad = dict(GOOD[0], spoken="Hey guys, welcome back to my channel")
        tease = dict(GOOD[1], spoken="You won't believe this grinder")
        filler = dict(GOOD[2], spoken="Okay so this grinder is great")
        result = hooks.check_batch({"language": "en", "hooks": [bad, tease, filler] + GOOD[3:]})
        self.assertEqual([h["status"] for h in result["hooks"][:3]], ["fail", "fail", "fail"])

    def test_too_long_to_say(self) -> None:
        long_line = dict(GOOD[0], spoken="I have been making coffee every single morning for twelve years and here "
                                         "is the one thing nobody ever tells you about grinders")
        result = hooks.check_batch({"language": "en", "hooks": [long_line] + GOOD[1:]})
        self.assertEqual(result["hooks"][0]["status"], "fail")

    def test_missing_layers(self) -> None:
        result = hooks.check_batch({"language": "en", "hooks": [dict(GOOD[0], visual="", on_screen="")] + GOOD[1:]})
        messages = [f["check"] for f in result["hooks"][0]["findings"]]
        self.assertIn("visual", messages)
        self.assertIn("on_screen", messages)

    def test_too_few_archetypes(self) -> None:
        same = [dict(h, archetype="contrarian") for h in GOOD]
        result = hooks.check_batch({"language": "en", "hooks": same})
        self.assertEqual(result["status"], "fail")
        self.assertTrue(any(f["check"] == "batch" for f in result["batch"]))

    def test_language_is_guessed(self) -> None:
        spanish = [dict(h, spoken="Hola a todos, esto es lo que tienes que hacer con el café") for h in GOOD]
        result = hooks.check_batch({"hooks": spanish})
        self.assertEqual(result["language"], "es")
        self.assertEqual(result["hooks"][0]["status"], "fail")


if __name__ == "__main__":
    unittest.main()
