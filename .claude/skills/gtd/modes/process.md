# Inbox Processing

## Start

```bash
.claude/skills/gtd/scripts/reminders.sh inbox
```

**Empty:** "Inbox clear." → end

**Has items:** Show count + first item immediately.

## Per-Item Flow

**Simple items:**
```
"N/total: '[title]'
 Actionable? When? (now/later/someday/delete)"

→ "y later" or "n delete" or "someday"
```

**Complex items (projects):**
```
"N/total: '[title]'
 Sounds like a project. What's ONE next action?"

→ "schedule meeting with john"

"Got it. Keep '[title]' in Projects? (y/n)"
```

## Response Mapping

| User Says | Action |
|-----------|--------|
| `y now` | → Next Actions (flagged) |
| `y later` | → Next Actions |
| `n delete` / `delete` | Delete |
| `n someday` / `someday` | → Someday |
| `skip` | Next item |
| `stop` | End session |

**Optional context:** `"y later home"` → adds `@home` to notes

## Pacing

- 10-20 seconds per simple item
- If user hesitates: "Skip for now?"

## Session End

```bash
.claude/skills/gtd/scripts/state.sh session process <count>
```

```
"Done. [N] processed:
 • [X] → Next Actions
 • [Y] → Someday
 • [Z] → Deleted

Anything else?"
```

