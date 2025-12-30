# MCP Tools Reference

## Things 3

| Category | Tools |
|----------|-------|
| **Read** | `get_inbox`, `get_today`, `get_upcoming`, `get_anytime`, `get_someday`, `get_logbook`, `get_trash` |
| **Query** | `get_todos`, `get_projects`, `get_areas`, `get_tags`, `get_tagged_items`, `get_recent` |
| **Search** | `search_todos` (text), `search_advanced` (status, deadline, tag, area, start_date) |
| **Write** | `add_todo`, `add_project`, `update_todo`, `update_project` |
| **Navigate** | `show_item` (open in Things) |

## macOS Calendar

| Category | Tools |
|----------|-------|
| **Read** | `list-calendars`, `list-today-events` |
| **Search** | `search-events` (query, optional calendar filter) |
| **Write** | `create-event` (title, startDate, endDate, calendar, description, location) |

## Common Patterns

```
# Context-aware task selection
get_today + get_tagged_items("@home") + get_tagged_items("#low")

# Duplicate check before capture
search_todos("dentist") → exists? merge : add_todo

# Weekly review data
get_logbook(period:'7d') + get_projects + get_tagged_items("@waiting")

# Deadline urgency
search_advanced(deadline:"YYYY-MM-DD", status:"open")

# Calendar gap detection
list-today-events → find gaps → suggest tasks that fit
```
