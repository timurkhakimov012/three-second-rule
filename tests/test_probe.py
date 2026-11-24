from __future__ import annotations

import unittest

from helpers import TempDir, make_video, needs_ffmpeg

from threesec import probe


@needs_ffmpeg
class ProbeTest(TempDir):
    def test_known_answers(self) -> None:
        video = make_video(self.tmp / "a.mp4", [("black", 1.0), ("red", 1.5), ("pattern", 2.0)], quiet=[(1.0, 2.0)])
        measured = probe.measure(video)
        self.assertEqual(measured["aspect"], "9:16")
        self.assertTrue(measured["vertical"])
        self.assertAlmostEqual(measured["duration"], 4.5, delta=0.1)
        self.assertEqual(len(measured["cuts"]), 2)
        self.assertAlmostEqual(measured["cuts"][0], 1.0, delta=0.1)
        self.assertAlmostEqual(measured["cuts"][1], 2.5, delta=0.1)
        self.assertAlmostEqual(measured["black_at_start"], 1.0, delta=0.1)
        self.assertTrue(measured["motion"]["frame0"]["flat"])
        silences = measured["audio"]["silences"]
        self.assertEqual(len(silences), 1)
        self.assertAlmostEqual(silences[0][0], 1.0, delta=0.1)
        self.assertAlmostEqual(silences[0][1], 2.0, delta=0.1)
        self.assertIsNotNone(measured["audio"]["integrated_lufs"])
        self.assertEqual(measured["longest_shot"]["n"], 3)

    def test_still_versus_moving_opening(self) -> None:
        still = probe.measure(make_video(self.tmp / "still.mp4", [("blue", 2.0)]))
        moving = probe.measure(make_video(self.tmp / "moving.mp4", [("pattern", 2.0)]))
        self.assertLess(still["motion"]["first_half_second"], 0.002)
        self.assertGreater(moving["motion"]["first_half_second"], 0.008)
        self.assertGreaterEqual(still["frozen_at_start"], 0.5)
        self.assertEqual(still["cut_count"], 0)

    def test_no_audio_and_landscape(self) -> None:
        measured = probe.measure(make_video(self.tmp / "wide.mp4", [("pattern", 1.5)], audio=False, size=(320, 180)))
        self.assertFalse(measured["has_audio"])
        self.assertIsNone(measured["audio"])
        self.assertEqual(measured["aspect"], "16:9")
        self.assertFalse(measured["vertical"])

    def test_merge_close_cuts(self) -> None:
        self.assertEqual(probe.merge_close([1.0, 1.1, 1.5, 3.0]), [1.0, 1.5, 3.0])

    def test_rotation_swaps_dimensions(self) -> None:
        stream = {"side_data_list": [{"side_data_type": "Display Matrix", "rotation": -90}]}
        self.assertEqual(probe.stream_rotation(stream), 270)


if __name__ == "__main__":
    unittest.main()
