#!/usr/bin/env python3
"""Calculate Available Time from complete normalized calendar evidence."""
import argparse
from dataclasses import dataclass
import datetime as dt
import json
import re
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


WORKDAY = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)-([01]\d|2[0-3]):([0-5]\d)$")


@dataclass(frozen=True)
class CompleteBusy:
    intervals: tuple
    covering: tuple

    def __init__(self, intervals, covering):
        object.__setattr__(self, "intervals", tuple(tuple(item) for item in intervals))
        object.__setattr__(self, "covering", tuple(covering))


@dataclass(frozen=True)
class Unavailable:
    reason: str


@dataclass(frozen=True)
class Known:
    total: dt.timedelta


@dataclass(frozen=True)
class Unknown:
    reason: str
    interval_index: int = None


class _LocalTimeError(Exception):
    pass


def aware(value):
    return (
        isinstance(value, dt.datetime)
        and value.tzinfo is not None
        and value.utcoffset() is not None
    )


def local_instant(day, hour, minute, zone, endpoint):
    naive = dt.datetime.combine(day, dt.time(hour, minute))
    candidates = [naive.replace(tzinfo=zone, fold=fold) for fold in (0, 1)]
    valid = [
        candidate for candidate in candidates
        if candidate.astimezone(dt.timezone.utc).astimezone(zone).replace(tzinfo=None) == naive
    ]
    if not valid:
        raise _LocalTimeError("Workday endpoint does not exist in the profile timezone")
    return min(valid) if endpoint == "start" else max(valid)


def elapsed(start, end):
    return dt.timedelta(seconds=end.timestamp() - start.timestamp())


class AvailableTime:
    def __init__(self, workday, timezone):
        self.workday = workday
        self.timezone = timezone

    def at(self, *, now, busy):
        if isinstance(busy, Unavailable) or not isinstance(busy, CompleteBusy):
            return Unknown("unavailable")
        if not aware(now):
            return Unknown("invalid_now")
        match = WORKDAY.fullmatch(self.workday) if isinstance(self.workday, str) else None
        if not match:
            return Unknown("invalid_workday")
        start_minute = int(match.group(1)) * 60 + int(match.group(2))
        end_minute = int(match.group(3)) * 60 + int(match.group(4))
        if start_minute >= end_minute:
            return Unknown("invalid_workday")
        try:
            zone = ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError):
            return Unknown("invalid_timezone")
        try:
            day = now.astimezone(zone).date()
            start = local_instant(
                day, start_minute // 60, start_minute % 60, zone, "start"
            )
            end = local_instant(
                day, end_minute // 60, end_minute % 60, zone, "end"
            )
        except _LocalTimeError:
            return Unknown("unresolved_local_time")

        intervals = []
        for index, interval in enumerate(busy.intervals):
            if not isinstance(interval, (tuple, list)) or len(interval) != 2:
                return Unknown("invalid_interval", index)
            left, right = interval
            if not aware(left) or not aware(right) or left >= right:
                return Unknown("invalid_interval", index)
            intervals.append((left, right))

        covering = busy.covering
        if not isinstance(covering, (tuple, list)) or len(covering) != 2:
            return Unknown("invalid_coverage")
        cover_start, cover_end = covering
        if not aware(cover_start) or not aware(cover_end) or cover_start >= cover_end:
            return Unknown("invalid_coverage")

        window_start = max(now, start)
        window_end = end
        if window_start >= window_end:
            return Known(dt.timedelta(0))
        if cover_start > window_start or cover_end < window_end:
            return Unknown("incomplete_coverage")

        clipped = []
        for left, right in intervals:
            left = max(left, window_start)
            right = min(right, window_end)
            if left < right:
                clipped.append((left, right))
        clipped.sort()
        occupied = dt.timedelta(0)
        cursor = None
        for left, right in clipped:
            if cursor is None or left > cursor:
                occupied += elapsed(left, right)
                cursor = right
            elif right > cursor:
                occupied += elapsed(cursor, right)
                cursor = right
        return Known(elapsed(window_start, window_end) - occupied)


def assess(request):
    try:
        now = dt.datetime.fromisoformat(request["now"])
    except (KeyError, TypeError, ValueError):
        return Unknown("invalid_now")
    busy_value = request.get("busy")
    if busy_value is None:
        busy = Unavailable(request.get("reason", "calendar unavailable"))
    else:
        try:
            busy = CompleteBusy(
                intervals=[(dt.datetime.fromisoformat(a), dt.datetime.fromisoformat(b))
                           for a, b in busy_value],
                covering=(dt.datetime.fromisoformat(request["covering"][0]),
                          dt.datetime.fromisoformat(request["covering"][1])),
            )
        except (KeyError, TypeError, ValueError):
            return Unknown("invalid_interval")
    return AvailableTime(request.get("workday", ""), request.get("timezone", "")).at(
        now=now, busy=busy
    )


def result_json(result):
    if isinstance(result, Known):
        return {"status": "known", "seconds": int(result.total.total_seconds())}
    payload = {"status": "unknown", "reason": result.reason}
    if result.interval_index is not None:
        payload["interval_index"] = result.interval_index
    return payload


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", help="JSON request path; stdin when omitted")
    args = parser.parse_args(argv)
    try:
        if args.path:
            request = json.loads(open(args.path, encoding="utf-8").read())
        else:
            request = json.load(sys.stdin)
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "unknown", "reason": "invalid_request", "detail": str(exc)}))
        return 2
    print(json.dumps(result_json(assess(request)), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
