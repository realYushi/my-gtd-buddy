# Backend Profile

A profile is JSON. It maps GTD concepts to one task backend and one calendar backend. It contains names, not credentials.

## Shape

```json
{
  "schema": 1,
  "name": "todoist-google",
  "task": {
    "provider": "todoist",
    "mode": "mcp",
    "containers": {
      "inbox": "Inbox",
      "next": "Next Actions",
      "waiting": "Waiting For",
      "someday": "Someday",
      "projects": "Projects"
    },
    "labels": {
      "contexts": ["@home", "@office", "@errands", "@calls"],
      "energy": ["#high", "#low", "#quick"],
      "duration": ["#5min", "#15min", "#30min", "#1hour", "#deep"]
    },
    "tools": {
      "capture": "todoist_create_task",
      "list": "todoist_get_tasks",
      "read": "todoist_get_task",
      "update": "todoist_update_task",
      "complete": "todoist_complete_task",
      "delete": "todoist_delete_task",
      "completed": "todoist_get_completed_tasks",
      "projects": "todoist_get_projects",
      "labels": "todoist_get_labels"
    },
    "capabilities": {
      "undo": false,
      "delete": true,
      "completed_query": true,
      "due_dates": true,
      "labels": true,
      "priority": true,
      "modified_date": false,
      "project_links": false,
      "batch": false
    }
  },
  "calendar": {
    "provider": "google",
    "mode": "mcp",
    "tools": {
      "events": "google_calendar_list_events",
      "freebusy": "google_calendar_freebusy"
    },
    "capabilities": {
      "freebusy": true
    },
    "workday": "09:00-18:00"
  },
  "preferences": {
    "processing_style": "quick",
    "timezone": "Pacific/Auckland"
  }
}
```

The example tool names are illustrative. Setup must replace them with names discovered from the installed MCP server.

## Rules

- The five containers are distinct and named exactly as the backend names them.
- Tool names are exact.
- Manual Mode applies per backend. A manual task backend or manual calendar uses empty tools for that backend; a manual task backend may still use an mcp calendar.
- An mcp task backend requires `capture`, `list`, `read`, `update`, and `complete`. `projects` is optional.
- An mcp calendar requires `events` and an explicit valid IANA `preferences.timezone`.
- `workday` is a same-day `HH:MM-HH:MM` span with start before end. It applies every day. For example, `09:15-09:45` is valid.
- `completed_query: true` requires `tools.completed`.
- `delete: true` requires `tools.delete` in mcp mode.
- `undo: true` requires `tools.undo` in mcp mode.
- `freebusy: true` requires `calendar.tools.freebusy`.
- Optional task capabilities: `modified_date`, `project_links`, `batch`.
- Capability declarations control behavior. A tool's presence never enables an undeclared capability.
- Context, energy, and duration label lists may be empty.
- No tokens, passwords, or credentials belong in the profile.
- Store the profile per user, outside the skill. `.gtd/profile.json` is the default.
