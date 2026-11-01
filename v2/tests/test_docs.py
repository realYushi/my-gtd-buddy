"""Keep the V2 skill package internally consistent."""
from pathlib import Path
import re
import unittest
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "gtd"


class DocumentationTests(unittest.TestCase):
    def test_relative_links_resolve(self):
        for markdown in sorted(ROOT.rglob("*.md")):
            for target in re.findall(r"\[[^]]+\]\(([^)#]+)(?:#[^)]+)?\)", markdown.read_text()):
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                resolved = (markdown.parent / unquote(target)).resolve()
                self.assertTrue(resolved.exists(), f"{markdown}: missing {target}")

    def test_description_is_a_short_pointer(self):
        text = (SKILL / "SKILL.md").read_text()
        description = text.split("description:", 1)[1].splitlines()[0].strip()
        self.assertLessEqual(len(description.split()), 60)

    def test_router_names_every_mode(self):
        text = (SKILL / "SKILL.md").read_text()
        for mode in ("setup", "capture", "process", "coach", "waiting", "review", "health"):
            self.assertIn(f"modes/{mode}.md", text)
            self.assertTrue((SKILL / "modes" / f"{mode}.md").is_file())

    def test_core_stays_backend_neutral(self):
        text = (SKILL / "SKILL.md").read_text().casefold()
        for name in ("todoist", "google calendar", "applescript", "reminders.sh"):
            self.assertNotIn(name, text)


if __name__ == "__main__":
    unittest.main()
