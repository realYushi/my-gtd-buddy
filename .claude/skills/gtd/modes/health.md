# System Health

Agent checks health at session start and surfaces issues naturally.

## Health Thresholds

| Metric | Healthy | Warning | Critical |
|--------|---------|---------|----------|
| Inbox | 0-5 | 6-15 | 16+ |
| Stale (14+ days) | 0-3 | 4-10 | 11+ |
| Days since review | 0-7 | 8-14 | 15+ |
| Next Actions | 5-20 | 21-40 | 41+ |

## Surfacing (Don't lecture, state facts)

```
"Inbox has 23 items. Clear now?"

"8 items sitting 2+ weeks. Quick prune?"

"Last review was 12 days ago. 5-min check-in?"
```

## Recovery Mode

Trigger: Critical health OR "system is a mess"

```
"Let's reset. No guilt.

1. Declare bankruptcy? (stale items → Someday)
2. Inbox blitz? (rapid keep/dump)
3. Pick just 3 for this week?

Which?"
```

**Bankruptcy:** Move all 14+ day stale items to Someday
**Blitz:** Rapid "keep/dump" for each item
**Focus:** Pick 3, flag them, ignore rest

## Prevention > Recovery

| Frequency | Action | Time |
|-----------|--------|------|
| Daily | Process inbox | 2 min |
| Weekly | Review | 5 min |
| Monthly | Prune lists | 10 min |

Small, frequent, friction-free beats big scheduled reviews.
