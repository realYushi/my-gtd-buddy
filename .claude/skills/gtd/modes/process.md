# Inbox Processing

## Start

```bash
.claude/skills/gtd/scripts/reminders.sh inbox
.claude/skills/gtd/scripts/state.sh begin process
```

Keep the printed session ID for this conversation. Reuse it if the session is interrupted and resumed.

**Empty:** "Inbox clear." → end

**Has items:** Jump straight in. Show count in first item:

```
1/5: 'Call dentist'
Actionable? (now/later/someday/delete)
```

Show the first item immediately.

## Per-Item Flow

**Simple items:**
```
1/5: 'Call dentist'
Actionable? (now/later/someday/delete)

→ "later"
```
Move it, show next item immediately.

**Looks like a project** (multi-step, vague, or big):
```
2/5: 'Plan vacation'
Sounds like a project. What's ONE next action?

→ "research flights"

Got it. Keep 'Plan vacation' in Projects? (y/n)
```

**Has a due date or time clue** ("dentist appointment Tuesday"):
```
3/5: 'Dentist appointment Tuesday'
When? (I'll set the due date)

→ "tuesday 2pm"
```
Use `add-natural` for date parsing, then `process` to move it to Next Actions.

## One Decision Per Item

Write every disposition through the Reminder changes module:

| Disposition | Command |
|-------------|---------|
| `now` | `reminders.sh now <id> [context] [energy] [duration]` |
| `later` | `reminders.sh process <id> [context] [energy] [duration]` |
| `delegate [person]` | `reminders.sh delegate <id> "[person]"` |
| `someday` | `reminders.sh defer <id>` |
| `delete` | `reminders.sh delete <id>` |

Processing and flagging are one decision. Write each disposition with exactly one command. Command outcomes follow [Error Recovery](../SKILL.md#error-recovery).

## Response Mapping

| User Says | Action |
|-----------|--------|
| `now` | → Next Actions (flagged for today) |
| `later` | → Next Actions |
| `later home` | → Next Actions with @home tag |
| `someday` | → Someday |
| `delete` | Delete |
| `skip` | Next item |
| `stop` | End session |
| `home` / `office` / `errands` / `calls` | → Next Actions with @context tag |
| `delegate [person]` | → Waiting For with @waiting: [person] |

**Context shortcut:** Any context word combined with a disposition adds the tag. "later office" = move to Next Actions + @office tag.

**Delegate shortcut:** "delegate sarah" = move to Waiting For + @waiting: Sarah.

## Response Rules

**Position:** Show `N/total: 'Title'` for the current item.

**Flow:** After each decision, show the next item immediately. Save recaps for the end.

**Interruptions:** On `stop`, `pause`, or `wait`, end the session at the current item. Record net outcomes, then offer to resume later.

## Session End

When the session ends — including `stop`, `pause`, or an interruption — record net outcomes after subtracting any decision reversed during this session. Omit a value you do not know; do not invent zero.

```bash
.claude/skills/gtd/scripts/state.sh session process <processed> --id <session-id> --deferred <deferred>
```

Add `--contexts '{"home":2,"office":1}'` only when contexts were assigned. Repeating the same call with the same ID is safe.

```
Done. 5 processed:
• 3 → Next Actions
• 1 → Someday
• 1 deleted

Anything else?
```
