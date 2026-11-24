from __future__ import annotations

import copy
import unittest

import helpers  # noqa: F401

from threesec import checks

PROBE = {
    "duration": 18.0, "width": 1080, "height": 1920, "aspect": "9:16", "vertical": True, "has_audio": True,
    "cuts": [1.4, 4.0, 8.0, 12.0], "first_cut": 1.4, "cuts_per_10s": 2.2, "black_at_start": 0.0,
    "frozen_at_start": 0.0, "longest_shot": {"n": 3, "start": 4.0, "end": 8.0, "length": 4.0},
    "motion": {"first_half_second": 0.03, "first_three_seconds": 0.2, "frame0": {"flat": False}},
    "audio": {"silences": [], "integrated_lufs": -14.5},
}
SPEECH = {"words": 40, "first_word_s": 0.3, "source": "whisper", "granularity": "word", "language": "en",
          "first_3s_text": "Your camera has a setting that fixes shaky video",
          "transcript": "Your camera has a setting that fixes shaky video. Save this for later."}
NOTES = {
    "looked": True, "frame0": {"kind": "action", "what": "a hand opening the camera app"},
    "hook_text": "1 setting fixes shaky video", "hook_text_tile": 4, "topic_clear_tile": 6,
    "visual_change_tile": None, "muted_ok": True, "layers_agree": True, "safe_zone_ok": True,
    "speaking": True, "captions": True, "payoff_delivered": True, "ending_lands": True,
}


def statuses(probe=PROBE, speech=SPEECH, notes=NOTES, **extra) -> dict:
    outcome = checks.evaluate(probe, speech, notes, **extra)
    return {row["id"]: row["status"] for row in outcome["checks"]}


def changed(base: dict, **updates) -> dict:
    copied = copy.deepcopy(base)
    copied.update(updates)
    return copied


