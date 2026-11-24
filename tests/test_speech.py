from __future__ import annotations

import json
import unittest

from helpers import FIXTURES, TempDir

from threesec import lang, speech

SRT = """1
00:00:00,820 --> 00:00:02,000
Hey guys, <i>today</i> I want to

2
00:00:02,000 --> 00:00:03,500
show you one setting

3
00:00:05,000 --> 00:00:06,000
[music]
"""

VTT = """WEBVTT

NOTE a comment

00:00.400 --> 00:01.600 align:start
This one setting

00:01.600 --> 00:02.800
doubles your battery
"""

YOUTUBE_AUTO = """WEBVTT
Kind: captions
Language: en

00:00:00.320 --> 00:00:02.000 align:start position:0%
this<00:00:00.640><c> one</c><00:00:00.960><c> setting</c>

00:00:02.000 --> 00:00:02.010 align:start position:0%
this one setting

00:00:02.010 --> 00:00:03.500 align:start position:0%
this one setting
doubles<00:00:02.400><c> your</c><00:00:02.700><c> battery</c>
"""


class SubtitleTest(unittest.TestCase):
    def test_srt_cues(self) -> None:
        words, granularity = speech.subtitle_words(SRT)
        self.assertEqual(granularity, "cue")
        self.assertEqual(words[0]["w"], "Hey")
        self.assertAlmostEqual(words[0]["start"], 0.82)
        self.assertNotIn("music", " ".join(w["w"] for w in words))
        self.assertEqual(words[2]["w"], "today")

    def test_vtt_cues(self) -> None:
        words, granularity = speech.subtitle_words(VTT)
        self.assertEqual(granularity, "cue")
        self.assertAlmostEqual(words[0]["start"], 0.4)
        self.assertEqual(len(words), 6)

    def test_youtube_inline_timings_are_word_level(self) -> None:
        words, granularity = speech.subtitle_words(YOUTUBE_AUTO)
        self.assertEqual(granularity, "word")
        self.assertEqual([w["w"] for w in words], ["this", "one", "setting", "doubles", "your", "battery"])
        self.assertAlmostEqual(words[1]["start"], 0.64)
        self.assertAlmostEqual(words[3]["start"], 2.01)

    def test_whisper_json(self) -> None:
        body = json.loads((FIXTURES / "whisper.json").read_text())
        words, dropped, language = speech.whisper_words(body)
        self.assertEqual(language, "en")
        self.assertEqual(dropped, 1)
        self.assertEqual(words[0]["w"], "Stop")
        self.assertAlmostEqual(words[0]["start"], 0.24)

    def test_whisper_cpp_json(self) -> None:
        body = json.loads((FIXTURES / "whisper-cpp.json").read_text())
        words, _, _ = speech.whisper_words(body)
        self.assertEqual([w["w"] for w in words], ["Stop", "editing", "captions."])
        self.assertAlmostEqual(words[1]["start"], 0.52)


class MetricsTest(unittest.TestCase):
    def test_metrics(self) -> None:
        words, _ = speech.subtitle_words(SRT)
        result = speech.metrics(words, 7.0, None)
        self.assertAlmostEqual(result["first_word_s"], 0.82)
        self.assertEqual(result["language"], "en")
        self.assertTrue(result["first_3s_text"].startswith("Hey guys"))
        self.assertEqual(result["gaps"], [])

    def test_gap_is_found(self) -> None:
        words = [{"w": "one", "start": 0.2, "end": 0.5}, {"w": "two", "start": 1.6, "end": 1.9}]
        self.assertEqual(speech.metrics(words, 3.0, "en")["gaps"][0]["length"], 1.1)

    def test_empty(self) -> None:
        self.assertIsNone(speech.metrics([], 5.0, None)["first_word_s"])


class SidecarTest(TempDir):
    def test_finds_subtitles_next_to_video(self) -> None:
        video = self.tmp / "my [draft].mp4"
        video.write_bytes(b"")
        (self.tmp / "my [draft].en.vtt").write_text(VTT)
        self.assertEqual(speech.find_sidecar(video).name, "my [draft].en.vtt")


class LanguageTest(unittest.TestCase):
    def test_guess(self) -> None:
        self.assertEqual(lang.guess("this is the one thing you need to do with your phone"), "en")
        self.assertEqual(lang.guess("esto es lo que tienes que hacer con el teléfono para que dure más"), "es")
        self.assertEqual(lang.guess("это то что ты должен сделать если хочешь но не можешь"), "ru")
        self.assertIsNone(lang.guess("ok"))

    def test_phrase_matching_uses_word_boundaries(self) -> None:
        self.assertTrue(lang.contains("Hey guys, what's up", "hey guys"))
        self.assertFalse(lang.contains("theyguys", "hey guys"))
        self.assertTrue(lang.starts_with("Okay so here's the thing", "okay so"))


if __name__ == "__main__":
    unittest.main()
