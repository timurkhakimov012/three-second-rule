from __future__ import annotations

import unittest

from helpers import TempDir, make_video, needs_ffmpeg

from threesec import image, probe, sheets


class ImageTest(unittest.TestCase):
    def test_text_draws_pixels(self) -> None:
        canvas = image.Image(60, 30, (10, 10, 10))
        canvas.text(0, 0, "12 0.25s", scale=1)
        self.assertIn(255, canvas.pixels)

    def test_paste_clips_at_edges(self) -> None:
        canvas = image.Image(4, 4)
        canvas.paste(image.Image(3, 3, (200, 0, 0)), 2, 2)
        self.assertEqual(canvas.pixels[(3 * 4 + 3) * 3], 200)
        self.assertEqual(canvas.pixels[0], 0)

    def test_union_zone_takes_the_largest_side(self) -> None:
        zone = sheets.union_zone(sheets.platforms(["tiktok", "reels"]))
        self.assertEqual(zone["top"], 0.12)
        self.assertEqual(zone["right"], 0.13)


@needs_ffmpeg
class SheetsTest(TempDir):
    def test_all_three_sheets(self) -> None:
        video = make_video(self.tmp / "v.mp4", [("red", 1.0), ("pattern", 2.5), ("blue", 1.5)], size=(360, 640))
        measured = probe.measure(video)
        drawn = sheets.draw_all(video, measured, self.tmp / "out", ["tiktok"])
        self.assertEqual(len(drawn["first_3s"]["tiles"]), 12)
        self.assertEqual(drawn["first_3s"]["tiles"][4]["t"], 1.0)
        kinds = [t["kind"] for t in drawn["shots"]["tiles"]]
        self.assertEqual(kinds[0], "start")
        self.assertEqual(kinds[-1], "end")
        self.assertEqual(kinds.count("cut"), 2)
        for name in ("first-3s.jpg", "shots.jpg", "safe-zones.jpg"):
            self.assertGreater((self.tmp / "out" / name).stat().st_size, 1000)

    def test_short_video_and_landscape(self) -> None:
        video = make_video(self.tmp / "short.mp4", [("pattern", 1.0)], size=(320, 180))
        measured = probe.measure(video)
        drawn = sheets.draw_all(video, measured, self.tmp / "out")
        self.assertLessEqual(len(drawn["first_3s"]["tiles"]), 5)
        self.assertIsNone(drawn["safe_zones"]["file"])
        self.assertIn("9:16 only", drawn["safe_zones"]["skipped"])


if __name__ == "__main__":
    unittest.main()
