#!/usr/bin/env python3
"""Reminder decisions and reversal. Shell queries remain in reminders.sh."""
import argparse
import contextlib
import datetime as dt
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid


# Every string crosses argv. Foundation supplies lossless JSON, including notes.
READ_SCRIPT = '''use framework "Foundation"
on run argv
    tell application "Reminders"
        set r to reminder id (item 1 of argv)
        set noteText to body of r
        if noteText is missing value then set noteText to ""
        set reminderID to id of r
        set listName to name of container of r
        set isFlagged to flagged of r
        set isCompleted to completed of r
    end tell
    set payload to current application's NSMutableDictionary's dictionary()
    payload's setObject:reminderID forKey:"id"
    payload's setObject:listName forKey:"list"
    payload's setObject:noteText forKey:"body"
    payload's setObject:isFlagged forKey:"flagged"
    payload's setObject:isCompleted forKey:"completed"
    set jsonData to current application's NSJSONSerialization's dataWithJSONObject:payload options:0 |error|:(missing value)
    return (current application's NSString's alloc()'s initWithData:jsonData encoding:(current application's NSUTF8StringEncoding)) as text
end run
'''

PATCH_SCRIPT = '''use framework "Foundation"
on run argv
    set jsonText to current application's NSString's stringWithString:(item 2 of argv)
    set jsonData to jsonText's dataUsingEncoding:(current application's NSUTF8StringEncoding)
    set payload to current application's NSJSONSerialization's JSONObjectWithData:jsonData options:0 |error|:(missing value)
    set expected to payload's objectForKey:"expected"
    set desired to payload's objectForKey:"desired"
    tell application "Reminders"
        set r to reminder id (item 1 of argv)
        repeat with keyName in {"body", "flagged", "completed", "list"}
            set keyText to keyName as text
            if (expected's objectForKey:keyText) is not missing value then
                if keyText is "body" then
                    set actualValue to body of r
                    if actualValue is missing value then set actualValue to ""
                    set expectedValue to (expected's objectForKey:keyText) as text
                else if keyText is "list" then
                    set actualValue to name of container of r
                    set expectedValue to (expected's objectForKey:keyText) as text
                else if keyText is "flagged" then
                    set actualValue to flagged of r
                    set expectedValue to (expected's objectForKey:keyText) as boolean
                else
                    set actualValue to completed of r
                    set expectedValue to (expected's objectForKey:keyText) as boolean
                end if
                if actualValue is not expectedValue then error "Reminder changed before applying decision" number 1001
            end if
        end repeat
        -- Validate the target before changing notes or flags.
        if (desired's objectForKey:"list") is not missing value then
            set targetList to list ((desired's objectForKey:"list") as text)
        end if
        if (desired's objectForKey:"body") is not missing value then set body of r to ((desired's objectForKey:"body") as text)
        if (desired's objectForKey:"flagged") is not missing value then set flagged of r to ((desired's objectForKey:"flagged") as boolean)
        if (desired's objectForKey:"completed") is not missing value then set completed of r to ((desired's objectForKey:"completed") as boolean)
        if (desired's objectForKey:"list") is not missing value then move r to targetList
    end tell
end run
'''


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, ensure_ascii=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


@contextlib.contextmanager
def history_lock(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(str(path) + '.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield


class AppleScriptAdapter:
    def run(self, script, *args):
        result = subprocess.run(['osascript', '-', *args], input=script,
                                text=True, capture_output=True)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or 'Reminders did not respond')
        return result.stdout

    def read(self, reminder_id):
        return json.loads(self.run(READ_SCRIPT, reminder_id))

    def patch(self, reminder_id, expected, desired):
        self.run(PATCH_SCRIPT, reminder_id,
                 json.dumps({'expected': expected, 'desired': desired}))

    def delete(self, reminder_id):
        self.run('''on run argv
    tell application "Reminders" to delete reminder id (item 1 of argv)
end run''', reminder_id)


class CommandAdapter:
    """Internal test seam: executable receives operation/id and JSON on stdin."""
    def __init__(self, executable):
        self.executable = executable

    def call(self, operation, reminder_id, payload=None):
        result = subprocess.run([self.executable, operation, reminder_id],
                                input=json.dumps(payload), text=True, capture_output=True)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or 'Adapter failed')
        return json.loads(result.stdout) if result.stdout.strip() else None

    def read(self, reminder_id):
        return self.call('read', reminder_id)

    def patch(self, reminder_id, expected, desired):
        self.call('patch', reminder_id, {'expected': expected, 'desired': desired})

    def delete(self, reminder_id):
        self.call('delete', reminder_id)


