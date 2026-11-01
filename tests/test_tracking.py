"""Integration tests: python3 -m unittest discover -s tests.

These tests invoke state.sh and the real mikefarah yq found on PATH. No Python
YAML package or fake YAML parser is used. Each test owns an isolated state file.
"""

import concurrent.futures
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
import uuid


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / ".claude/skills/gtd/scripts/state.sh"
TEMPLATE = ROOT / ".claude/skills/gtd/state.yaml.template"
NOW = "2026-11-02T12:00:00-08:00"


class TrackingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.yq = shutil.which("yq")
        if cls.yq is None:
            raise unittest.SkipTest("real mikefarah yq is required on PATH (brew install yq)")
        version = subprocess.run([cls.yq, "--version"], text=True, capture_output=True)
        if version.returncode or "mikefarah/yq" not in version.stdout:
            raise unittest.SkipTest("tests require real mikefarah yq v4, not the Python yq wrapper")

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="gtd tracking ")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.state = self.directory / "state.yaml"
        self.env = {**os.environ, "GTD_STATE_FILE": str(self.state), "GTD_NOW": NOW}

    def cli(self, *arguments, now=None, env=None, ok=True):
        environment = {**self.env, **(env or {})}
        if now is not None:
            environment["GTD_NOW"] = now
        result = subprocess.run(
            ["/bin/bash", str(SCRIPT), *map(str, arguments)],
            env=environment, text=True, capture_output=True, timeout=30,
        )
        if ok:
            self.assertEqual(result.returncode, 0, result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout)
        return result

    def document(self):
        result = subprocess.run(
            [self.yq, "-o=json", ".", str(self.state)],
            text=True, capture_output=True, check=True, timeout=10,
        )
        return json.loads(result.stdout)

    def put_document(self, document):
        result = subprocess.run(
            [self.yq, "-P", "."], input=json.dumps(document),
            text=True, capture_output=True, check=True, timeout=10,
        )
        self.state.write_text(result.stdout, encoding="utf-8")

    def trends(self, now=None):
        return json.loads(self.cli("trends", now=now).stdout)

    def session(self, identity, number=None, mode="process", now=None, **kwargs):
        arguments = ["session", mode]
        if number is not None:
            arguments.append(str(number))
        arguments.extend(["--id", identity])
        for key, value in kwargs.items():
            arguments.extend(["--" + key, json.dumps(value) if key == "contexts" else str(value)])
        return self.cli(*arguments, now=now)

    def test_init_unknowns_and_unrelated_state_preservation(self):
        self.put_document({"preferences": {"processing_style": "thorough"},
                           "custom": {"text": "leave me alone", "values": [1, 2]}})
        self.cli("init")
        document = self.document()
        self.assertEqual(document["schema_version"], 2)
        self.assertEqual(document["preferences"], {"processing_style": "thorough"})
        self.assertEqual(document["custom"], {"text": "leave me alone", "values": [1, 2]})
        self.assertEqual(self.trends()["weekly_processed"], [None] * 4)
        self.assertIsNone(self.trends()["processing_velocity"])
        before = self.state.read_bytes()
        self.cli("init")
        self.assertEqual(self.state.read_bytes(), before)
        self.assertIn("schema_version: 2", self.cli("read").stdout)
        self.assertEqual(self.cli("review-days").stdout.strip(), "never")
        self.assertIn("Last session: never", self.cli("health").stdout)

    def test_begin_does_not_write_and_optional_ids_are_printed(self):
        first = self.cli("begin", "process").stdout.strip()
        second = self.cli("begin", "review").stdout.strip()
        self.assertEqual(str(uuid.UUID(first)), first)
        self.assertNotEqual(first, second)
        self.assertEqual(list(self.directory.iterdir()), [])
        session = json.loads(self.cli("session", "process").stdout)
        review = json.loads(self.cli("review", "4").stdout)
        self.assertEqual(str(uuid.UUID(session["id"])), session["id"])
        self.assertNotEqual(session["id"], review["id"])
        self.assertIsNone(self.document()["last_session"]["items_processed"])

    def test_replay_same_day_later_day_and_payload_conflict(self):
        self.session("stable", 12, deferred=3, contexts={"home": 2, "calls": 1})
        before = self.state.read_bytes()
        for now in (NOW, "2026-11-03T12:00:00-08:00", "2027-02-01T12:00:00-08:00"):
            replay = self.session("stable", 12, now=now, deferred=3,
                                  contexts={"calls": 1, "home": 2})
            self.assertEqual(json.loads(replay.stdout)["status"], "replayed")
            self.assertEqual(self.state.read_bytes(), before)
        failure = self.cli("session", "process", "13", "--id", "stable", ok=False)
        self.assertIn("conflict", failure.stderr)
        self.assertEqual(self.state.read_bytes(), before)
        self.cli("review", "12", "--id", "stable", ok=False)
        self.assertEqual(self.state.read_bytes(), before)
        self.assertEqual(self.trends()["weeks"][-1]["processed"], 12)
        self.assertAlmostEqual(self.trends()["processing_velocity"], 3.6)

    def test_unknown_partial_zero_and_context_completeness(self):
        self.session("unknown")
        initial = self.trends()["weeks"][-1]
        self.assertIsNone(initial["processed"])
        self.assertIsNone(initial["deferred"])
        self.assertIsNone(initial["contexts"])
        self.assertFalse(initial["processed_complete"])
        self.assertIsNone(self.trends()["processing_velocity"])
        self.session("observed", 0, deferred=0, contexts={})
        week = self.trends()["weeks"][-1]
        self.assertEqual(week["processed"], 0)
        self.assertEqual(week["deferred"], 0)
        self.assertEqual(week["contexts"], {})
        self.assertFalse(week["processed_complete"])
        self.assertFalse(week["deferred_complete"])
        self.assertFalse(week["contexts_complete"])
        self.assertEqual(week["processed_known_sessions"], 1)
        self.session("known", 5, deferred=2, contexts={"home": 2})
        week = self.trends()["weeks"][-1]
        self.assertEqual(week["processed"], 5)
        self.assertEqual(week["deferred"], 2)
        self.assertEqual(week["contexts"], {"home": 2})

    def test_actual_net_outcomes_and_deferred_subset(self):
        # Five dispositions minus two undone decisions, including one undone defer.
        self.session("after-undo", 3, deferred=1, contexts={"home": 1})
        week = self.trends()["weeks"][-1]
        self.assertEqual((week["processed"], week["deferred"]), (3, 1))
        self.assertTrue(week["processed_complete"])
        self.assertTrue(week["contexts_complete"])
        before = self.state.read_bytes()
        result = self.cli("session", "process", "1", "--deferred", "2", "--id", "bad", ok=False)
        self.assertIn("deferred cannot exceed processed", result.stderr)
        self.assertEqual(self.state.read_bytes(), before)
        # A coach may defer an existing non-Inbox reminder without processing Inbox.
        self.session("coach", 0, mode="coach", deferred=2)
        self.assertEqual(self.trends()["weeks"][-1]["deferred"], 3)

    def test_coach_sessions_without_observations_do_not_unlock_trends(self):
        self.session("coach-1", mode="coach")
        self.session("coach-2", mode="coach", now="2026-11-09T12:00:00-08:00")
        self.assertFalse(self.trends(now="2026-11-09T12:00:00-08:00")["trends_available"])

    def test_velocity_only_known_process_sessions(self):
        self.session("process-1", 10)
        self.assertAlmostEqual(self.trends()["processing_velocity"], 3)
        self.session("coach", 100, mode="coach")
        self.session("review-mode", 100, mode="review")
        self.session("recovery-mode", 100, mode="recovery")
        self.session("unknown")
        self.cli("review", "300", "--id", "snapshot")
        self.assertAlmostEqual(self.trends()["processing_velocity"], 3)
        # Recovery work that actually processes Inbox uses the explicit process mode.
        self.session("recovered-process", 20)
        self.assertAlmostEqual(self.trends()["processing_velocity"], 8.1)
        self.assertEqual(self.trends()["weeks"][-1]["processed"], 330)

    def test_monday_rollover_uses_override_offset_not_utc(self):
        self.session("sunday", 4, now="2026-11-01T23:45:00-08:00")
        sunday = self.trends(now="2026-11-01T23:50:00-08:00")
        self.assertEqual(sunday["weeks"][-1]["start"], "2026-10-26")
        self.assertFalse(sunday["trends_available"])
        self.session("monday", 6, now="2026-11-02T00:15:00+14:00")
        monday = self.trends(now="2026-11-02T00:20:00+14:00")
        self.assertEqual(monday["weekly_processed"], [None, None, 4, 6])
        self.assertTrue(monday["trends_available"])
        self.assertEqual(monday["dated_weeks"], 2)
        self.assertEqual(self.document()["tracking"]["sessions"]["monday"]["date"], "2026-11-02")

    def test_retention_four_weeks_and_permanent_replay_protection(self):
        dates = ["2026-09-28", "2026-10-05", "2026-10-12", "2026-10-19", "2026-10-26", "2026-11-02"]
        for index, day in enumerate(dates):
            now = day + "T12:00:00-08:00"
            self.session("s" + str(index), 10, now=now)
            self.cli("review", "8", "--id", "r" + str(index), now=now)
        tracking = self.document()["tracking"]
        self.assertEqual(set(tracking["sessions"]), {"s2", "s3", "s4", "s5"})
        self.assertEqual(set(tracking["completion_snapshots"]), {"r2", "r3", "r4", "r5"})
        self.assertEqual(len(tracking["identities"]), 12)
        self.assertEqual(self.trends()["weekly_processed"], [10] * 4)
        self.assertEqual([week["start"] for week in tracking["weeks"]], dates[-4:])
        self.assertAlmostEqual(tracking["processing_velocity"], 10 * (1 - 0.7 ** 6))
        before = self.state.read_bytes()
        self.session("s0", 10)
        self.cli("review", "8", "--id", "r0")
        self.assertEqual(self.state.read_bytes(), before)
        self.cli("session", "process", "11", "--id", "s0", ok=False)
        self.assertEqual(self.state.read_bytes(), before)
        empty = self.trends(now="2026-12-07T12:00:00-08:00")
        self.assertEqual(empty["weekly_processed"], [None] * 4)
        self.assertEqual(self.document()["tracking"]["sessions"], {})
        self.assertEqual(len(self.document()["tracking"]["identities"]), 12)
        self.assertAlmostEqual(empty["processing_velocity"], tracking["processing_velocity"])

    def test_legacy_migration_keeps_undated_history_and_seeds_velocity(self):
        legacy = {
            "trends": {"weekly_completed": [99, 88], "weekly_processed": [200], "weekly_deferred": [12]},
            "patterns": {"peak_days": ["Monday"], "defer_days": ["Friday"], "avg_process_velocity": 10},
            "contexts": {"home": 900},
            "preferences": {"processing_style": "thorough"},
            "extra": {"nested": "preserved"},
        }
        self.put_document(legacy)
        self.cli("init")
        document = self.document()
        for key in ("trends", "patterns", "contexts"):
            self.assertEqual(document["legacy_history"][key], legacy[key])
            self.assertNotIn(key, document)
        self.assertEqual(document["extra"], legacy["extra"])
        self.assertEqual(self.trends()["weekly_processed"], [None] * 4)
        self.assertEqual(self.trends()["weekly_completed"], [None] * 4)
        self.assertEqual(self.trends()["processing_velocity"], 10)
        self.assertFalse(self.trends()["trends_available"])
        self.session("new", 20)
        self.assertAlmostEqual(self.trends()["processing_velocity"], 13)
        self.assertEqual(self.trends()["weeks"][-1]["contexts"], None)

    def test_actual_template_migrates_without_dating_zeros(self):
        shutil.copyfile(TEMPLATE, self.state)
        self.cli("init")
        self.assertEqual(self.trends()["weekly_processed"], [None] * 4)
        self.assertEqual(self.document()["tracking"]["sessions"], {})
        self.assertEqual(self.document()["legacy_history"]["contexts"]["home"], 0)

    def test_deprecated_setters_write_only_legacy_history(self):
        self.session("current", 10, contexts={"home": 2})
        before = self.document()
        for arguments in (("context", "home"), ("weekly", "50", "60", "2"),
                          ("velocity", "999"), ("pattern", "peak", "Monday"),
                          ("pattern", "defer", "Friday")):
            result = self.cli(*arguments, now="2026-11-09T12:00:00-08:00")
            self.assertIn("deprecated", result.stderr)
        after = self.document()
        self.assertEqual(after["tracking"], before["tracking"])
        self.assertEqual(after["last_session"], before["last_session"])
        self.assertEqual(after["legacy_history"]["trends"]["weekly_completed"], [50])
        self.assertEqual(after["legacy_history"]["contexts"], {"home": 1})
        self.assertAlmostEqual(self.trends()["processing_velocity"], 3)
        self.assertEqual(self.trends()["weekly_processed"], [None, None, None, 10])

    def test_review_snapshot_replay_quoting_and_no_summation(self):
        focus = 'Next "focus": it\'s okay\nsecond line\t| .bad = true\n$(touch SHOULD_NOT_EXIST) `echo nope`'
        identity = 'review "one" | .bad = true'
        self.cli("review", "8", focus, "--id", identity)
        before = self.state.read_bytes()
        result = self.cli("review", "8", focus, "--id", identity, now="2026-11-03T10:00:00-08:00")
        self.assertEqual(json.loads(result.stdout)["status"], "replayed")
        self.assertEqual(self.state.read_bytes(), before)
        self.cli("review", "9", focus, "--id", identity, ok=False)
        self.assertEqual(self.state.read_bytes(), before)
        self.cli("review", "9", "--id", "second", now="2026-11-03T10:00:00-08:00")
        document = self.document()
        snapshots = document["tracking"]["completion_snapshots"]
        self.assertEqual(len(snapshots), 2)
        self.assertEqual(snapshots[identity]["focus"], focus)
        summary = self.trends(now="2026-11-03T12:00:00-08:00")
        self.assertEqual([event["completed_count"] for event in summary["completion_snapshots"]], [8, 9])
        self.assertEqual(summary["weekly_completed"], [None] * 4)
        self.assertEqual(summary["weekly_processed"], [None] * 4)
        self.assertNotIn("bad", document)
        self.assertFalse((ROOT / "SHOULD_NOT_EXIST").exists())

    def test_review_days_uses_local_calendar_dates(self):
        self.cli("review", "0", "--id", "r", now="2026-11-01T23:55:00-08:00")
        self.assertEqual(self.cli("review-days", now="2026-11-02T00:01:00-08:00").stdout.strip(), "1")
        self.assertEqual(self.cli("review-days", now="2026-11-03T00:01:00-08:00").stdout.strip(), "2")

    def test_future_events_ignored_in_totals_velocity_and_review_days(self):
        self.session("present", 10)
        self.session("future", 1000, now="2026-11-04T12:00:00-08:00", contexts={"home": 100})
        self.cli("review", "500", "--id", "future-review", now="2026-11-04T12:00:00-08:00")
        summary = self.trends()
        self.assertEqual(summary["weekly_processed"], [None, None, None, 10])
        self.assertEqual(summary["completion_snapshots"], [])
        self.assertAlmostEqual(summary["processing_velocity"], 3)
        self.assertEqual(self.cli("review-days").stdout.strip(), "never")
        self.assertIn("Last session: 2026-11-02", self.cli("health").stdout)

    def test_invalid_clock_arguments_and_malformed_state_do_not_write(self):
        self.cli("init")
        before = self.state.read_bytes()
        invalid_arguments = [
            ("session", "process", "-1"), ("session", "process", "1.5"),
            ("session", "process", "--contexts", '{"home":true}'),
            ("session", "process", "--contexts", '{"home":-1}'),
            ("session", "process", "--contexts", '[]'),
            ("session", "process", "--id", " "), ("session", "", "0"),
            ("review", "-1"),
        ]
        for arguments in invalid_arguments:
            with self.subTest(arguments=arguments):
                self.cli(*arguments, ok=False)
                self.assertEqual(self.state.read_bytes(), before)
        for now in ("2026-11-02T12:00:00", "not a datetime", "2026-13-01T10:00:00Z"):
            self.assertIn("GTD_NOW", self.cli("init", now=now, ok=False).stderr)
            self.assertEqual(self.state.read_bytes(), before)
        malformed_values = [[], {"schema_version": 999},
                            {"schema_version": 2, "tracking": {"sessions": []}}]
        for malformed in malformed_values:
            self.put_document(malformed)
            contents = self.state.read_bytes()
            self.cli("session", "process", "1", "--id", "bad", ok=False)
            self.assertEqual(self.state.read_bytes(), contents)
        self.state.write_text("broken: [unclosed\n", encoding="utf-8")
        contents = self.state.read_bytes()
        self.cli("init", ok=False)
        self.assertEqual(self.state.read_bytes(), contents)

    def test_tampered_dated_event_is_rejected(self):
        self.session("valid", 4)
        document = self.document()
        document["tracking"]["sessions"]["valid"]["processed"] = 100
        self.put_document(document)
        contents = self.state.read_bytes()
        result = self.cli("trends", ok=False)
        self.assertIn("identity", result.stderr)
        self.assertEqual(self.state.read_bytes(), contents)

    def test_yq_write_failure_after_read_is_atomic(self):
        self.session("first", 10)
        before = self.state.read_bytes()
        tools = self.directory / "failing-tools"
        tools.mkdir()
        wrapper = tools / "yq"
        marker = self.directory / "read-happened"
        wrapper.write_text(
            '#!/bin/sh\n'
            'if [ "$1" = "-o=json" ]; then\n'
            '  : > "$GTD_READ_MARKER"\n'
            '  exec "$GTD_REAL_YQ" "$@"\n'
            'fi\n'
            'echo "controlled YAML serialization failure" >&2\n'
            'exit 41\n', encoding="utf-8",
        )
        wrapper.chmod(0o755)
        result = self.cli("session", "process", "20", "--id", "failed", env={
            "PATH": str(tools) + os.pathsep + self.env["PATH"],
            "GTD_REAL_YQ": self.yq, "GTD_READ_MARKER": str(marker),
        }, ok=False)
        self.assertTrue(marker.exists())
        self.assertIn("controlled YAML serialization failure", result.stderr)
        self.assertEqual(self.state.read_bytes(), before)
        self.assertEqual(list(self.directory.glob(".state.yaml.*")), [])
        self.session("failed", 20)
        self.assertEqual(self.trends()["weeks"][-1]["processed"], 30)
        self.assertAlmostEqual(self.trends()["processing_velocity"], 8.1)

    def test_missing_yq_has_clear_error(self):
        # Keep the interpreter available while removing yq from PATH.
        tools = self.directory / "python-only"
        tools.mkdir()
        python = shutil.which("python3")
        (tools / "python3").symlink_to(python)
        for command in ("dirname",):
            (tools / command).symlink_to(shutil.which(command))
        result = self.cli("init", env={"PATH": str(tools)}, ok=False)
        self.assertIn("mikefarah yq is required", result.stderr)
        self.assertFalse(self.state.exists())

    def test_concurrent_writers_and_duplicate_retry(self):
        def persist(index):
            identity = "parallel-" + str(index % 4)
            return self.cli("session", "process", "2", "--id", identity)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(persist, range(8)))
        statuses = [json.loads(result.stdout)["status"] for result in results]
        self.assertEqual(statuses.count("recorded"), 4)
        self.assertEqual(statuses.count("replayed"), 4)
        self.assertEqual(len(self.document()["tracking"]["sessions"]), 4)
        self.assertEqual(self.trends()["weeks"][-1]["processed"], 8)
        self.assertAlmostEqual(self.trends()["processing_velocity"], 2 * (1 - 0.7 ** 4))

    def test_default_path_is_relative_to_script(self):
        isolated = self.directory / "isolated" / "scripts"
        isolated.mkdir(parents=True)
        for name in ("state.sh", "gtd_tracking.py"):
            shutil.copyfile(SCRIPT.parent / name, isolated / name)
        environment = dict(self.env)
        del environment["GTD_STATE_FILE"]
        result = subprocess.run(["/bin/bash", str(isolated / "state.sh"), "init"],
                                env=environment, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((isolated.parent / "state.yaml").exists())
        self.assertFalse(self.state.exists())


if __name__ == "__main__":
    unittest.main()
