from __future__ import annotations

import json
import re
import unittest

from helpers import ROOT

SKILL = ROOT / "skills" / "three-second-rule"


class DocsTest(unittest.TestCase):
    def test_skill_frontmatter(self) -> None:
        text = (SKILL / "SKILL.md").read_text()
        self.assertTrue(text.startswith("---\nname: three-second-rule\n"))
        description = re.search(r'description: "(.*?)"\n', text, re.S).group(1)
        self.assertLessEqual(len(description), 1024)

    def test_referenced_files_exist(self) -> None:
        text = (SKILL / "SKILL.md").read_text()
        for name in set(re.findall(r"references/([a-z-]+\.md)", text)):
            self.assertTrue((SKILL / "references" / name).is_file(), name)

    def test_every_check_is_documented(self) -> None:
        checks = json.loads((SKILL / "data" / "checks.json").read_text())["checks"]
        detail = (ROOT / "docs" / "checks.md").read_text()
        table = (SKILL / "references" / "preflight.md").read_text()
        for check in checks:
            self.assertIn(f"### {check['id']} ", detail, check["id"])
            if not check["id"].startswith("R"):
                self.assertIn(f"| {check['id']} |", table, check["id"])

    def test_every_source_is_defined(self) -> None:
        conf = json.loads((SKILL / "data" / "checks.json").read_text())
        for check in conf["checks"]:
            for key in check["source"].split("+"):
                self.assertIn(key, conf["sources"], check["id"])

    def test_counts_in_readme(self) -> None:
        readme = (ROOT / "README.md").read_text()
        archetypes = json.loads((SKILL / "data" / "archetypes.json").read_text())["archetypes"]
        checks = [c for c in json.loads((SKILL / "data" / "checks.json").read_text())["checks"]
                  if not c["id"].startswith("R")]
        self.assertIn(f"{len(archetypes)} archetypes", readme)
        self.assertIn(f"{len(checks)} checks", readme)

    def test_plugin_manifests_agree(self) -> None:
        plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text())
        market = json.loads((ROOT / ".claude-plugin" / "marketplace.json").read_text())
        self.assertEqual(plugin["name"], market["plugins"][0]["name"])
        self.assertEqual(plugin["version"], market["plugins"][0]["version"])
        from threesec.common import VERSION
        self.assertEqual(plugin["version"], VERSION)


if __name__ == "__main__":
    unittest.main()
