#!/usr/bin/env python3
"""Calendar availability shared by the free and gaps commands."""
import argparse
import datetime as dt
import json
import math
import os
import subprocess
import sys


EVENT_SCRIPT = '''on run argv
    set theCal to item 1 of argv
    set startEpoch to (item 2 of argv) as real
    set endEpoch to (item 3 of argv) as real
    set nowEpoch to (item 4 of argv) as real
    set capturedNow to current date
    set winStart to capturedNow + (startEpoch - nowEpoch)
    set winEnd to capturedNow + (endEpoch - nowEpoch)
    set output to ""
    tell application "Calendar"
        set cals to calendars
        if theCal is not "" then set cals to {calendar theCal}
        repeat with cal in cals
            set selectedEvents to (every event of cal whose start date < winEnd and end date > winStart and allday event is false)
            repeat with e in selectedEvents
                set startOffset to (start date of e) - capturedNow
                set endOffset to (end date of e) - capturedNow
                set output to output & (startOffset as text) & tab & (endOffset as text) & linefeed
            end repeat
        end repeat
    end tell
    return output
end run
'''


class AppleScriptAdapter:
    def events(self, calendar, start, end, now):
        result = subprocess.run(['osascript', '-', calendar, str(start.timestamp()),
                                 str(end.timestamp()), str(now.timestamp())],
                                input=EVENT_SCRIPT, text=True, capture_output=True)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or 'Calendar did not respond')
        events = []
        for row in result.stdout.splitlines():
            if row.strip():
                a, b = row.split('\t')
                events.append({'start': now.timestamp() + float(a),
                               'end': now.timestamp() + float(b)})
        return events


class CommandAdapter:
    def __init__(self, executable):
        self.executable = executable

    def events(self, calendar, start, end, now):
        request = {'calendar': calendar, 'start': start.isoformat(),
                   'end': end.isoformat(), 'now': now.isoformat()}
        result = subprocess.run([self.executable], input=json.dumps(request),
                                text=True, capture_output=True)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or 'Calendar adapter failed')
        return json.loads(result.stdout)


def clock():
    value = os.environ.get('GTD_NOW')
    now = dt.datetime.fromisoformat(value) if value else dt.datetime.now().astimezone()
    if now.tzinfo is None:
        raise ValueError('GTD_NOW must include a timezone offset')
    return now


def timestamp(value):
    if isinstance(value, (int, float)):
        return float(value)
    parsed = dt.datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError('Calendar event times must include a timezone offset')
    return parsed.timestamp()


class CalendarAvailability:
    def __init__(self, adapter, now):
        self.adapter, self.now = adapter, now

    def gaps(self, calendar=''):
        start = max(self.now, self.now.replace(hour=9, minute=0, second=0, microsecond=0))
        end = self.now.replace(hour=18, minute=0, second=0, microsecond=0)
        if start >= end:
            return []
        left, right = start.timestamp(), end.timestamp()
        intervals = []
        for event in self.adapter.events(calendar, start, end, self.now):
            if event.get('allday', False):
                continue
            if calendar and event.get('calendar', calendar) != calendar:
                continue
            a, b = max(left, timestamp(event['start'])), min(right, timestamp(event['end']))
            if a < b:
                intervals.append((a, b))
        cursor = left
        gaps = []
        for a, b in sorted(intervals):
            if a > cursor:
                gaps.append((cursor, a))
            cursor = max(cursor, b)
        if cursor < right:
            gaps.append((cursor, right))
        return gaps


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['free', 'gaps'])
    parser.add_argument('values', nargs='*')
    args = parser.parse_args(argv)
    try:
        now = clock()
        minutes = 0
        if args.command == 'gaps':
            minutes = int(args.values[0]) if args.values else 30
            if minutes <= 0:
                raise ValueError('Minimum gap must be positive')
            calendar = args.values[1] if len(args.values) > 1 else ''
        else:
            calendar = args.values[0] if args.values else ''
        adapter = CommandAdapter(os.environ['GTD_CALENDAR_ADAPTER']) if os.environ.get('GTD_CALENDAR_ADAPTER') else AppleScriptAdapter()
        gaps = CalendarAvailability(adapter, now).gaps(calendar)
        if args.command == 'free':
            total = math.floor(sum(b - a for a, b in gaps) / 60)
            print(f'{total // 60}h {total % 60}m available for the rest of today (9AM-6PM)')
        else:
            for a, b in gaps:
                if b - a >= minutes * 60:
                    start = dt.datetime.fromtimestamp(a, now.tzinfo).isoformat(timespec='seconds')
                    end = dt.datetime.fromtimestamp(b, now.tzinfo).isoformat(timespec='seconds')
                    print(f'{start}\t{end}\t{math.floor((b - a) / 60)} min')
        return 0
    except (ValueError, RuntimeError, OSError, KeyError) as exc:
        print('Calendar availability failed: ' + str(exc), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
