"""Availability calculations through the Calendar module interface."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
import datetime as dt
import json
import os
import subprocess

SCRIPTS = Path(__file__).resolve().parents[1] / '.claude/skills/gtd/scripts'
spec = importlib.util.spec_from_file_location('gtd_calendar', SCRIPTS / 'gtd_calendar.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class FakeCalendar:
    def __init__(self, events):
        self.events_list = events

    def events(self, calendar, start, end, now):
        return [e for e in self.events_list if e['start'] < end.timestamp() and e['end'] > start.timestamp()]


def event(day, start, end, allday=False):
    return {'start': dt.datetime.combine(day, start).timestamp(),
            'end': dt.datetime.combine(day, end).timestamp(), 'allday': allday}


class AvailabilityTests(unittest.TestCase):
    def at(self, hour, minute=0):
        return dt.datetime(2026, 11, 2, hour, minute).astimezone()

    def test_before_workday_uses_whole_window(self):
        gaps = m.CalendarAvailability(FakeCalendar([]), self.at(7)).gaps()
        self.assertEqual(sum(b - a for a, b in gaps), 9 * 3600)

    def test_after_workday_has_nothing(self):
        self.assertEqual(m.CalendarAvailability(FakeCalendar([]), self.at(19)).gaps(), [])

    def test_remaining_workday_starts_at_now(self):
        gaps = m.CalendarAvailability(FakeCalendar([]), self.at(14)).gaps()
        self.assertEqual(sum(b - a for a, b in gaps), 4 * 3600)

    def test_overlaps_merge_nested_and_adjacent(self):
        day = self.at(12).date()
        events = [event(day, dt.time(10), dt.time(12)), event(day, dt.time(11), dt.time(13)),
                  event(day, dt.time(11, 30), dt.time(11, 45)), event(day, dt.time(13), dt.time(14))]
        gaps = m.CalendarAvailability(FakeCalendar(events), self.at(9)).gaps()
        self.assertEqual(gaps, [(self.at(9).timestamp(), event(day, dt.time(10), dt.time(10))['start']),
                                (event(day, dt.time(14), dt.time(14))['start'], self.at(18).timestamp())])

    def test_event_spanning_window_and_all_day(self):
        day = self.at(12).date()
        events = [event(day, dt.time(8), dt.time(10)), event(day, dt.time(17), dt.time(20)),
                  event(day, dt.time(0), dt.time(0), allday=True)]
        gaps = m.CalendarAvailability(FakeCalendar(events), self.at(9)).gaps()
        self.assertEqual([(b - a) / 60 for a, b in gaps], [420])

    def test_free_and_gaps_share_coverage(self):
        day = self.at(12).date()
        events = [event(day, dt.time(9, 15), dt.time(9, 45)), event(day, dt.time(12), dt.time(13))]
        module = m.CalendarAvailability(FakeCalendar(events), self.at(8))
        all_gaps = module.gaps()
        self.assertEqual(sum(b - a for a, b in all_gaps), 9 * 3600 - 30 * 60 - 3600)
        self.assertEqual([g for g in all_gaps if g[1] - g[0] >= 30 * 60],
                         [g for g in all_gaps if g[1] - g[0] >= 30 * 60])

    def test_command_adapter_and_output(self):
        day = self.at(12).date()
        with tempfile.TemporaryDirectory() as temp:
            adapter = Path(temp) / 'adapter'
            adapter.write_text('#!/usr/bin/env python3\nimport json,sys\nr=json.load(sys.stdin)\nnow=__import__("datetime").datetime.fromisoformat(r["now"])\nmid=now.replace(hour=12,minute=0,second=0,microsecond=0).timestamp()\nprint(json.dumps([{"start":mid,"end":mid+3600}]))\n')
            adapter.chmod(0o755)
            env = dict(os.environ, GTD_CALENDAR_ADAPTER=str(adapter), GTD_NOW=self.at(9).isoformat())
            result = subprocess.run([str(SCRIPTS / 'calendar.sh'), 'free'], env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.strip(), '8h 0m available for the rest of today (9AM-6PM)')

    def test_minimum_gap_filter(self):
        day = self.at(12).date()
        events = [event(day, dt.time(9), dt.time(10)), event(day, dt.time(10, 15), dt.time(18))]
        gaps = m.CalendarAvailability(FakeCalendar(events), self.at(8)).gaps()
        self.assertEqual([(b - a) / 60 for a, b in gaps], [15])


if __name__ == '__main__':
    unittest.main()