class ChecklistTest(unittest.TestCase):
    def test_a_good_video_passes_everything(self) -> None:
        result = statuses()
        self.assertTrue(all(value == "pass" for value in result.values()), result)

    def test_black_opening_fails(self) -> None:
        self.assertEqual(statuses(probe=changed(PROBE, black_at_start=0.5))["H1"], "fail")

    def test_still_opening_fails(self) -> None:
        still = changed(PROBE, first_cut=2.0, frozen_at_start=1.2,
                        motion={"first_half_second": 0.0, "first_three_seconds": 0.0, "frame0": {"flat": True}})
        self.assertEqual(statuses(probe=still)["H2"], "fail")

    def test_first_word_thresholds(self) -> None:
        self.assertEqual(statuses(speech=changed(SPEECH, first_word_s=0.8))["H3"], "warn")
        self.assertEqual(statuses(speech=changed(SPEECH, first_word_s=1.4))["H3"], "fail")

    def test_first_word_not_measured_without_transcript(self) -> None:
        speech = {"words": 0, "not_measured": "no subtitles"}
        result = checks.evaluate(PROBE, speech, NOTES)
        row = next(r for r in result["checks"] if r["id"] == "H3")
        self.assertEqual(row["status"], "not_measured")
        self.assertIn("no subtitles", row["detail"])

    def test_late_or_long_hook_text(self) -> None:
        self.assertEqual(statuses(notes=changed(NOTES, hook_text_tile=9))["H4"], "warn")
        self.assertEqual(statuses(notes=changed(NOTES, hook_text_tile=12))["H4"], "fail")
        long_text = "this is a very long hook text that nobody will read in one second flat"
        self.assertEqual(statuses(notes=changed(NOTES, hook_text=long_text))["H4"], "fail")

    def test_no_hook_text_is_softer_when_the_picture_carries_it(self) -> None:
        self.assertEqual(statuses(notes=changed(NOTES, hook_text=None, hook_text_tile=None))["H4"], "warn")
        notes = changed(NOTES, hook_text=None, hook_text_tile=None, muted_ok=False)
        self.assertEqual(statuses(notes=notes)["H4"], "fail")

    def test_text_that_repeats_the_voice_warns(self) -> None:
        notes = changed(NOTES, hook_text="Your camera has a setting that fixes shaky video")
        self.assertEqual(statuses(notes=notes)["H8"], "warn")

    def test_dead_openers(self) -> None:
        self.assertEqual(statuses(speech=changed(SPEECH, first_3s_text="Hey guys welcome back"))["H9"], "fail")
        self.assertEqual(statuses(speech=changed(SPEECH, first_3s_text="Okay so this camera"))["H9"], "warn")
        self.assertEqual(statuses(speech=changed(SPEECH, first_3s_text="You won't believe this camera"))["H9"], "warn")

    def test_opener_in_other_languages(self) -> None:
        spanish = changed(SPEECH, language="es", first_3s_text="Hola a todos, hoy les voy a mostrar")
        self.assertEqual(statuses(speech=spanish)["H9"], "fail")
        russian = changed(SPEECH, language="ru", first_3s_text="Всем привет, сегодня я покажу")
        self.assertEqual(statuses(speech=russian)["H9"], "fail")

    def test_unknown_language_is_not_measured(self) -> None:
        speech = changed(SPEECH, language="ja", first_3s_text="こんにちは")
        notes = changed(NOTES, hook_text=None, hook_text_tile=None)
        self.assertEqual(statuses(speech=speech, notes=notes)["H9"], "not_measured")

    def test_dead_air(self) -> None:
        self.assertEqual(statuses(probe=changed(PROBE, audio={"silences": [[5.0, 5.9]], "integrated_lufs": -14}))["B1"], "warn")
        self.assertEqual(statuses(probe=changed(PROBE, audio={"silences": [[5.0, 7.0]], "integrated_lufs": -14}))["B1"], "fail")
        self.assertEqual(statuses(probe=changed(PROBE, audio={"silences": [[17.7, 18.0]], "integrated_lufs": -14}))["B1"], "pass")

    def test_two_kinds_of_ask_warn(self) -> None:
        speech = changed(SPEECH, transcript="Follow me for more and comment CAMERA below")
        self.assertEqual(statuses(speech=speech)["B4"], "warn")

    def test_format_and_loudness(self) -> None:
        self.assertEqual(statuses(probe=changed(PROBE, width=1920, height=1080, aspect="16:9"))["T1"], "fail")
        self.assertEqual(statuses(probe=changed(PROBE, width=720, height=1280, aspect="9:16"))["T1"], "pass")
        self.assertEqual(statuses(probe=changed(PROBE, audio={"silences": [], "integrated_lufs": -24}))["T3"], "fail")

    def test_length_limit_by_platform(self) -> None:
        long_video = changed(PROBE, duration=200.0)
        self.assertEqual(statuses(probe=long_video, chosen_platforms=["tiktok"])["T5"], "pass")
        self.assertEqual(statuses(probe=long_video, chosen_platforms=["reels"])["T5"], "fail")
        self.assertEqual(statuses(probe=long_video)["T5"], "warn")

    def test_without_notes_seen_checks_wait(self) -> None:
        outcome = checks.evaluate(PROBE, SPEECH, None)
        waiting = {r["id"] for r in outcome["checks"] if r["status"] == "not_measured"}
        self.assertTrue({"H4", "H5", "H7", "H8", "B3", "B5", "T2", "T4"} <= waiting)
        self.assertFalse(outcome["looked"])

    def test_notes_must_say_looked(self) -> None:
        outcome = checks.evaluate(PROBE, SPEECH, changed(NOTES, looked=False))
        self.assertFalse(outcome["looked"])

    def test_bad_notes_are_reported(self) -> None:
        clean, problems = checks.validate_notes(changed(NOTES, hook_text_tile=40, frame0={"kind": "cat"}))
        self.assertIsNone(clean["hook_text_tile"])
        self.assertEqual(len(problems), 3)

    def test_recipe_checks(self) -> None:
        recipe = {"length_s": 18.0, "cuts_per_10s": 2.0, "tolerance": {"cut_s": 0.25},
                  "beats": [{"at": 1.5, "what": "turn", "cut": True}, {"at": 10.0, "what": "payoff", "cut": True}]}
        result = statuses(recipe=recipe)
        self.assertEqual(result["R1"], "pass")
        self.assertEqual(result["R2"], "pass")
        self.assertEqual(result["R3"], "fail")

    def test_summary_line(self) -> None:
        outcome = checks.evaluate(changed(PROBE, black_at_start=0.5), SPEECH, NOTES)
        self.assertIn("1 failed", outcome["summary"]["line"])
        self.assertIn("Fix first", checks.text_table(outcome))


if __name__ == "__main__":
    unittest.main()
