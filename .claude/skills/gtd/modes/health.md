# System Health

Agent checks health at session start and surfaces issues naturally. Never lecture — state facts, offer action.

## Health Thresholds

| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| Inbox | 0-5 | 6-15 | 16+ |
| Stale (14+ days) | 0-3 | 4-10 | 11+ |
| Days since review | 0-7 | 8-14 | 15+ |
| Next Actions | 5-20 | 21-40 | 41+ |

## Surfacing

One issue at a time. Pick the worst metric and offer to fix it:

```
"Inbox has 23 items. Clear now?"

"8 items sitting 2+ weeks. Quick prune?"

"Last review was 12 days ago. Quick 5-min check?"

"41 next actions — system's bloated. Trim down?"
```

If multiple metrics are critical, still pick ONE. Fix it, then check if there's another.

## Recovery Mode

Trigger: Critical health OR user says "system is a mess" / "need to reset" / "cleanup"

First, show the damage briefly:
```
[X] inbox, [Y] stale, [Z] days since review.

Let's reset. 3 options:

1. Bankruptcy — stale items → Someday, start clean
2. Blitz — rapid keep/dump through everything
3. Focus 3 — pick 3 tasks for this week, ignore rest

Which?
```

**Option 1 — Bankruptcy:**
```bash
.claude/skills/gtd/scripts/reminders.sh batch-defer 14
```
Then: "Done. [N] items moved to Someday. Inbox next? (y/n)"

**Option 2 — Blitz:**
Use inbox processing flow but faster — just "keep/dump" for each:
```
1/[N]: '[item]' — keep or dump?
```
No project detection, no context tagging. Speed is the point.

**Option 3 — Focus 3:**
```bash
.claude/skills/gtd/scripts/reminders.sh next
```
Show all Next Actions. User picks 3 → flag those → done.
```
Flagged your 3. Rest is noise this week.
```

## After Recovery

Once recovery action is done:
```
Better. [summary of what changed]

Process inbox next, or done for now?
```

## Prevention

| Frequency | Action | Time |
|-----------|--------|------|
| Daily | Process inbox | 2 min |
| Weekly | Review | 5 min |
| Monthly | Prune Someday list | 10 min |

Small, frequent, friction-free beats big scheduled reviews. If the user's system keeps going critical, suggest shorter daily check-ins rather than bigger weekly reviews.
