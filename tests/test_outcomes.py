"""Behavior tests for durable Inbox-processing Session outcomes."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPTS = Path(__file__).resolve().parents[1] / ".claude/skills/gtd/scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("gtd_outcomes", SCRIPTS / "gtd_outcomes.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class FakeReminders:
    def __init__(self):
        self.items = {
            "r": {
                "id": "r",
                "list": "Inbox",
                "body": "original",
                "flagged": False,
                "completed": False,
                "name": "Original",
            }
        }
        self.fail = None
        self.unreadable = False
        self.patches = 0

    def read(self, rid):
        if self.unreadable:
            raise RuntimeError("offline")
        return dict(self.items[rid])

    def patch(self, rid, expected, desired):
        self.patches += 1
        item = self.items[rid]
        if any(item[key] != value for key, value in expected.items()):
            raise RuntimeError("conflict")
        for key, value in desired.items():
            item[key] = value
            if self.fail == "partial":
                raise RuntimeError("interrupted")
        if self.fail == "offline-after":
            self.unreadable = True
            raise RuntimeError("lost connection")

    def delete(self, rid):
        del self.items[rid]


class OutcomeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        directory = Path(self.temp.name)
        self.fake = FakeReminders()
        self.changes = m.ReminderChanges(self.fake, directory / "undo.json")
        self.ledger = directory / "outcomes.json"
        self.tracked = []
        self.outcomes = m.ProcessingOutcomes(self.changes, self.ledger, self.track)

    def track(self, session_id, processed, deferred, contexts):
        self.tracked.append({
            "session_id": session_id,
            "processed": processed,
            "deferred": deferred,
            "contexts": contexts,
        })

    def dispose(self, turn, disposition="later", **options):
        reply = {"type": "dispose", "reminder_id": "r", "disposition": disposition, **options}
        return self.outcomes.answer(turn["ticket"], reply)

    def test_begin_is_durable_and_single_active_process_session(self):
        first = self.outcomes.begin()
        second = self.outcomes.begin()
        self.assertEqual(first["session_id"], second["session_id"])
        self.assertEqual(first["ticket"], second["ticket"])
        self.assertEqual(first["phase"], "open")
        self.assertTrue(self.ledger.exists())

    def test_dispose_counts_one_processed_item_and_is_idempotent(self):
        turn = self.outcomes.begin()
        ticket = turn["ticket"]
        result = self.dispose(turn, context="home", energy="#low")
        self.assertEqual(result["decisions"][0]["observation"], "confirmed")
        self.assertEqual(self.fake.items["r"]["list"], "Next Actions")
        before = dict(self.fake.items["r"])
        replay = self.outcomes.answer(ticket, {
            "type": "dispose", "reminder_id": "r", "disposition": "later",
            "context": "home", "energy": "#low",
        })
        self.assertEqual(replay["ticket"], result["ticket"])
        self.assertEqual(self.fake.items["r"], before)

        closed = self.outcomes.answer(result["ticket"], {"type": "close"})
        self.assertEqual(closed["outcome"], {
            "processed": 1, "deferred": 0, "contexts": {"home": 1}, "incomplete": False,
        })
        self.assertEqual(self.tracked, [{
            "session_id": turn["session_id"], "processed": 1,
            "deferred": 0, "contexts": {"home": 1},
        }])

    def test_undo_before_close_subtracts_the_someday_decision(self):
        turn = self.outcomes.begin()
        turn = self.dispose(turn, "someday")
        decision_id = turn["decisions"][0]["decision_id"]
        turn = self.outcomes.answer(turn["ticket"], {
            "type": "undo", "decision_id": decision_id,
        })
        self.assertEqual(self.fake.items["r"]["list"], "Inbox")
        self.assertEqual(turn["decisions"][0]["undo"], "reversed")
        closed = self.outcomes.answer(turn["ticket"], {"type": "close"})
        self.assertEqual(closed["outcome"]["processed"], 0)
        self.assertEqual(closed["outcome"]["deferred"], 0)

    def test_optional_tag_failure_keeps_the_processed_disposition(self):
        self.fake.fail = "partial"
        turn = self.outcomes.begin()
        turn = self.dispose(turn, "later", context="home")
        decision = turn["decisions"][0]
        self.assertEqual(decision["observation"], "confirmed")
        self.assertEqual(decision["optional_changes"], "partial")
        self.fake.fail = None
        closed = self.outcomes.answer(turn["ticket"], {"type": "close"})
        self.assertEqual(closed["outcome"]["processed"], 1)
        self.assertEqual(closed["outcome"]["contexts"], {})

    def test_uncertain_disposition_makes_the_outcome_incomplete(self):
        self.fake.fail = "offline-after"
        turn = self.outcomes.begin()
        turn = self.dispose(turn, "later")
        decision = turn["decisions"][0]
        self.assertEqual(decision["observation"], "unknown")
        self.fake.fail = None
        self.fake.unreadable = False
        closed = self.outcomes.answer(turn["ticket"], {"type": "close"})
        self.assertTrue(closed["outcome"]["incomplete"])
        self.assertNotIn("processed", closed["outcome"])
        self.assertIsNone(self.tracked[0]["processed"])

    def test_closed_session_starts_a_new_session_and_rejects_changed_reply(self):
        turn = self.outcomes.begin()
        closed = self.outcomes.answer(turn["ticket"], {"type": "close"})
        replay = self.outcomes.answer(turn["ticket"], {"type": "close"})
        self.assertEqual(replay["session_id"], closed["session_id"])
        next_turn = self.outcomes.begin()
        self.assertNotEqual(closed["session_id"], next_turn["session_id"])
        with self.assertRaises(m.OutcomeError):
            self.outcomes.answer(turn["ticket"], {"type": "observe"})

    def test_interrupted_pending_disposition_is_observed_not_replayed(self):
        turn = self.outcomes.begin()
        reply = {"type": "dispose", "reminder_id": "r", "disposition": "later"}
        ledger = json.loads(self.ledger.read_text())
        ledger["active"]["process"]["pending"] = {
            "ticket": turn["ticket"],
            "reply": reply,
            "fingerprint": m.fingerprint(reply),
        }
        m.atomic_json(self.ledger, ledger)
        self.fake.items["r"]["list"] = "Next Actions"
        result = self.outcomes.answer(turn["ticket"], reply)
        self.assertEqual(result["decisions"][0]["observation"], "confirmed")
        self.assertEqual(self.fake.patches, 0)

    def test_close_with_pending_disposition_is_incomplete_without_mutation(self):
        turn = self.outcomes.begin()
        reply = {"type": "dispose", "reminder_id": "r", "disposition": "later"}
        ledger = json.loads(self.ledger.read_text())
        ledger["active"]["process"]["pending"] = {
            "ticket": turn["ticket"],
            "reply": reply,
            "fingerprint": m.fingerprint(reply),
        }
        m.atomic_json(self.ledger, ledger)
        closed = self.outcomes.answer(turn["ticket"], {"type": "close"})
        self.assertTrue(closed["outcome"]["incomplete"])
        self.assertNotIn("processed", closed["outcome"])
        self.assertEqual(self.fake.patches, 0)

    def test_delete_is_processed_and_cannot_be_undone(self):
        turn = self.outcomes.begin()
        turn = self.dispose(turn, "delete")
        decision = turn["decisions"][0]
        self.assertEqual(decision["observation"], "confirmed")
        self.assertEqual(decision["undo"], "permanent")
        self.assertNotIn("r", self.fake.items)
        closed = self.outcomes.answer(turn["ticket"], {"type": "close"})
        self.assertEqual(closed["outcome"]["processed"], 1)

    def test_cli_begin_reports_a_durable_ticket(self):
        env = {**os.environ, "GTD_OUTCOME_LEDGER": str(self.ledger),
               "GTD_UNDO_FILE": str(Path(self.temp.name) / "cli-undo.json")}
        result = subprocess.run(
            [str(SCRIPTS / "outcomes.sh"), "begin"], env=env,
            text=True, capture_output=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        turn = json.loads(result.stdout)
        self.assertEqual(turn["phase"], "open")
        self.assertTrue(turn["ticket"])


if __name__ == "__main__":
    unittest.main()
