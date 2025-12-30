# Daily Planning Workflow

## Progress Checklist

```
Inbox Processing:
- [ ] Fetch inbox items
- [ ] Process each item (actionable? → next action → when → area)
- [ ] Apply 2-minute rule for quick items
- [ ] Confirm all items cleared
```

## Processing Flow

### Quick Mode (Default)

```
"[N/total]: '[ITEM]' — actionable?"

→ no/reference/delete: Execute, next item
→ yes: "Next physical action?" → "When?" → "Which area?"
→ Execute update_todo, confirm briefly, next item
```

### Full Mode

Trigger: user says "full mode" or item is complex. Add:
- Priority? → high = flag
- Single task or project?
- Context? (@home/@office/@calls/@errands)
- Energy? (#high/#low/#quick)
- Waiting on anyone? → @waiting tag

## Smart Detection

| Pattern | Action |
|---------|--------|
| Quick keywords (email, call, check) | "Looks quick — do now?" |
| Multiple similar items | "Process together with same area?" |
| Multi-step task | "Create as project?" |
| Similar existing task | "Merge or keep separate?" |
| Area overload (8+ tasks) | "Area has 8 tasks — still add?" |

## Calendar Integration

Before scheduling to "today":
1. `list-today-events` to check calendar
2. If conflict: "You have '[event]' at [time]. Schedule before/after?"
3. If busy day: "Heavy calendar — keep small or move to tomorrow?"

For focus tasks: "This needs ~1 hour. Gap at 2-4pm. Block it?"

## Date Semantics

- "When?" → `when` parameter (start date)
- "Due date?" → `deadline` parameter (hard deadline, only ask if external)

## Session Flow

1. Start: "X items. Let's clear them."
2. Keep pace: 5-10 min for typical inbox
3. Confirm tersely: "Done. Today, @calls."