class ReminderChanges:
    def __init__(self, adapter, history):
        self.adapter = adapter
        self.history = Path(history)

    def load(self):
        if not self.history.exists():
            return []
        try:
            records = json.loads(self.history.read_text())
        except json.JSONDecodeError as exc:
            raise ValueError('Legacy or invalid undo history; preserve it elsewhere before starting a new history') from exc
        if not isinstance(records, list) or any(not isinstance(r, dict) for r in records):
            raise ValueError('Invalid undo history')
        return records

    def save(self, records):
        atomic_json(self.history, records[-10:])

    @staticmethod
    def result(status, reminder_id=None, **details):
        return {'status': status, 'reminder_id': reminder_id, **details}

    def change(self, operation, reminder_id, **options):
        with history_lock(self.history):
            records = self.load()  # Fail before touching Reminders if history is unreadable.
            before = self.adapter.read(reminder_id)
            desired = {}
            if operation == 'move':
                desired['list'] = options['target']
            elif operation == 'complete':
                desired['completed'] = True
            elif operation in ('process', 'now'):
                desired['list'] = 'Next Actions'
                tags = []
                for key, prefix in [('context', '@'), ('energy', '#'), ('duration', '#')]:
                    value = options.get(key)
                    if value:
                        tag = prefix + value.lstrip('@#')
                        if tag not in before['body'].split():
                            tags.append(tag)
                if tags:
                    desired['body'] = ' '.join(tags) + ('\n' + before['body'] if before['body'] else '')
                if operation == 'now':
                    desired['flagged'] = True
            elif operation == 'delegate':
                desired['list'] = 'Waiting For'
                line = '@waiting: ' + options['person']
                desired['body'] = line + ('\n' + before['body'] if before['body'] else '')
            elif operation == 'defer':
                desired['list'] = 'Someday'
            elif operation != 'delete':
                raise ValueError('Unsupported Reminder decision')
            desired = {k: v for k, v in desired.items() if before[k] != v}
            if not desired and operation != 'delete':
                return self.result('unchanged', reminder_id, undo_available=False, retry_safe=True)
            expected = {k: before[k] for k in desired}
            error = None
            try:
                if operation == 'delete':
                    self.adapter.delete(reminder_id)
                else:
                    self.adapter.patch(reminder_id, expected, desired)
            except RuntimeError as exc:
                error = str(exc)
            if operation == 'delete':
                # A failed read cannot distinguish deletion from an unavailable app.
                # Never automatically retry an uncertain permanent deletion.
                return self.result('uncertain' if error else 'changed', reminder_id,
                                   undo_available=False, retry_safe=False, error=error)
            try:
                after = self.adapter.read(reminder_id)
            except Exception as exc:
                # Preserve the intent before returning an uncertain result. Undo first
                # checks actual values, so a guessed result is never applied blindly.
                record = self.record(reminder_id, operation, expected, desired, uncertain=True)
                try:
                    self.save(records + [record])
                    saved = True
                except OSError:
                    saved = False
                return self.result('uncertain', reminder_id, undo_available=False,
                                   recovery_recorded=saved, retry_safe=False,
                                   error=error or str(exc))
            actual = {k: after[k] for k in desired if after[k] != before[k]}
            if not actual:
                return self.result('failed', reminder_id, undo_available=False,
                                   retry_safe=True, error=error or 'No change observed')
            record = self.record(reminder_id, operation,
                                 {k: before[k] for k in actual}, actual)
            full = all(after[k] == v for k, v in desired.items())
            # Only observed intended changes are safe to reverse. Unexpected values
            # may be external edits, so preserve them and report the uncertainty.
            unexpected = [k for k in actual if actual[k] != desired[k]]
            if unexpected:
                record['uncertain'] = True
            try:
                self.save(records + [record])
            except OSError as exc:
                return self.result('partial', reminder_id, changed=actual,
                                   undo_available=False, retry_safe=False,
                                   error='Reminder changed; undo history could not be saved: ' + str(exc))
            return self.result('changed' if full and not error else 'partial', reminder_id,
                               changed=actual, decision_id=record['decision_id'],
                               undo_available=not unexpected, retry_safe=False, error=error)

    @staticmethod
    def record(reminder_id, operation, before, after, uncertain=False):
        return {'decision_id': str(uuid.uuid4()), 'reminder_id': reminder_id,
                'operation': operation, 'before': before, 'after': after,
                'date': dt.datetime.now().astimezone().isoformat(), 'uncertain': uncertain}

    def undo(self):
        with history_lock(self.history):
            records = self.load()
            if not records:
                return self.result('empty', undo_available=False, retry_safe=True)
            record = records[-1]
            rid = record['reminder_id']
            current = self.adapter.read(rid)
            before, after = record['before'], record['after']
            if record.get('uncertain'):
                # Resolve an unverified attempt only if every field is original or
                # intended. Any third value may be a later edit.
                conflict = [k for k in after if current[k] not in (before[k], after[k])]
                remaining = {k: before[k] for k in after if current[k] == after[k] and before[k] != after[k]}
            else:
                conflict = [k for k in after if current[k] != after[k]]
                remaining = dict(before)
            if conflict:
                return self.result('conflict', rid, fields=conflict,
                                   undo_available=True, retry_safe=False)
            error = None
            try:
                if remaining:
                    self.adapter.patch(rid, {k: current[k] for k in remaining}, remaining)
            except RuntimeError as exc:
                error = str(exc)
            try:
                observed = self.adapter.read(rid)
            except Exception as exc:
                return self.result('uncertain', rid, undo_available=True,
                                   retry_safe=False, error=error or str(exc))
            pending = {k: v for k, v in remaining.items() if observed[k] != v}
            if pending:
                # Retain only still-unrestored fields. A future attempt must match
                # their observed values, and cannot overwrite unrelated changes.
                if all(observed[k] in (current[k], remaining[k]) for k in remaining):
                    record['before'] = pending
                    record['after'] = {k: observed[k] for k in pending}
                    record['uncertain'] = False
                    self.save(records)
                return self.result('partial', rid, undo_available=True,
                                   retry_safe=False, error=error or 'Some values were not restored')
            try:
                self.save(records[:-1])
            except OSError as exc:
                return self.result('partial', rid, undo_available=False, retry_safe=False,
                                   error='Reminder restored; history entry could not be removed: ' + str(exc))
            return self.result('undone', rid, decision_id=record['decision_id'],
                               undo_available=bool(records[:-1]), retry_safe=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=['move', 'process', 'now', 'delegate', 'defer', 'complete', 'delete', 'undo'])
    parser.add_argument('id', nargs='?')
    parser.add_argument('values', nargs='*')
    args = parser.parse_args(argv)
    adapter = CommandAdapter(os.environ['GTD_REMINDERS_ADAPTER']) if os.environ.get('GTD_REMINDERS_ADAPTER') else AppleScriptAdapter()
    history = os.environ.get('GTD_UNDO_FILE', str(Path(__file__).resolve().parent.parent / '.undo_stack'))
    changes = ReminderChanges(adapter, history)
    try:
        if args.operation == 'undo':
            result = changes.undo()
        else:
            if not args.id:
                raise ValueError('A reminder id is required')
            values = args.values
            options = {}
            if args.operation in ('move', 'delegate'):
                if not values or not values[0]:
                    raise ValueError('A target list or person is required')
                options['target' if args.operation == 'move' else 'person'] = values[0]
            elif args.operation in ('process', 'now'):
                options.update(zip(('context', 'energy', 'duration'), values))
            result = changes.change(args.operation, args.id, **options)
        print(json.dumps(result, ensure_ascii=False))
        return 0 if result['status'] in ('changed', 'unchanged', 'undone', 'empty') else 2
    except (OSError, ValueError, RuntimeError, KeyError) as exc:
        print(json.dumps({'status': 'failed', 'retry_safe': False, 'error': str(exc)}))
        return 2


if __name__ == '__main__':
    sys.exit(main())
