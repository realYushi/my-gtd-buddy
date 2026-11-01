"""Behavior tests for V2 Available Time."""
import datetime as dt
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "gtd" / "scripts" / "gtd_availability.py"
spec = importlib.util.spec_from_file_location("gtd_availability", SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def at(text):
    return dt.datetime.fromisoformat(text)


class AvailabilityTests(unittest.TestCase):
    def assess(self, now, busy, covering, workday="09:00-18:00", timezone="Pacific/Auckland"):
        return m.AvailableTime(workday=workday, timezone=timezone).at(
            now=at(now),
            busy=m.CompleteBusy(
                intervals=[(at(start), at(end)) for start, end in busy],
                covering=(at(covering[0]), at(covering[1])),
            ),
        )

    def test_remaining_workday_without_events(self):
        result = self.assess(
            "2026-11-02T14:00:00+13:00", [],
            ("2026-11-02T14:00:00+13:00", "2026-11-02T18:00:00+13:00"),
        )
        self.assertEqual(result, m.Known(dt.timedelta(hours=4)))

    def test_before_workday_uses_the_whole_window(self):
        result = self.assess(
            "2026-11-02T08:00:00+13:00", [],
            ("2026-11-02T08:00:00+13:00", "2026-11-02T18:00:00+13:00"),
        )
        self.assertEqual(result, m.Known(dt.timedelta(hours=9)))

    def test_after_workday_is_zero(self):
        result = self.assess(
            "2026-11-02T20:00:00+13:00", [],
            ("2026-11-02T20:00:00+13:00", "2026-11-02T21:00:00+13:00"),
        )
        self.assertEqual(result, m.Known(dt.timedelta(0)))

    def test_overlapping_nested_and_adjacent_events_count_once(self):
        result = self.assess(
            "2026-11-02T10:00:00+13:00",
            [
                ("2026-11-02T09:00:00+13:00", "2026-11-02T11:30:00+13:00"),
                ("2026-11-02T10:30:00+13:00", "2026-11-02T12:00:00+13:00"),
                ("2026-11-02T12:00:00+13:00", "2026-11-02T13:00:00+13:00"),
            ],
            ("2026-11-02T10:00:00+13:00", "2026-11-02T18:00:00+13:00"),
        )
        self.assertEqual(result, m.Known(dt.timedelta(hours=5)))

    def test_incomplete_calendar_coverage_is_unknown(self):
        result = self.assess(
            "2026-11-02T14:00:00+13:00", [],
            ("2026-11-02T14:00:00+13:00", "2026-11-02T16:00:00+13:00"),
        )
        self.assertEqual(result, m.Unknown("incomplete_coverage"))

    def test_malformed_interval_outside_the_window_is_unknown(self):
        result = self.assess(
            "2026-11-02T14:00:00+13:00",
            [("2026-11-02T08:00:00+13:00", "2026-11-02T08:00:00+13:00")],
            ("2026-11-02T14:00:00+13:00", "2026-11-02T18:00:00+13:00"),
        )
        self.assertEqual(result, m.Unknown("invalid_interval", 0))

    def test_unavailable_observation_stays_unknown_after_workday(self):
        result = m.AvailableTime("09:00-18:00", "Pacific/Auckland").at(
            now=at("2026-11-02T20:00:00+13:00"),
            busy=m.Unavailable("calendar read failed"),
        )
        self.assertEqual(result, m.Unknown("unavailable"))

    def test_today_uses_the_profile_timezone(self):
        result = m.AvailableTime("09:00-18:00", "Pacific/Auckland").at(
            now=at("2026-11-01T20:00:00+00:00"),
            busy=m.CompleteBusy(
                intervals=[],
                covering=(at("2026-11-01T20:00:00+00:00"), at("2026-11-02T05:00:00+00:00")),
            ),
        )
        self.assertEqual(result, m.Known(dt.timedelta(hours=9)))

    def test_dst_fall_back_uses_elapsed_time(self):
        result = m.AvailableTime("01:00-03:00", "America/New_York").at(
            now=at("2026-11-01T00:30:00-04:00"),
            busy=m.CompleteBusy(
                intervals=[],
                covering=(at("2026-11-01T00:30:00-04:00"), at("2026-11-01T03:00:00-05:00")),
            ),
        )
        self.assertEqual(result, m.Known(dt.timedelta(hours=3)))

    def test_nonexistent_workday_endpoint_is_unknown(self):
        result = m.AvailableTime("02:00-04:00", "America/New_York").at(
            now=at("2026-03-08T00:00:00-05:00"),
            busy=m.CompleteBusy(
                intervals=[],
                covering=(at("2026-03-08T00:00:00-05:00"), at("2026-03-08T04:00:00-04:00")),
            ),
        )
        self.assertEqual(result, m.Unknown("unresolved_local_time"))

    def test_cli_reports_known_duration(self):
        request = {
            "now": "2026-11-02T14:00:00+13:00",
            "workday": "09:00-18:00",
            "timezone": "Pacific/Auckland",
            "busy": [],
            "covering": ["2026-11-02T14:00:00+13:00", "2026-11-02T18:00:00+13:00"],
        }
        result = subprocess.run(
            [sys.executable, str(SCRIPT)], input=json.dumps(request),
            text=True, capture_output=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {
            "status": "known", "seconds": 14400,
        })


if __name__ == "__main__":
    unittest.main()
