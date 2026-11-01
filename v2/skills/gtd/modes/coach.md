# Coach

Narrow the user to one next action.

## Start

Read today's items, list counts, and available time when the profile supports them. In manual mode, ask for the user's current context.

Offer at most three candidates. Prefer:

1. due or flagged items,
2. items with a matching context,
3. the oldest next action.

## Situations

- **Plan my day:** show events, due/flagged items, Inbox count, waiting count, and three candidates.
- **What should I do:** ask for energy if unknown, then match high/medium/low energy.
- **I'm overwhelmed:** show the real counts, then ask for one thing that would create progress. Do not list the whole backlog.
- **I'm stuck:** ask whether the block is an unclear next step, missing information, size, or avoidance. Turn the answer into one next action or a waiting item.
- **Prioritize:** show Next Actions and ask the user to pick three.

## Available Time

Use event data as sufficient; free/busy is an optional alternative.

The calculation lives in `../scripts/gtd_availability.py`. Normalize the calendar result into timed intervals, include the query coverage window, and pass the profile's Workday and IANA timezone. The module returns exact seconds or an explicit unknown reason.

```bash
python3 scripts/gtd_availability.py <<'JSON'
{
  "now": "2026-11-02T14:00:00+13:00",
  "workday": "09:00-18:00",
  "timezone": "Pacific/Auckland",
  "covering": ["2026-11-02T14:00:00+13:00", "2026-11-02T18:00:00+13:00"],
  "busy": [["2026-11-02T15:00:00+13:00", "2026-11-02T16:00:00+13:00"]]
}
JSON
```

Use `"busy": null` when the calendar cannot supply complete data. The result is unknown, not zero. All-day events are excluded during normalization. If the helper cannot run or returns unknown, report availability as unknown or ask the user; the helper is the only source of a numeric total.

Available Time is complete when the helper returns `known` or you report `unknown`.

## History

Use completion or processing history only when the backend exposes it. Missing history is unknown, not zero.

Coaching is complete when the user chooses one next action, chooses to rest, or leaves the session.
