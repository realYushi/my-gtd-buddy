# CLI Reference

## Contents

- [Reminders](#reminders)
- [Calendar](#calendar)
- [State](#state)
- [Tags](#tags)

---

## Reminders

Script: `.claude/skills/gtd/scripts/reminders.sh`

### Lists

| Command | Description |
|---------|-------------|
| `lists` | List all reminder lists |
| `setup` | Create GTD lists if missing |

### Read

| Command | Description |
|---------|-------------|
| `inbox` | Get Inbox items |
| `next` | Get Next Actions |
| `waiting` | Get Waiting For items |
| `someday` | Get Someday items |
| `projects` | Get Projects |
| `list <name>` | Get items from specific list |
| `today` | Due today or flagged |
| `upcoming` | Items with future due dates |
| `counts` | Item counts per list |
| `completed [days]` | Completed items (default: 7) |

### Search

| Command | Description |
|---------|-------------|
| `search <query>` | Search title/notes |
| `priority <0-9>` | Search by priority (1=high, 5=med, 9=low) |
| `flagged` | Get flagged items |
| `context <tag>` | Filter by tag (@home, #quick) |
| `stale [days]` | Untouched items (default: 7) |

### Write

| Command | Description |
|---------|-------------|
| `add <title> [list] [notes] [due] [flagged] [priority]` | Add reminder |
| `add-natural <title> [list] <due> [notes] [flagged]` | Add with natural language date |
| `parse-date <string>` | Test date parsing |
| `update <id> <prop> <val>` | Update property |
| `move <id> <list>` | Move to list |
| `complete <id>` | Mark complete |
| `delete <id>` | Delete permanently |
| `undo` | Reverse the last decision, preserving later edits |

### Natural Language Dates

`add-natural` supports:
- `today`, `tomorrow`, `tmr`
- `monday`, `tue`, `next friday`
- `next week`
- `2pm`, `14:00`, `3:30pm`
- `tomorrow 2pm`, `fri 9am`
- `Jan 15`, `12/25`

### GTD

| Command | Description |
|---------|-------------|
| `now <id> [context] [energy] [duration]` | Move to Next Actions, add tags, and flag as one decision |
| `process <id> [context] [energy] [duration]` | Move to Next Actions with tags |
| `delegate <id> <person>` | Move to Waiting For |
| `defer <id>` | Move to Someday |
| `batch-defer [days]` | Defer all items stale > N days (default: 14) |
| `orphan-projects` | Find projects without next actions |
| `waiting-age` | Show waiting items with age |

---

## Calendar

Script: `.claude/skills/gtd/scripts/calendar.sh`

### Lists

| Command | Description |
|---------|-------------|
| `calendars` | List all calendars |

### Read

| Command | Description |
|---------|-------------|
| `today [calendar]` | Today's events |
| `tomorrow [calendar]` | Tomorrow's events |
| `week [calendar]` | This week's events |
| `date <YYYY-MM-DD> [calendar]` | Events on specific date |
| `upcoming [days] [calendar]` | Upcoming events (default: 7 days) |
| `free [calendar]` | Available time remaining today (9AM-6PM) |
| `gaps [mins] [calendar]` | Available intervals remaining today (default: 30 min) |

Both commands start at the later of now and 9AM. Overlapping events count once, events already underway are included, and all-day events are excluded.

### Search

| Command | Description |
|---------|-------------|
| `search <query> [calendar] [days]` | Search events (default: 30 days) |

### Write

| Command | Description |
|---------|-------------|
| `add <title> <start> <end> [calendar] [location] [notes]` | Add event |
| `add-allday <title> <YYYY-MM-DD> [calendar] [notes]` | Add all-day event |
| `delete <event_id> <calendar>` | Delete event |

Date/time format: `YYYY-MM-DD HH:MM`

---

## State

Script: `.claude/skills/gtd/scripts/state.sh`

### Basic

| Command | Description |
|---------|-------------|
| `read` | Read full state |
| `begin <mode>` | Generate a stable session or review ID without writing |
| `session <mode> [count] --id <id> [--deferred N] [--contexts JSON]` | Record net outcomes for one session |
| `review <count> [focus] --id <id>` | Record a dated seven-day completion snapshot |
| `health` | Quick health summary |
| `review-days` | Days since last review |
| `trends` | Dated weeks, completion snapshots, and velocity |

Retain the ID from `begin`. Repeating a `session` or `review` call with the same ID and payload is a no-op; reusing it with different values is an error. Omit unknown counts. `processed` counts Inbox dispositions; `deferred` counts Inbox items moved to Someday. Same-session undo is subtracted before recording. Coach sessions do not affect processing velocity.

### Legacy compatibility

`context`, `weekly`, `velocity`, and `pattern` only update `legacy_history`. They never contribute to dated totals. Modes do not use them.

---

## Tags

Stored in reminder notes field.

| Type | Tags |
|------|------|
| Location | `@home` `@office` `@errands` `@calls` |
| Energy | `#high` `#low` `#quick` |
| Duration | `#5min` `#15min` `#30min` `#1hour` `#deep` |
| Waiting | `@waiting: <person>` |

Native features:
- **Flagged** = today's focus
- **Priority 1/5/9** = high/medium/low
- **Due date** = hard deadline

---

## Output Formats

### Reminders
```
<id>	<name>	<notes>	<due>	<flagged>	<priority>
```

### Calendar
```
<id>	<title>	<start>	<end>	<location>	<calendar>	<allday>
```

### Waiting Age
```
<id>	<name>	<waiting_for>	<age in days>
```
