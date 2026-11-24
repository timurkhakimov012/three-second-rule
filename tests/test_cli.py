from __future__ import annotations

import contextlib
import io
import json
import unittest

from helpers import FIXTURES, TempDir, make_video, needs_ffmpeg

import tsr

SUBS = """1
00:00:00,820 --> 00:00:02,400
Hey guys, today I want to show you

2
00:00:02,400 --> 00:00:04,000
the one setting that doubles battery life
"""

NOTES = {
    "looked": True, "frame0": {"kind": "blank", "what": "black"}, "hook_text": "1 setting, 2x battery",
    "hook_text_tile": 5, "topic_clear_tile": 9, "visual_change_tile": None, "muted_ok": True, "layers_agree": True,
    "safe_zone_ok": True, "speaking": True, "captions": True, "payoff_delivered": True, "ending_lands": True,
}


def call(*args: str) -> tuple[int, str]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = tsr.main(list(args))
    return code, out.getvalue()


@needs_ffmpeg
class PreflightFlowTest(TempDir):
    def test_full_flow(self) -> None:
        video = make_video(self.tmp / "draft.mp4", [("black", 0.4), ("pattern", 2.6), ("red", 3.0)],
                           quiet=[(4.0, 5.5)], size=(360, 640))
        (self.tmp / "draft.srt").write_text(SUBS)
        code, text = call("preflight", str(video), "--platform", "tiktok", "--json")
        self.assertEqual(code, 0)
        result = json.loads(text)
        run_id = result["run"]["id"]
        found = {c["id"]: c["status"] for c in result["checks"]["checks"]}
        self.assertEqual(found["H1"], "fail")
        self.assertEqual(found["H3"], "warn")
        self.assertEqual(found["H9"], "fail")
        self.assertEqual(found["B1"], "fail")
        self.assertEqual(found["H4"], "not_measured")
        folder = self.home / "runs" / run_id
        (folder / "notes.json").write_text(json.dumps(NOTES))
        code, text = call("check", run_id, "--json")
        checked = {c["id"]: c["status"] for c in json.loads(text)["checks"]["checks"]}
        self.assertEqual(checked["H4"], "pass")
        self.assertEqual(checked["H1"], "fail")

        fixed = make_video(self.tmp / "draft.mp4", [("pattern", 3.0), ("red", 3.0)], size=(360, 640))
        (self.tmp / "draft.srt").write_text(SUBS.replace("00:00:00,820", "00:00:00,300"))
        code, text = call("preflight", str(fixed), "--platform", "tiktok", "--json")
        second = json.loads(text)
        self.assertIn(run_id, second["run"]["same_name_runs"])
        code, text = call("compare", run_id, second["run"]["id"], "--json")
        compared = json.loads(text)
        changed = {c["id"]: c["after"] for c in compared["changes"]}
        self.assertEqual(changed.get("H3"), "pass")
        self.assertEqual(changed.get("B1"), "pass")

        code, text = call("report", run_id, "--out", str(self.tmp / "reports"))
        self.assertEqual(code, 0)
        report = (self.tmp / "reports" / f"{run_id}.md").read_text()
        self.assertIn("## Fix first", report)
        self.assertTrue((self.tmp / "reports" / f"{run_id}-files" / "first-3s.jpg").is_file())

        code, text = call("runs")
        self.assertIn(run_id, text)

    def test_missing_file_is_a_clean_error(self) -> None:
        code, _ = call("preflight", str(self.tmp / "nope.mp4"))
        self.assertEqual(code, 2)


class CommandsTest(TempDir):
    def test_hooks_exit_code(self) -> None:
        batch = self.tmp / "hooks.json"
        batch.write_text(json.dumps({"language": "en", "hooks": [
            {"archetype": "contrarian", "visual": "x", "spoken": "Hey guys welcome back", "on_screen": "a b c"}]}))
        code, text = call("hooks", str(batch))
        self.assertEqual(code, 3)
        self.assertIn("dead opener", text)

    def test_archetypes_and_recipe_template(self) -> None:
        code, text = call("archetypes", "--family", "sports")
        self.assertIn("goal_first", text)
        code, text = call("recipe", "template", "--json")
        self.assertEqual(json.loads(text)["schema"], "tsr/recipe@1")

    def test_teardown_from_csv_without_downloads(self) -> None:
        code, text = call("teardown", "--csv", str(FIXTURES / "posts.csv"), "--no-download", "--json")
        self.assertEqual(code, 0)
        result = json.loads(text)
        self.assertTrue(result["baseline"]["usual"]["weak_basis"])
        self.assertEqual(result["run"]["watched"]["target"]["read"], False)


if __name__ == "__main__":
    unittest.main()
