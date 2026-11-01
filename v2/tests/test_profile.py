"""Profile validation tests for the V2 skill."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "gtd"
VALIDATOR = SKILL / "scripts" / "validate_profile.py"
spec = importlib.util.spec_from_file_location("validate_profile", VALIDATOR)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def example(name):
    return json.loads((SKILL / "backends" / name).read_text())


class ProfileTests(unittest.TestCase):
    def setUp(self):
        self.profile = example("todoist-google.example.json")

    def errors(self, document):
        return validator.validate(document)

    def test_examples_validate(self):
        self.assertEqual(self.errors(example("todoist-google.example.json")), [])
        self.assertEqual(self.errors(example("manual.example.json")), [])

    def test_manual_mode_needs_no_tools(self):
        profile = example("manual.example.json")
        self.assertEqual(profile["task"]["mode"], "manual")
        self.assertEqual(profile["task"]["tools"], {})
        self.assertEqual(self.errors(profile), [])

    def test_missing_container_fails(self):
        profile = copy.deepcopy(self.profile)
        del profile["task"]["containers"]["waiting"]
        self.assertTrue(any("task.containers.waiting" in error for error in self.errors(profile)))

    def test_duplicate_containers_fail(self):
        profile = copy.deepcopy(self.profile)
        profile["task"]["containers"]["waiting"] = "Next Actions"
        self.assertTrue(any("distinct" in error for error in self.errors(profile)))

    def test_mcp_requires_capture_tool(self):
        profile = copy.deepcopy(self.profile)
        del profile["task"]["tools"]["capture"]
        self.assertTrue(any("task.tools.capture" in error for error in self.errors(profile)))

    def test_completed_query_requires_tool(self):
        profile = copy.deepcopy(self.profile)
        del profile["task"]["tools"]["completed"]
        self.assertTrue(any("task.tools.completed" in error for error in self.errors(profile)))

    def test_delete_requires_tool(self):
        profile = copy.deepcopy(self.profile)
        del profile["task"]["tools"]["delete"]
        self.assertTrue(any("task.tools.delete" in error for error in self.errors(profile)))

    def test_freebusy_requires_tool(self):
        profile = copy.deepcopy(self.profile)
        del profile["calendar"]["tools"]["freebusy"]
        self.assertTrue(any("calendar.tools.freebusy" in error for error in self.errors(profile)))

    def test_optional_capabilities_are_booleans(self):
        profile = copy.deepcopy(self.profile)
        profile["task"]["capabilities"]["modified_date"] = "yes"
        self.assertTrue(any("task.capabilities.modified_date" in error for error in self.errors(profile)))

    def test_workday_must_be_ordered(self):
        profile = copy.deepcopy(self.profile)
        profile["calendar"]["workday"] = "18:00-09:00"
        self.assertTrue(any("start must be before end" in error for error in self.errors(profile)))

    def test_credentials_are_rejected(self):
        profile = copy.deepcopy(self.profile)
        profile["task"]["tools"]["api_key"] = "do-not-store-me"
        self.assertTrue(any("credential" in error for error in self.errors(profile)))

    def test_cli_reports_valid_and_invalid(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "profile.json"
            path.write_text(json.dumps(self.profile))
            result = subprocess.run([str(VALIDATOR), str(path)], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)["status"], "valid")
            path.write_text("{}")
            result = subprocess.run([str(VALIDATOR), str(path)], text=True, capture_output=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)["status"], "invalid")


if __name__ == "__main__":
    unittest.main()
