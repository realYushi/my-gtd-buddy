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
| `delete <id>` | Delete |
| `undo` | Undo last move/complete |

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
| `free [calendar]` | Free time today (9AM-6PM) |
| `gaps [mins] [calendar]` | Find free gaps (default: 30 min) |

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
| `session <mode> <count>` | Update after session |
| `review <count> [focus]` | Update after review |
| `health` | Quick health summary |
| `review-days` | Days since last review |

### Tracking

| Command | Description |
|---------|-------------|
| `trends` | Show trends and patterns |
| `context <name>` | Increment context usage (home/office/errands/calls) |
| `weekly <completed> <processed> <deferred>` | Update weekly trends |
| `velocity <n>` | Update processing velocity |
| `pattern <type> <day>` | Record day pattern (peak/defer) |

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
