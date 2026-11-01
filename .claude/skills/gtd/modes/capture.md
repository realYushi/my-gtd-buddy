# Quick Capture

Capture puts work into Inbox. Disposition happens later in [process.md](process.md).

## Start

```bash
.claude/skills/gtd/scripts/reminders.sh add "[title]" Inbox
```

Respond `Captured: [title]`.

**Multiple items:** Parse comma-separated, "and"-joined, or line-broken lists. Run one `add` per item, then confirm as a batch:

```
Captured:
• Call dentist
• Buy groceries
• Email Sarah re: project
```

**Due date clue:** For "remind me to call mom tomorrow", use the natural-date form:

```bash
.claude/skills/gtd/scripts/reminders.sh add-natural "call mom" Inbox "tomorrow"
```

Capture is complete when every named item exists exactly once in Inbox. New captures are not processed items and do not contribute to processing totals.
