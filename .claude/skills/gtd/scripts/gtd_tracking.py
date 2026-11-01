#!/usr/bin/env python3
"""Dated GTD outcomes. Use begin and persist its stable ID when closing a session.

Counts are caller-supplied net outcomes, after subtracting same-session undo.
Omitted session counts remain unknown. Review counts are rolling seven-day
observations, never additive weekly completions. Only process sessions affect
velocity. Legacy setters are retained solely for compatibility.
"""

import argparse
import copy
from datetime import date, datetime, timedelta
import fcntl
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid


SCHEMA_VERSION = 2


class TrackingError(Exception):
    pass


def count(value):
    try:
        result = int(value)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError("count must be a nonnegative integer")
    if str(result) != str(value) or result < 0:
        raise argparse.ArgumentTypeError("count must be a nonnegative integer")
    return result


def valid_count(value):
    return type(value) is int and value >= 0


def contexts_arg(value):
    try:
        result = json.loads(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("contexts must be a JSON object") from exc
    if not valid_contexts(result):
        raise argparse.ArgumentTypeError("contexts must map nonempty names to nonnegative integers")
    return result


def valid_contexts(value):
    return isinstance(value, dict) and all(
        isinstance(key, str) and key.strip() and valid_count(number)
        for key, number in value.items()
    )


def local_now():
    override = os.environ.get("GTD_NOW")
    if override is None:
        return datetime.now().astimezone()
    try:
        result = datetime.fromisoformat(override.replace("Z", "+00:00"))
        if result.tzinfo is None or result.utcoffset() is None:
            raise ValueError("timezone offset required")
        return result  # The supplied offset defines the local tracking date.
    except ValueError as exc:
        raise TrackingError("GTD_NOW must be an ISO datetime with a timezone offset") from exc


def parse_date(value):
    try:
        result = date.fromisoformat(value)
        if result.isoformat() != value:
            raise ValueError("noncanonical date")
        return result
    except (TypeError, ValueError) as exc:
        raise TrackingError("malformed state: expected an ISO calendar date") from exc


def monday(day):
    return day - timedelta(days=day.weekday())


def fingerprint(kind, payload):
    encoded = json.dumps([kind, payload], sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def yq_run(binary, arguments, input_text=None):
    try:
        result = subprocess.run(
            [binary, *arguments], input=input_text, text=True, capture_output=True, check=False
        )
    except OSError as exc:
        raise TrackingError(f"cannot execute yq: {exc}") from exc
    if result.returncode:
        raise TrackingError(f"yq failed: {result.stderr.strip() or 'exit ' + str(result.returncode)}")
    return result.stdout


def load_state(path, binary):
    if not path.exists():
        return {
            "last_session": {"date": None, "mode": None, "items_processed": None},
            "last_review": {"date": None, "completed_count": None, "focus": None},
            "preferences": {"processing_style": "quick"},
        }
    try:
        state = json.loads(yq_run(binary, ["-o=json", ".", str(path)]))
    except ValueError as exc:
        raise TrackingError("malformed state: yq did not return one JSON object") from exc
    if not isinstance(state, dict):
        raise TrackingError("malformed state: root must be a mapping")
    return state


def migrate(state):
    version = state.get("schema_version")
    if version == SCHEMA_VERSION and type(version) is int:
        return
    if version is not None and (type(version) is not int or version != 1):
        raise TrackingError(f"unsupported state schema_version: {version!r}")
    if "tracking" in state:
        raise TrackingError("malformed state: unversioned tracking data")
    legacy = state.setdefault("legacy_history", {})
    if not isinstance(legacy, dict):
        raise TrackingError("malformed state: legacy_history must be a mapping")
    patterns = state.get("patterns", {})
    seed = patterns.get("avg_process_velocity") if isinstance(patterns, dict) else None
    if seed is not None and not valid_velocity(seed):
        raise TrackingError("malformed state: invalid legacy velocity")
    for key in ("trends", "patterns", "contexts"):
        if key in state:
            value = state.pop(key)
            if key in legacy and legacy[key] != value:
                # Preserve both earlier archival data and newly encountered legacy data.
                archive = legacy.setdefault("migration_history", [])
                if not isinstance(archive, list):
                    raise TrackingError("malformed state: migration_history must be a list")
                archive.append({key: value})
            else:
                legacy[key] = value
    state["schema_version"] = SCHEMA_VERSION
    state["tracking"] = {
        "sessions": {},
        "completion_snapshots": {},
        "identities": {},
        "velocity_seed": seed,
        "next_sequence": 1,
    }


def valid_velocity(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def validate(state):
    tracking = state.get("tracking")
    if not isinstance(tracking, dict):
        raise TrackingError("malformed state: tracking must be a mapping")
    for key in ("sessions", "completion_snapshots", "identities"):
        if not isinstance(tracking.get(key), dict):
            raise TrackingError(f"malformed state: tracking.{key} must be a mapping")
    if not valid_count(tracking.get("next_sequence")) or tracking["next_sequence"] < 1:
        raise TrackingError("malformed state: invalid next_sequence")
    seed = tracking.get("velocity_seed")
    if seed is not None and not valid_velocity(seed):
        raise TrackingError("malformed state: invalid velocity seed")
    if "weeks" in tracking and not isinstance(tracking["weeks"], list):
        raise TrackingError("malformed state: weeks must be a list")
    velocity = tracking.get("processing_velocity")
    if velocity is not None and not valid_velocity(velocity):
        raise TrackingError("malformed state: invalid processing velocity")
    if not isinstance(state.get("legacy_history", {}), dict):
        raise TrackingError("malformed state: legacy_history must be a mapping")
    for key in ("last_session", "last_review"):
        entry = state.get(key)
        if entry is not None:
            if not isinstance(entry, dict):
                raise TrackingError(f"malformed state: {key} must be a mapping")
            if entry.get("date") is not None:
                parse_date(entry["date"])
    for identity, record in tracking["identities"].items():
        if not isinstance(identity, str) or not identity.strip() or not isinstance(record, dict):
            raise TrackingError("malformed state: invalid identity")
        digest = record.get("fingerprint")
        if (record.get("kind") not in ("session", "review") or not isinstance(digest, str)
                or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest)):
            raise TrackingError("malformed state: invalid identity fingerprint")
    sequences = set()
    for collection, kind in (("sessions", "session"), ("completion_snapshots", "review")):
        for identity, event in tracking[collection].items():
            if not isinstance(event, dict):
                raise TrackingError("malformed state: event must be a mapping")
            parse_date(event.get("date"))
            sequence = event.get("sequence")
            if (not valid_count(sequence) or sequence < 1 or sequence in sequences
                    or sequence >= tracking["next_sequence"]):
                raise TrackingError("malformed state: invalid event sequence")
            sequences.add(sequence)
            if kind == "session":
                payload = {key: event.get(key) for key in ("mode", "processed", "deferred", "contexts")}
                if not isinstance(payload["mode"], str) or not payload["mode"].strip():
                    raise TrackingError("malformed state: invalid session mode")
                for key in ("processed", "deferred"):
                    if payload[key] is not None and not valid_count(payload[key]):
                        raise TrackingError("malformed state: invalid session count")
                if payload["contexts"] is not None and not valid_contexts(payload["contexts"]):
                    raise TrackingError("malformed state: invalid context counts")
                check_subset(payload)
            else:
                payload = {key: event.get(key) for key in ("completed_count", "focus")}
                if not valid_count(payload["completed_count"]):
                    raise TrackingError("malformed state: invalid completion snapshot")
                if payload["focus"] is not None and not isinstance(payload["focus"], str):
                    raise TrackingError("malformed state: invalid review focus")
            expected = {"kind": kind, "fingerprint": fingerprint(kind, payload)}
            if tracking["identities"].get(identity) != expected:
                raise TrackingError("malformed state: event identity does not match its payload")


def check_subset(payload):
    if (payload["mode"] == "process" and payload["processed"] is not None
            and payload["deferred"] is not None and payload["deferred"] > payload["processed"]):
        raise TrackingError("deferred cannot exceed processed for a process session")


def apply_velocity(value, event):
    if event["mode"] == "process" and event["processed"] is not None:
        return (value if value is not None else 0) * 0.7 + event["processed"] * 0.3
    return value


def refresh(state, today):
    tracking = state["tracking"]
    first = monday(today) - timedelta(weeks=3)
    # Fold expired processing observations into the EMA seed before pruning them.
    # Fingerprints are deliberately never pruned: an old ID must never count twice.
    ordered = sorted(tracking["sessions"].items(), key=lambda item: item[1]["sequence"])
    for identity, event in ordered:
        if parse_date(event["date"]) < first:
            tracking["velocity_seed"] = apply_velocity(tracking["velocity_seed"], event)
            del tracking["sessions"][identity]
    tracking["completion_snapshots"] = {
        identity: event for identity, event in tracking["completion_snapshots"].items()
        if parse_date(event["date"]) >= first
    }
    sessions = [event for event in tracking["sessions"].values() if parse_date(event["date"]) <= today]
    snapshots = [event for event in tracking["completion_snapshots"].values()
                 if parse_date(event["date"]) <= today]
    velocity = tracking["velocity_seed"]
    for event in sorted(sessions, key=lambda event: event["sequence"]):
        velocity = apply_velocity(velocity, event)
    tracking["processing_velocity"] = velocity
    weeks = []
    for index in range(4):
        start = first + timedelta(weeks=index)
        end = start + timedelta(days=6)
        events = [event for event in sessions if start <= parse_date(event["date"]) <= end]
        week = {"start": start.isoformat(), "end": end.isoformat(), "sessions": len(events)}
        for key in ("processed", "deferred"):
            known = [event[key] for event in events if event[key] is not None]
            week[key] = sum(known) if known else None
            week[key + "_complete"] = bool(events) and len(known) == len(events)
            week[key + "_known_sessions"] = len(known)
        known_contexts = [event["contexts"] for event in events if event["contexts"] is not None]
        totals = {}
        for context_counts in known_contexts:
            for key, number in context_counts.items():
                totals[key] = totals.get(key, 0) + number
        week["contexts"] = totals if known_contexts else None
        week["contexts_complete"] = bool(events) and len(known_contexts) == len(events)
        week["contexts_known_sessions"] = len(known_contexts)
        weeks.append(week)
    tracking["weeks"] = weeks
    observed_sessions = [event for event in sessions
                         if any(event[key] is not None for key in ("processed", "deferred", "contexts"))]
    dated_weeks = {monday(parse_date(event["date"])) for event in observed_sessions + snapshots}
    return {
        "weeks": weeks,
        "weekly_processed": [week["processed"] for week in weeks],
        "weekly_deferred": [week["deferred"] for week in weeks],
        "weekly_completed": [None] * 4,
        "processing_velocity": velocity,
        "completion_snapshots": sorted(snapshots, key=lambda event: event["sequence"]),
        "dated_weeks": len(dated_weeks),
        "trends_available": len(dated_weeks) >= 2,
    }


def atomic_write(path, state, binary):
    # Convert before touching the destination. yq receives data, never an expression
    # containing user input. Temporary files share the destination filesystem.
    rendered = yq_run(binary, ["-P", "."], json.dumps(state, ensure_ascii=False, allow_nan=False))
    if not rendered.strip():
        raise TrackingError("yq failed: empty YAML output")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         prefix="." + path.name + ".", delete=False) as stream:
            temporary = stream.name
            if path.exists():
                os.fchmod(stream.fileno(), path.stat().st_mode & 0o777)
            stream.write(rendered)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            os.unlink(temporary)
    return rendered


def legacy_update(state, args):
    print(f"Warning: {args.command} is deprecated; writing only legacy_history", file=sys.stderr)
    legacy = state.setdefault("legacy_history", {})
    if args.command == "context":
        contexts = legacy.setdefault("contexts", {})
        if not valid_contexts(contexts):
            raise TrackingError("malformed legacy context counts")
        contexts[args.name] = contexts.get(args.name, 0) + 1
    elif args.command == "weekly":
        trends = legacy.setdefault("trends", {})
        if not isinstance(trends, dict):
            raise TrackingError("malformed legacy trends")
        for key, value in (("completed", args.completed), ("processed", args.processed), ("deferred", args.deferred)):
            values = trends.setdefault("weekly_" + key, [])
            if not isinstance(values, list):
                raise TrackingError("malformed legacy weekly history")
            trends["weekly_" + key] = (values + [value])[-4:]
    else:
        patterns = legacy.setdefault("patterns", {})
        if not isinstance(patterns, dict):
            raise TrackingError("malformed legacy patterns")
        if args.command == "velocity":
            previous = patterns.get("avg_process_velocity", 0)
            if not valid_velocity(previous):
                raise TrackingError("malformed legacy velocity")
            patterns["avg_process_velocity"] = previous * 0.7 + args.items * 0.3
        else:
            values = patterns.setdefault(args.type + "_days", [])
            if not isinstance(values, list):
                raise TrackingError("malformed legacy day patterns")
            if args.day not in values:
                values.append(args.day)


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    for name in ("init", "read", "health", "review-days", "trends"):
        commands.add_parser(name)
    begin = commands.add_parser("begin", help="generate a stable session/review ID without writing state")
    begin.add_argument("mode")
    session = commands.add_parser("session", help="record net outcomes; retain a stable --id for retries")
    session.add_argument("mode")
    session.add_argument("count", nargs="?", type=count, default=None)
    session.add_argument("--id", help="stable caller-retained ID (preferred; generated if omitted)")
    session.add_argument("--deferred", type=count, default=None)
    session.add_argument("--contexts", type=contexts_arg, default=None)
    review = commands.add_parser("review", help="record a rolling seven-day completion snapshot")
    review.add_argument("count", type=count)
    review.add_argument("focus", nargs="?", default=None)
    review.add_argument("--id", help="stable caller-retained ID (preferred; generated if omitted)")
    context = commands.add_parser("context")
    context.add_argument("name")
    weekly = commands.add_parser("weekly")
    for key in ("completed", "processed", "deferred"):
        weekly.add_argument(key, type=count)
    velocity = commands.add_parser("velocity")
    velocity.add_argument("items", type=count)
    pattern = commands.add_parser("pattern")
    pattern.add_argument("type", choices=("peak", "defer"))
    pattern.add_argument("day")
    return result


def latest_date(state, key, today):
    value = (state.get(key) or {}).get("date")
    candidates = [parse_date(value)] if value else []
    collection = "sessions" if key == "last_session" else "completion_snapshots"
    candidates.extend(parse_date(event["date"]) for event in state["tracking"][collection].values())
    return max((day for day in candidates if day <= today), default=None)


def run(args):
    if args.command == "begin":
        if not args.mode.strip():
            raise TrackingError("mode must not be empty")
        print(uuid.uuid4())
        return
    binary = shutil.which("yq")
    if binary is None:
        raise TrackingError("mikefarah yq is required; install with: brew install yq")
    now = local_now()
    today = now.date()
    path = Path(os.environ.get("GTD_STATE_FILE", str(Path(__file__).resolve().parent.parent / "state.yaml"))).expanduser().absolute()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path) + ".lock", "a", encoding="utf-8") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load_state(path, binary)
        original = copy.deepcopy(state)
        migrate(state)
        validate(state)
        outcome = None
        if args.command in ("session", "review"):
            identity = args.id if args.id is not None else str(uuid.uuid4())
            if not identity.strip():
                raise TrackingError("id must not be empty")
            if args.command == "session":
                if not args.mode.strip():
                    raise TrackingError("mode must not be empty")
                payload = {"mode": args.mode, "processed": args.count,
                           "deferred": args.deferred, "contexts": args.contexts}
                check_subset(payload)
                collection = "sessions"
            else:
                payload = {"completed_count": args.count, "focus": args.focus}
                collection = "completion_snapshots"
            record = {"kind": args.command, "fingerprint": fingerprint(args.command, payload)}
            previous = state["tracking"]["identities"].get(identity)
            if previous is not None:
                if previous != record:
                    raise TrackingError(f"ID conflict: {identity!r} was already recorded with a different payload")
                print(json.dumps({"id": identity, "status": "replayed"}))
                return  # Even a later-day replay must not rewrite state or reapply EMA.
            tracking = state["tracking"]
            tracking["identities"][identity] = record
            tracking[collection][identity] = {
                **payload, "date": today.isoformat(), "sequence": tracking["next_sequence"]
            }
            tracking["next_sequence"] += 1
            if args.command == "session":
                state.setdefault("last_session", {})
                if state["last_session"] is None:
                    state["last_session"] = {}
                state["last_session"].update({"date": today.isoformat(), "mode": args.mode,
                                              "items_processed": args.count, "id": identity})
            else:
                state.setdefault("last_review", {})
                if state["last_review"] is None:
                    state["last_review"] = {}
                state["last_review"].update({"date": today.isoformat(), **payload, "id": identity})
            outcome = {"id": identity, "status": "recorded"}
        if args.command in ("context", "weekly", "velocity", "pattern"):
            # Compatibility setters must not change dated observations or EMA.
            if original.get("schema_version") != SCHEMA_VERSION:
                refresh(state, today)
            legacy_update(state, args)
            atomic_write(path, state, binary)
            return
        summary = refresh(state, today)
        rendered = None
        if state != original or not path.exists():
            rendered = atomic_write(path, state, binary)
        if outcome is not None:
            print(json.dumps(outcome))
        elif args.command == "read":
            print(rendered if rendered is not None else path.read_text(encoding="utf-8"), end="")
        elif args.command == "trends":
            print(json.dumps(summary, ensure_ascii=False, allow_nan=False))
        elif args.command in ("review-days", "health"):
            last_review = latest_date(state, "last_review", today)
            days = (today - last_review).days if last_review else "never"
            if args.command == "health":
                last_session = latest_date(state, "last_session", today)
                print(f"Last session: {last_session.isoformat() if last_session else 'never'}")
                print(f"Days since review: {days}")
            else:
                print(days)


def main():
    args = parser().parse_args()
    try:
        run(args)
    except (TrackingError, OSError, ValueError, TypeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
