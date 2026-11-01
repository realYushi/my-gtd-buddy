# Inbox Processing

## Start

```bash
.claude/skills/gtd/scripts/reminders.sh inbox
.claude/skills/gtd/scripts/outcomes.sh begin
```

Start completes when you hold `session_id` and its `ticket`. Calling `begin` again resumes the active session.

**Empty:** close, say "Inbox clear," and end.

**Has items:** show the first item immediately.

```
1/5: 'Call dentist'
Actionable? (now/later/someday/delete)
```

## One Decision Per Item

Send each disposition through the durable ticket:

```bash
.claude/skills/gtd/scripts/outcomes.sh answer "$TICKET" \
  '{"type":"dispose","reminder_id":"<id>","disposition":"later","context":"home"}'
```

| User says | `disposition` | Extra field |
|-----------|---------------|-------------|
| `now` | `now` | context, energy, duration |
| `later` | `later` | context, energy, duration |
| `delegate Sarah` | `delegate` | `"person":"Sarah"` |
| `someday` | `someday` | — |
| `delete` | `delete` | — |

A context word beside `now` or `later` adds that tag. Include `energy` and `duration` only when the user gives them.

The decision is complete when `answer` returns a new `ticket` and an observation of `confirmed`, `not_applied`, or `unknown`. Use the new ticket for the next item. `skip` sends no reply; show the next item.

**Project clue** (multi-step, vague, or big):

```
2/5: 'Plan vacation'
Sounds like a project. What's ONE next action?

→ "research flights"

Got it. Keep 'Plan vacation' in Projects? (y/n)
```

A project disposition is complete when one next action exists in Next Actions and the project item is retained in Projects or the user chooses another outcome.

**Date clue:**

```
3/5: 'Dentist appointment Tuesday'
When? (I'll set the due date)

→ "tuesday 2pm"
```

Set the date with `reminders.sh add-natural`, then send the disposition through `outcomes.sh`.

## Undo

```bash
.claude/skills/gtd/scripts/outcomes.sh answer "$TICKET" \
  '{"type":"undo","decision_id":"<decision-id>"}'
```

Undo is complete when the reminder is restored and the decision reads `reversed`, or when you report a conflict. Only the latest eligible decision can be reversed. Before close, Undo subtracts its contribution.

Once the session is closed, `reminders.sh undo` restores the reminder; the recorded Session outcome stays unchanged.

## Unknown Result

When an answer returns an `issue` or an `unknown` observation, observe once:

```bash
.claude/skills/gtd/scripts/outcomes.sh answer "$TICKET" '{"type":"observe"}'
```

Then report the result. If it remains unknown, close as incomplete.

## Session End

`stop`, `pause`, `wait`, or an empty Inbox end here.

```bash
.claude/skills/gtd/scripts/outcomes.sh answer "$TICKET" '{"type":"close"}'
```

Session end is complete when `close` returns an outcome. The module owns processed, deferred, and context totals; missing values stay omitted and unresolved decisions make the outcome incomplete.

```
Done. 5 processed:
• 3 → Next Actions
• 1 → Someday
• 1 deleted

Anything else?
```
