# Inbox Processing

## Start

```bash
.claude/skills/gtd/scripts/reminders.sh inbox
```

**Empty:** "Inbox clear." → end

**Has items:** Jump straight in. Show count in first item:

```
1/5: 'Call dentist'
Actionable? (now/later/someday/delete)
```

No preamble. No "Let's process your inbox!" Just the first item.

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
Use `add-natural` for date parsing, move to Next Actions.

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

## Error Handling

If a script fails mid-session:
1. Retry once
2. If still fails: "Reminders not responding. Open the app and try again?"
3. Don't lose track of position — remember where you were

## Session End

```bash
.claude/skills/gtd/scripts/state.sh session process <count>
```

```
Done. 5 processed:
• 3 → Next Actions
• 1 → Someday
• 1 deleted

Anything else?
```
