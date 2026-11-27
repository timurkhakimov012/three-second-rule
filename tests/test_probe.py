from __future__ import annotations

import subprocess

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

    def test_split_screen_cut_in_one_half(self) -> None:
        video = self.tmp / "split.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc2=s=180x160:r=25:d=6",
            "-f", "lavfi", "-i", "color=c=red:s=180x160:r=25:d=3",
            "-f", "lavfi", "-i", "color=c=blue:s=180x160:r=25:d=3",
            "-filter_complex", "[1:v][2:v]concat=n=2:v=1[b];[0:v][b]vstack,format=yuv420p",
            "-c:v", "libx264", "-preset", "ultrafast", str(video),
        ], check=True)
        measured = probe.measure(video)
        self.assertEqual(measured["cuts"], [])
        self.assertEqual(len(measured["region_cuts"]), 1)
        self.assertAlmostEqual(measured["region_cuts"][0], 3.0, delta=0.1)
        self.assertAlmostEqual(measured["longest_unchanged"]["length"], 3.0, delta=0.1)

    def test_most_active_window_skips_the_opening_and_cuts(self) -> None:
        changes = [{"t": round(n * 0.25, 2), "change": 0.01} for n in range(1, 24)]
        for point in changes:
            if point["t"] in (3.25, 3.5):
                point["change"] = 0.08
            if point["t"] == 4.5:
                point["change"] = 0.9
        best = probe.most_active(changes, [4.4], 0.25)
        self.assertEqual(best["start"], 3.0)
        self.assertEqual(best["end"], 3.5)
        self.assertEqual(probe.most_active(changes[:2], [], 0.25), None)

    def test_aspect_labels(self) -> None:
        self.assertEqual(probe.aspect_label(1080, 1920), "9:16")
        self.assertEqual(probe.aspect_label(704, 576), "11:9")
        self.assertEqual(probe.aspect_label(1080, 1350), "4:5")

    def test_merge_close_cuts(self) -> None:
        self.assertEqual(probe.merge_close([1.0, 1.1, 1.5, 3.0]), [1.0, 1.5, 3.0])

    def test_rotation_swaps_dimensions(self) -> None:
        stream = {"side_data_list": [{"side_data_type": "Display Matrix", "rotation": -90}]}
        self.assertEqual(probe.stream_rotation(stream), 270)


if __name__ == "__main__":
    unittest.main()
