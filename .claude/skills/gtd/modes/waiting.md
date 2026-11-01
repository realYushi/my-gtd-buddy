# Waiting Check

Review delegated work and decide whether each item still waits, needs a nudge, or is done.

## Start

```bash
.claude/skills/gtd/scripts/reminders.sh waiting-age
```

Show items with who and age. Mark items older than 7 days with ⚠️ and offer a nudge:

```
Waiting on:
• 'API access' — Sarah — 3 days
• 'Budget approval' — Mike — 12 days ⚠️

Nudge Mike? (y/n)
```

## Decisions

| Response | Action |
|----------|--------|
| keep waiting | Leave the reminder unchanged |
| nudge | Add "Follow up with [person] re: [item]" to Next Actions |
| done | `reminders.sh complete <id>` |

Adding a follow-up does not change the waiting item. A completion is one undoable Reminder decision and follows [Error Recovery](../SKILL.md#error-recovery).

The check is complete when every waiting item is unchanged, has a follow-up next action, or is completed.
