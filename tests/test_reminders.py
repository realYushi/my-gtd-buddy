"""Exercise decision logic at the same interface used by reminders.sh."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / '.claude/skills/gtd/scripts'
spec = importlib.util.spec_from_file_location('gtd_reminders', SCRIPTS / 'gtd_reminders.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class FakeReminders:
    def __init__(self):
        self.items = {'r': {'id': 'r', 'list': 'Inbox', 'body': 'original\nnotes\t|"quoted"',
                            'flagged': False, 'completed': False, 'name': 'Original'}}
        self.fail = None
        self.unreadable = False

    def read(self, rid):
        if self.unreadable:
            raise RuntimeError('offline')
        return dict(self.items[rid])

    def patch(self, rid, expected, desired):
        item = self.items[rid]
        if any(item[k] != v for k, v in expected.items()):
            raise RuntimeError('conflict')
        if self.fail == 'before':
            raise RuntimeError('failed before change')
        for k, v in desired.items():
            item[k] = v
            if self.fail == 'partial':
                raise RuntimeError('interrupted')
        if self.fail == 'offline-after':
            self.unreadable = True
            raise RuntimeError('lost connection')

    def delete(self, rid):
        del self.items[rid]


class ReminderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.history = Path(self.temp.name) / 'undo.json'
        self.fake = FakeReminders()
        self.changes = m.ReminderChanges(self.fake, self.history)

    def test_whole_now_decision_and_unrelated_edit_survives(self):
        original = dict(self.fake.items['r'])
        result = self.changes.change('now', 'r', context='home', energy='#low')
        self.assertEqual(result['status'], 'changed')
        self.assertTrue(self.fake.items['r']['flagged'])
        self.assertTrue(self.fake.items['r']['body'].startswith('@home #low\n'))
        self.fake.items['r']['name'] = 'Edited elsewhere'
        self.assertEqual(self.changes.undo()['status'], 'undone')
        original['name'] = 'Edited elsewhere'
        self.assertEqual(self.fake.items['r'], original)
        self.assertEqual(json.loads(self.history.read_text()), [])

    def test_delegate_and_two_successive_undos(self):
        self.changes.change('process', 'r', context='@home')
        self.changes.change('delegate', 'r', person='Sarah "A"\nSmith')
        self.assertEqual(self.changes.undo()['status'], 'undone')
        self.assertEqual(self.fake.items['r']['list'], 'Next Actions')
        self.assertEqual(self.changes.undo()['status'], 'undone')
        self.assertEqual(self.fake.items['r']['list'], 'Inbox')

    def test_conflict_leaves_every_field_and_history_untouched(self):
        self.changes.change('now', 'r', context='home')
        self.fake.items['r']['body'] += '\nnew external edit'
        before = dict(self.fake.items['r'])
        history = self.history.read_text()
        self.assertEqual(self.changes.undo()['status'], 'conflict')
        self.assertEqual(self.fake.items['r'], before)
        self.assertEqual(self.history.read_text(), history)

    def test_failed_completion_does_not_record_history(self):
        self.fake.fail = 'before'
        result = self.changes.change('complete', 'r')
        self.assertEqual(result['status'], 'failed')
        self.assertTrue(result['retry_safe'])
        self.assertFalse(self.history.exists())

    def test_history_write_failure_reports_applied_change(self):
        with patch.object(self.changes, 'save', side_effect=OSError('disk full')):
            result = self.changes.change('complete', 'r')
        self.assertEqual(result['status'], 'partial')
        self.assertTrue(self.fake.items['r']['completed'])
        self.assertFalse(result['undo_available'])
        self.assertFalse(result['retry_safe'])

    def test_partial_change_can_undo_observed_fields(self):
        self.fake.fail = 'partial'
        result = self.changes.change('now', 'r', context='home')
        self.assertEqual(result['status'], 'partial')
        self.fake.fail = None
        self.assertEqual(self.changes.undo()['status'], 'undone')
        self.assertEqual(self.fake.items['r']['list'], 'Inbox')
        self.assertFalse(self.fake.items['r']['flagged'])

    def test_partial_undo_retains_only_pending_fields(self):
        original = dict(self.fake.items['r'])
        self.changes.change('now', 'r', context='home')
        self.fake.fail = 'partial'
        self.assertEqual(self.changes.undo()['status'], 'partial')
        self.fake.fail = None
        self.assertEqual(self.changes.undo()['status'], 'undone')
        self.assertEqual(self.fake.items['r'], original)

    def test_uncertain_change_inspected_before_reversal(self):
        self.fake.fail = 'offline-after'
        self.assertEqual(self.changes.change('now', 'r', context='home')['status'], 'uncertain')
        self.fake.unreadable = False
        self.fake.fail = None
        self.assertEqual(self.changes.undo()['status'], 'undone')
        self.assertEqual(self.fake.items['r']['list'], 'Inbox')
        self.assertFalse(self.fake.items['r']['flagged'])

    def test_ten_decisions_retained(self):
        for n in range(12):
            self.changes.change('move', 'r', target=f'List {n}')
        self.assertEqual(len(json.loads(self.history.read_text())), 10)
        for _ in range(10):
            self.assertEqual(self.changes.undo()['status'], 'undone')
        self.assertEqual(self.fake.items['r']['list'], 'List 1')
        self.assertEqual(self.changes.undo()['status'], 'empty')

    def test_delete_permanent_and_legacy_history_preserved(self):
        result = self.changes.change('delete', 'r')
        self.assertEqual(result['status'], 'changed')
        self.assertFalse(result['undo_available'])
        self.history.write_text('move|r|Inbox|1\n')
        with self.assertRaises(ValueError):
            self.changes.change('move', 'other', target='Someday')
        self.assertEqual(self.history.read_text(), 'move|r|Inbox|1\n')

    def test_shell_entry_point_uses_same_decisions(self):
        state = Path(self.temp.name) / 'adapter-state.json'
        state.write_text(json.dumps(self.fake.items['r']))
        adapter = Path(self.temp.name) / 'adapter'
        adapter.write_text('''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
operation, reminder_id = sys.argv[1:3]
payload = json.load(sys.stdin) if operation != 'read' else None
path = Path(os.environ['FAKE_STATE'])
item = json.loads(path.read_text())
if operation == 'read':
    print(json.dumps(item))
elif operation == 'patch':
    if any(item[k] != v for k, v in payload['expected'].items()):
        raise SystemExit('conflict')
    item.update(payload['desired'])
    path.write_text(json.dumps(item))
    print('{}')
elif operation == 'delete':
    print('{}')
''')
        adapter.chmod(0o755)
        env = dict(os.environ, GTD_REMINDERS_ADAPTER=str(adapter), FAKE_STATE=str(state),
                   GTD_UNDO_FILE=str(Path(self.temp.name) / 'cli-undo.json'))
        script = SCRIPTS / 'reminders.sh'
        result = subprocess.run([str(script), 'now', 'r', 'home'], env=env, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'changed')
        self.assertTrue(json.loads(state.read_text())['flagged'])
        result = subprocess.run([str(script), 'undo'], env=env, text=True, capture_output=True)
        self.assertEqual(json.loads(result.stdout)['status'], 'undone')
        restored = json.loads(state.read_text())
        self.assertFalse(restored['flagged'])
        self.assertEqual(restored['list'], 'Inbox')


if __name__ == '__main__':
    unittest.main()
